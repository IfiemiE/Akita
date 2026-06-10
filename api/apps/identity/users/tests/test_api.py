"""
API-layer tests for UserViewSet and SpeakerProfileViewSet.
Uses APIClient + reverse() against the full URL conf.

URL patterns (from apps/identity/users/urls.py + project urls.py):
    user-list        GET     /api/v1/users/contributors/
    user-detail      GET     /api/v1/users/contributors/{pk}/
    speaker-list     GET     /api/v1/users/speakers/
    speaker-detail   GET/PUT/PATCH/DELETE  /api/v1/users/speakers/{pk}/

Fixtures:
    fixtures = [
                'infrastructure/communities.json', 
                'identity/akitauser.json', 
                'identity/speakerprofile.json'
                ]

Run
---
  $ python manage.py test TEST_DOTTED_PATH -v 2 --settings=config.settings.test
      
where 
TEST_DOTTED_PATH = apps.identity.users.tests.test_api.CLASS.METHOD for a specific test METHOD
TEST_DOTTED_PATH = apps.identity.users.tests.test_api.CLASS for a specific test CLASS
TEST_DOTTED_PATH = apps.identity.users.tests.test_api for the specific test_models module
TEST_DOTTED_PATH = apps.identity.users.tests for all modules in the test folder
---

"""

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.identity.users.models import AkitaUser, SpeakerProfile, UserRole
from apps.infrastructure.core.models import Community


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_bootstrap_superuser():
    """
    Shared superuser used as default registrar in tests.
    Created once per test database via get_or_create.
    Reserved username '_bootstrap_su' must never be used in test-specific users.
    """
    su, _ = AkitaUser.objects.get_or_create(
        username='_bootstrap_su',
        defaults={
            'role': UserRole.SUPERUSER,
            'is_staff': True,
            'is_superuser': True,
        }
    )
    return su


def make_user(username, role=UserRole.CONTRIBUTOR, community=None,
              is_active=True, registered_by='__auto__', **kwargs):
    """
    Create a minimal AkitaUser without hitting the fixture layer.

    The pre_save signal requires registered_by for all non-superuser roles.
    Pass registered_by=None explicitly only when testing signal rejection.
    All other callers get the bootstrap superuser assigned automatically.
    """
    if registered_by == '__auto__':
        registrar = None if role == UserRole.SUPERUSER else _get_bootstrap_superuser()
    else:
        registrar = registered_by  # explicit — includes None for signal tests

    return AkitaUser.objects.create_user(
        username=username,
        password='testpass123',
        role=role,
        community=community,
        is_active=is_active,
        registered_by=registrar,
        **kwargs,
    )


def auth_client(user):
    """Return an APIClient force-authenticated as the given user."""
    client = APIClient()
    client.force_authenticate(user=user)
    return client


# ---------------------------------------------------------------------------
# URL name constants (from DefaultRouter registration in users/urls.py)
# ---------------------------------------------------------------------------
USER_LIST      = 'user-list'
USER_DETAIL    = 'user-detail'
SPEAKER_LIST   = 'speaker-list'
SPEAKER_DETAIL = 'speaker-detail'


# ===========================================================================
# UserViewSet — GET /api/v1/users/contributors/
# ===========================================================================

class UserListTests(TestCase):
    """
    UserViewSet is ReadOnlyModelViewSet.
    permission_classes = [IsEditorOrAbove]
    queryset = AkitaUser.objects.filter(is_active=True)
    filterset_fields = ['role', 'community', 'first_name', 'last_name']
    """

    def setUp(self):
        self.superuser = make_user('super',    role=UserRole.SUPERUSER)
        self.admin     = make_user('admin',    role=UserRole.ADMIN)
        self.editor    = make_user('editor',   role=UserRole.EDITOR)
        self.contrib   = make_user('contrib',  role=UserRole.CONTRIBUTOR)
        self.inactive  = make_user('inactive', role=UserRole.EDITOR, is_active=False)

    # --- Permission ---

    def test_unauthenticated_request_is_rejected(self):
        response = APIClient().get(reverse(USER_LIST))
        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ])

    def test_contributor_is_forbidden(self):
        response = auth_client(self.contrib).get(reverse(USER_LIST))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_editor_can_list_users(self):
        response = auth_client(self.editor).get(reverse(USER_LIST))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_list_users(self):
        response = auth_client(self.admin).get(reverse(USER_LIST))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_superuser_can_list_users(self):
        response = auth_client(self.superuser).get(reverse(USER_LIST))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # --- Queryset — only active users returned ---

    def test_inactive_users_excluded_from_list(self):
        response = auth_client(self.editor).get(reverse(USER_LIST))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        usernames = [u['username'] for u in response.data['results']]
        self.assertNotIn('inactive', usernames)

    def test_active_users_included_in_list(self):
        response = auth_client(self.editor).get(reverse(USER_LIST))
        usernames = [u['username'] for u in response.data['results']]
        self.assertIn('editor', usernames)

    def test_bootstrap_superuser_appears_in_list(self):
        """_bootstrap_su is active and should appear in results."""
        response = auth_client(self.editor).get(reverse(USER_LIST))
        usernames = [u['username'] for u in response.data['results']]
        self.assertIn('_bootstrap_su', usernames)

    # --- Serializer fields ---

    def test_response_includes_expected_fields(self):
        response = auth_client(self.editor).get(reverse(USER_LIST))
        first = response.data['results'][0]
        for field in [
            'id', 'username', 'first_name', 'last_name', 'email',
            'role', 'role_level', 'community', 'community_name',
            'registered_by', 'registered_by_name',
            'registration_date', 'registration_notes', 'speaks_for_self',
            'elevated_by', 'elevated_by_name', 'elevated_at', 'elevation_notes',
            'date_joined', 'is_active',
        ]:
            with self.subTest(field=field):
                self.assertIn(field, first)

    def test_password_not_exposed_in_list(self):
        response = auth_client(self.editor).get(reverse(USER_LIST))
        first = response.data['results'][0]
        self.assertNotIn('password', first)

    def test_role_level_is_integer_in_list(self):
        response = auth_client(self.editor).get(reverse(USER_LIST))
        for user in response.data['results']:
            with self.subTest(username=user['username']):
                self.assertIsInstance(user['role_level'], int)

    def test_community_name_is_null_when_no_community(self):
        """Users with no community should return null community_name."""
        response = auth_client(self.editor).get(reverse(USER_LIST))
        editor_data = next(
            u for u in response.data['results'] if u['username'] == 'editor'
        )
        self.assertIsNone(editor_data['community_name'])

    def test_community_name_populated_when_community_set(self):
        community = Community.objects.create(name='agbobiri')
        make_user('villager', community=community)
        response = auth_client(self.editor).get(reverse(USER_LIST))
        villager_data = next(
            (u for u in response.data['results'] if u['username'] == 'villager'),
            None
        )
        self.assertIsNotNone(villager_data)
        self.assertEqual(villager_data['community_name'], 'agbobiri')

    # --- Read-only — write methods rejected ---

    def test_post_to_user_list_is_not_allowed(self):
        response = auth_client(self.admin).post(reverse(USER_LIST), {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    # --- Filtering ---

    def test_filter_by_role_contributor(self):
        response = auth_client(self.editor).get(
            reverse(USER_LIST), {'role': UserRole.CONTRIBUTOR}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for user in response.data['results']:
            self.assertEqual(user['role'], UserRole.CONTRIBUTOR)

    def test_filter_by_role_editor(self):
        response = auth_client(self.editor).get(
            reverse(USER_LIST), {'role': UserRole.EDITOR}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # inactive editor excluded, only active editor returned
        usernames = [u['username'] for u in response.data['results']]
        self.assertIn('editor', usernames)
        self.assertNotIn('inactive', usernames)

    def test_filter_by_community(self):
        community = Community.objects.create(name='kalaba')
        make_user('kalaba_user', community=community)
        response = auth_client(self.editor).get(
            reverse(USER_LIST), {'community': community.pk}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for user in response.data['results']:
            self.assertEqual(user['community'], community.pk)

    def test_filter_by_first_name(self):
        make_user('uniquefirst', first_name='Ekemezie')
        response = auth_client(self.editor).get(
            reverse(USER_LIST), {'first_name': 'Ekemezie'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        usernames = [u['username'] for u in response.data['results']]
        self.assertIn('uniquefirst', usernames)

    def test_filter_by_last_name(self):
        make_user('uniquelast', last_name='Oparanma')
        response = auth_client(self.editor).get(
            reverse(USER_LIST), {'last_name': 'Oparanma'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        usernames = [u['username'] for u in response.data['results']]
        self.assertIn('uniquelast', usernames)

    def test_filter_returns_empty_for_nonexistent_value(self):
        response = auth_client(self.editor).get(
            reverse(USER_LIST), {'first_name': 'ZZZNobodyHasThisName'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)
        
    # --- Pagination ---
    def test_first_page_has_no_previous(self):
        response = auth_client(self.editor).get(reverse(USER_LIST))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['previous'])

    def test_last_page_has_no_next(self):
        from django.conf import settings
        page_size = settings.REST_FRAMEWORK.get('PAGE_SIZE', 10)
        existing = AkitaUser.objects.filter(is_active=True).count()
        shortfall = (page_size - existing) + 1
        for i in range(max(shortfall, 0)):
            make_user(f'pagination_user_{i}')
        response = auth_client(self.editor).get(
            reverse(USER_LIST), {'page': 2}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['next'])

    def test_count_reflects_total_active_users(self):
        response = auth_client(self.editor).get(reverse(USER_LIST))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        active_count = AkitaUser.objects.filter(is_active=True).count()
        self.assertEqual(response.data['count'], active_count)

# ===========================================================================
# UserViewSet — GET /api/v1/users/contributors/{pk}/
# ===========================================================================

class UserDetailTests(TestCase):

    def setUp(self):
        self.editor   = make_user('editor',  role=UserRole.EDITOR)
        self.contrib  = make_user('contrib', role=UserRole.CONTRIBUTOR)
        self.inactive = make_user('gone',    role=UserRole.CONTRIBUTOR, is_active=False)

    def test_editor_can_retrieve_active_user(self):
        url = reverse(USER_DETAIL, kwargs={'pk': self.contrib.pk})
        response = auth_client(self.editor).get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'contrib')

    def test_inactive_user_returns_404(self):
        """Inactive users are excluded from the queryset."""
        url = reverse(USER_DETAIL, kwargs={'pk': self.inactive.pk})
        response = auth_client(self.editor).get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_nonexistent_user_returns_404(self):
        url = reverse(USER_DETAIL, kwargs={'pk': 99999})
        response = auth_client(self.editor).get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_contributor_cannot_retrieve_user_detail(self):
        url = reverse(USER_DETAIL, kwargs={'pk': self.editor.pk})
        response = auth_client(self.contrib).get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_retrieve_user_detail(self):
        url = reverse(USER_DETAIL, kwargs={'pk': self.contrib.pk})
        response = APIClient().get(url)
        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ])

    def test_put_not_allowed(self):
        url = reverse(USER_DETAIL, kwargs={'pk': self.contrib.pk})
        response = auth_client(self.editor).put(url, {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_patch_not_allowed(self):
        url = reverse(USER_DETAIL, kwargs={'pk': self.contrib.pk})
        response = auth_client(self.editor).patch(url, {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_not_allowed(self):
        url = reverse(USER_DETAIL, kwargs={'pk': self.contrib.pk})
        response = auth_client(self.editor).delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_role_level_computed_correctly_in_response(self):
        url = reverse(USER_DETAIL, kwargs={'pk': self.editor.pk})
        response = auth_client(self.editor).get(url)
        self.assertEqual(response.data['role_level'], 2)  # editor = 2

    def test_registered_by_name_populated_in_detail(self):
        """registered_by_name should reflect the registrar's username."""
        url = reverse(USER_DETAIL, kwargs={'pk': self.contrib.pk})
        response = auth_client(self.editor).get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # contrib was registered by _bootstrap_su
        self.assertEqual(response.data['registered_by_name'], '_bootstrap_su')

    def test_elevated_by_name_null_when_not_elevated(self):
        url = reverse(USER_DETAIL, kwargs={'pk': self.contrib.pk})
        response = auth_client(self.editor).get(url)
        self.assertIsNone(response.data['elevated_by_name'])

    def test_detail_response_fields_complete(self):
        url = reverse(USER_DETAIL, kwargs={'pk': self.contrib.pk})
        response = auth_client(self.editor).get(url)
        for field in [
            'id', 'username', 'role', 'role_level', 'is_active',
            'community', 'community_name', 'registered_by', 'registered_by_name',
            'elevated_by', 'elevated_by_name', 'elevated_at', 'elevation_notes',
        ]:
            with self.subTest(field=field):
                self.assertIn(field, response.data)


# ===========================================================================
# SpeakerProfileViewSet — GET (anonymous read)
# ===========================================================================

class SpeakerListReadTests(TestCase):
    """
    SpeakerProfileViewSet: SAFE_METHODS → IsAnonymousReadOnly (public).
    Write methods → IsContributor.
    """

    def setUp(self):
        self.documenter = make_user('doc', role=UserRole.EDITOR)
        self.sp1 = SpeakerProfile.objects.create(
            full_name='Ebi Egi',
            documented_by=self.documenter,
        )
        self.sp2 = SpeakerProfile.objects.create(
            full_name='Tari Igowari',
            documented_by=self.documenter,
            is_living=False,
        )

    def test_anonymous_can_list_speakers(self):
        response = APIClient().get(reverse(SPEAKER_LIST))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_anonymous_can_retrieve_speaker(self):
        url = reverse(SPEAKER_DETAIL, kwargs={'pk': self.sp1.pk})
        response = APIClient().get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['full_name'], 'Ebi Egi')

    def test_speaker_list_includes_all_profiles(self):
        response = APIClient().get(reverse(SPEAKER_LIST))
        names = [s['full_name'] for s in response.data['results']]
        self.assertIn('Ebi Egi', names)
        self.assertIn('Tari Igowari', names)

    def test_response_includes_expected_fields(self):
        response = APIClient().get(reverse(SPEAKER_LIST))
        first = response.data['results'][0]
        for field in [
            'id', 'full_name', 'clan_name', 'village', 'village_name',
            'birth_year', 'is_living',
            'user_account', 'user_account_username',
            'documented_by', 'documented_by_name',
        ]:
            with self.subTest(field=field):
                self.assertIn(field, first)

    def test_documented_by_name_field_present_and_correct(self):
        url = reverse(SPEAKER_DETAIL, kwargs={'pk': self.sp1.pk})
        response = APIClient().get(url)
        self.assertIn('documented_by_name', response.data)
        self.assertEqual(response.data['documented_by_name'], 'doc')

    def test_village_name_null_when_no_village(self):
        url = reverse(SPEAKER_DETAIL, kwargs={'pk': self.sp1.pk})
        response = APIClient().get(url)
        self.assertIsNone(response.data['village_name'])

    def test_village_name_populated_when_village_set(self):
        community = Community.objects.create(name='ayamabele')
        sp = SpeakerProfile.objects.create(
            full_name='Speaker With Village',
            village=community,
            documented_by=self.documenter,
        )
        url = reverse(SPEAKER_DETAIL, kwargs={'pk': sp.pk})
        response = APIClient().get(url)
        self.assertEqual(response.data['village_name'], 'ayamabele')

    def test_user_account_username_null_when_no_linked_account(self):
        url = reverse(SPEAKER_DETAIL, kwargs={'pk': self.sp1.pk})
        response = APIClient().get(url)
        self.assertIsNone(response.data['user_account_username'])

    def test_user_account_username_populated_when_linked(self):
        linked_user = make_user('linked_to_speaker')
        sp = SpeakerProfile.objects.create(
            full_name='Speaker With Account',
            user_account=linked_user,
            documented_by=self.documenter,
        )
        url = reverse(SPEAKER_DETAIL, kwargs={'pk': sp.pk})
        response = APIClient().get(url)
        self.assertEqual(response.data['user_account_username'], 'linked_to_speaker')

    def test_is_living_false_returned_correctly(self):
        url = reverse(SPEAKER_DETAIL, kwargs={'pk': self.sp2.pk})
        response = APIClient().get(url)
        self.assertFalse(response.data['is_living'])

    def test_nonexistent_speaker_returns_404(self):
        url = reverse(SPEAKER_DETAIL, kwargs={'pk': 99999})
        response = APIClient().get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ===========================================================================
# SpeakerProfileViewSet — POST
# ===========================================================================

class SpeakerCreateTests(TestCase):

    def setUp(self):
        self.contrib    = make_user('contrib', role=UserRole.CONTRIBUTOR)
        self.editor     = make_user('editor',  role=UserRole.EDITOR)
        self.documenter = make_user('doc',     role=UserRole.EDITOR)

    def _payload(self):
        return {
            'full_name': 'New Speaker',
            'birth_year': 1975,
            'is_living': True,
            'documented_by': self.documenter.pk,
        }

    def test_anonymous_cannot_create_speaker(self):
        response = APIClient().post(reverse(SPEAKER_LIST), self._payload())
        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ])

    def test_contributor_can_create_speaker(self):
        response = auth_client(self.contrib).post(
            reverse(SPEAKER_LIST), self._payload(), format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['full_name'], 'New Speaker')

    def test_editor_can_create_speaker(self):
        response = auth_client(self.editor).post(
            reverse(SPEAKER_LIST), self._payload(), format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_returns_all_expected_fields(self):
        response = auth_client(self.contrib).post(
            reverse(SPEAKER_LIST), self._payload(), format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for field in [
            'id', 'full_name', 'clan_name', 'village', 'village_name',
            'birth_year', 'is_living', 'user_account', 'user_account_username',
            'documented_by', 'documented_by_name',
        ]:
            with self.subTest(field=field):
                self.assertIn(field, response.data)

    def test_create_without_full_name_fails(self):
        payload = self._payload()
        del payload['full_name']
        response = auth_client(self.contrib).post(
            reverse(SPEAKER_LIST), payload, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('full_name', response.data)

    def test_create_with_village(self):
        community = Community.objects.create(name='ikarama')
        payload = self._payload()
        payload['village'] = community.pk
        response = auth_client(self.contrib).post(
            reverse(SPEAKER_LIST), payload, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['village'], community.pk)
        self.assertEqual(response.data['village_name'], 'ikarama')

    def test_create_with_linked_user_account(self):
        speaker_user = make_user('has_profile')
        payload = self._payload()
        payload['user_account'] = speaker_user.pk
        response = auth_client(self.contrib).post(
            reverse(SPEAKER_LIST), payload, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user_account'], speaker_user.pk)
        self.assertEqual(response.data['user_account_username'], 'has_profile')

    def test_create_deceased_speaker(self):
        payload = self._payload()
        payload['is_living'] = False
        response = auth_client(self.contrib).post(
            reverse(SPEAKER_LIST), payload, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data['is_living'])

    def test_create_speaker_without_clan_name(self):
        payload = self._payload()
        payload['clan_name'] = ''
        response = auth_client(self.contrib).post(
            reverse(SPEAKER_LIST), payload, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['clan_name'], '')

    def test_create_speaker_without_birth_year(self):
        payload = self._payload()
        del payload['birth_year']
        response = auth_client(self.contrib).post(
            reverse(SPEAKER_LIST), payload, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data['birth_year'])

    def test_duplicate_user_account_link_fails(self):
        """OneToOne constraint — same user_account on two profiles returns 400."""
        speaker_user = make_user('one_profile_only')
        payload = self._payload()
        payload['user_account'] = speaker_user.pk
        auth_client(self.contrib).post(
            reverse(SPEAKER_LIST), payload, format='json'
        )
        payload['full_name'] = 'Duplicate Attempt'
        response = auth_client(self.contrib).post(
            reverse(SPEAKER_LIST), payload, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_created_speaker_persists_in_database(self):
        response = auth_client(self.contrib).post(
            reverse(SPEAKER_LIST), self._payload(), format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            SpeakerProfile.objects.filter(pk=response.data['id']).exists()
        )


# ===========================================================================
# SpeakerProfileViewSet — PATCH / PUT
# ===========================================================================

class SpeakerUpdateTests(TestCase):

    def setUp(self):
        self.contrib    = make_user('contrib', role=UserRole.CONTRIBUTOR)
        self.documenter = make_user('doc',     role=UserRole.EDITOR)
        self.sp = SpeakerProfile.objects.create(
            full_name='Original Name',
            documented_by=self.documenter,
        )

    def test_contributor_can_patch_speaker(self):
        url = reverse(SPEAKER_DETAIL, kwargs={'pk': self.sp.pk})
        response = auth_client(self.contrib).patch(
            url, {'full_name': 'Updated Name'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['full_name'], 'Updated Name')

    def test_patch_persists_to_database(self):
        url = reverse(SPEAKER_DETAIL, kwargs={'pk': self.sp.pk})
        auth_client(self.contrib).patch(
            url, {'full_name': 'Persisted Name'}, format='json'
        )
        self.sp.refresh_from_db()
        self.assertEqual(self.sp.full_name, 'Persisted Name')

    def test_anonymous_cannot_patch_speaker(self):
        url = reverse(SPEAKER_DETAIL, kwargs={'pk': self.sp.pk})
        response = APIClient().patch(url, {'full_name': 'Hacked'}, format='json')
        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ])

    def test_patch_is_living_to_false(self):
        url = reverse(SPEAKER_DETAIL, kwargs={'pk': self.sp.pk})
        response = auth_client(self.contrib).patch(
            url, {'is_living': False}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_living'])

    def test_patch_clan_name(self):
        url = reverse(SPEAKER_DETAIL, kwargs={'pk': self.sp.pk})
        response = auth_client(self.contrib).patch(
            url, {'clan_name': 'Akita-Patched'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['clan_name'], 'Akita-Patched')

    def test_patch_village(self):
        community = Community.objects.create(name='akumoni')
        url = reverse(SPEAKER_DETAIL, kwargs={'pk': self.sp.pk})
        response = auth_client(self.contrib).patch(
            url, {'village': community.pk}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['village'], community.pk)
        self.assertEqual(response.data['village_name'], 'akumoni')

    def test_put_replaces_speaker_profile(self):
        url = reverse(SPEAKER_DETAIL, kwargs={'pk': self.sp.pk})
        payload = {
            'full_name': 'Fully Replaced',
            'clan_name': '',
            'birth_year': 1980,
            'is_living': True,
            'documented_by': self.documenter.pk,
        }
        response = auth_client(self.contrib).put(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['full_name'], 'Fully Replaced')
        self.assertEqual(response.data['birth_year'], 1980)

    def test_put_persists_to_database(self):
        url = reverse(SPEAKER_DETAIL, kwargs={'pk': self.sp.pk})
        payload = {
            'full_name': 'PUT Persisted',
            'clan_name': '',
            'birth_year': 1990,
            'is_living': False,
            'documented_by': self.documenter.pk,
        }
        auth_client(self.contrib).put(url, payload, format='json')
        self.sp.refresh_from_db()
        self.assertEqual(self.sp.full_name, 'PUT Persisted')
        self.assertFalse(self.sp.is_living)

    def test_put_without_full_name_fails(self):
        url = reverse(SPEAKER_DETAIL, kwargs={'pk': self.sp.pk})
        payload = {
            'clan_name': '',
            'is_living': True,
            'documented_by': self.documenter.pk,
        }
        response = auth_client(self.contrib).put(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('full_name', response.data)

    def test_patch_nonexistent_speaker_returns_404(self):
        url = reverse(SPEAKER_DETAIL, kwargs={'pk': 99999})
        response = auth_client(self.contrib).patch(
            url, {'full_name': 'Ghost'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ===========================================================================
# SpeakerProfileViewSet — DELETE
# ===========================================================================

class SpeakerDeleteTests(TestCase):

    def setUp(self):
        self.contrib    = make_user('contrib', role=UserRole.CONTRIBUTOR)
        self.documenter = make_user('doc',     role=UserRole.EDITOR)
        self.sp = SpeakerProfile.objects.create(
            full_name='To Be Deleted',
            documented_by=self.documenter,
        )

    def test_contributor_can_delete_speaker(self):
        url = reverse(SPEAKER_DETAIL, kwargs={'pk': self.sp.pk})
        response = auth_client(self.contrib).delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(SpeakerProfile.objects.filter(pk=self.sp.pk).exists())

    def test_anonymous_cannot_delete_speaker(self):
        url = reverse(SPEAKER_DETAIL, kwargs={'pk': self.sp.pk})
        response = APIClient().delete(url)
        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ])

    def test_delete_leaves_no_database_record(self):
        pk = self.sp.pk
        url = reverse(SPEAKER_DETAIL, kwargs={'pk': pk})
        auth_client(self.contrib).delete(url)
        self.assertFalse(SpeakerProfile.objects.filter(pk=pk).exists())

    def test_delete_nonexistent_speaker_returns_404(self):
        url = reverse(SPEAKER_DETAIL, kwargs={'pk': 99999})
        response = auth_client(self.contrib).delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_returns_no_body(self):
        url = reverse(SPEAKER_DETAIL, kwargs={'pk': self.sp.pk})
        response = auth_client(self.contrib).delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(response.data)  # 204 has no body


# ===========================================================================
# AkitaUserSerializer — read-only field enforcement (direct serializer test)
# ===========================================================================

class AkitaUserSerializerFieldTests(TestCase):
    """
    AkitaUserSerializer declares role, registered_by, elevated_by,
    registration_date, elevated_at, date_joined as read_only.
    Tested via direct serializer instantiation since UserViewSet is ReadOnly
    and exposes no write endpoint.
    """

    def setUp(self):
        self.user = make_user('ro_test', role=UserRole.CONTRIBUTOR)

    def test_read_only_fields_ignored_on_partial_update(self):
        from apps.identity.users.serializers import AkitaUserSerializer
        data = {
            'role': UserRole.SUPERUSER,    # read-only → ignored
            'registered_by': self.user.pk, # read-only → ignored
            'username': 'updated_username',
        }
        serializer = AkitaUserSerializer(self.user, data=data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn('role', serializer.validated_data)
        self.assertNotIn('registered_by', serializer.validated_data)

    def test_role_level_is_read_only_computed_field(self):
        from apps.identity.users.serializers import AkitaUserSerializer
        serializer = AkitaUserSerializer(self.user)
        self.assertIn('role_level', serializer.data)
        self.assertEqual(serializer.data['role_level'], 1)  # contributor = 1

    def test_registered_by_name_is_read_only(self):
        from apps.identity.users.serializers import AkitaUserSerializer
        serializer = AkitaUserSerializer(self.user)
        self.assertIn('registered_by_name', serializer.data)
        # registered by _bootstrap_su
        self.assertEqual(serializer.data['registered_by_name'], '_bootstrap_su')

    def test_elevated_by_name_null_when_not_elevated(self):
        from apps.identity.users.serializers import AkitaUserSerializer
        serializer = AkitaUserSerializer(self.user)
        self.assertIsNone(serializer.data['elevated_by_name'])

    def test_community_name_null_when_no_community(self):
        from apps.identity.users.serializers import AkitaUserSerializer
        serializer = AkitaUserSerializer(self.user)
        self.assertIsNone(serializer.data['community_name'])


# ===========================================================================
# ContributorRegistrationSerializer — direct serializer tests
# (No endpoint registered yet — tested via serializer instantiation)
# ===========================================================================

class ContributorRegistrationSerializerTests(TestCase):
    """
    ContributorRegistrationSerializer handles new user registration.
    No HTTP endpoint exposes it yet, so it is tested directly.
    """

    def setUp(self):
        self.registrar_admin = make_user('reg_admin', role=UserRole.ADMIN)
        self.registrar_editor = make_user('reg_editor', role=UserRole.EDITOR)

    def _mock_request(self, user):
        class MockRequest:
            pass
        req = MockRequest()
        req.user = user
        return req

    def _valid_payload(self):
        return {
            'username': 'new_contrib',
            'password': 'Str0ng!Pass99',
            'password_confirm': 'Str0ng!Pass99',
            'first_name': 'Emeka',
            'last_name': 'Obi',
            'email': 'emeka@akita.org',
            'role': UserRole.CONTRIBUTOR,
            'registration_notes': 'Registered at village event.',
            'speaks_for_self': True,
        }

    def test_valid_data_passes_validation(self):
        from apps.identity.users.serializers import ContributorRegistrationSerializer
        serializer = ContributorRegistrationSerializer(
            data=self._valid_payload(),
            context={'request': self._mock_request(self.registrar_admin)}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_mismatched_passwords_fail_validation(self):
        from apps.identity.users.serializers import ContributorRegistrationSerializer
        payload = self._valid_payload()
        payload['password_confirm'] = 'WrongPassword'
        serializer = ContributorRegistrationSerializer(
            data=payload,
            context={'request': self._mock_request(self.registrar_admin)}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)

    def test_registrar_cannot_assign_own_role(self):
        """Editor cannot register another editor."""
        from apps.identity.users.serializers import ContributorRegistrationSerializer
        payload = self._valid_payload()
        payload['role'] = UserRole.EDITOR  # same as registrar's role
        serializer = ContributorRegistrationSerializer(
            data=payload,
            context={'request': self._mock_request(self.registrar_editor)}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('role', serializer.errors)

    def test_registrar_cannot_assign_higher_role(self):
        """Editor cannot register an admin."""
        from apps.identity.users.serializers import ContributorRegistrationSerializer
        payload = self._valid_payload()
        payload['role'] = UserRole.ADMIN
        serializer = ContributorRegistrationSerializer(
            data=payload,
            context={'request': self._mock_request(self.registrar_editor)}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('role', serializer.errors)

    def test_admin_can_register_contributor(self):
        from apps.identity.users.serializers import ContributorRegistrationSerializer
        serializer = ContributorRegistrationSerializer(
            data=self._valid_payload(),
            context={'request': self._mock_request(self.registrar_admin)}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_admin_can_register_editor(self):
        from apps.identity.users.serializers import ContributorRegistrationSerializer
        payload = self._valid_payload()
        payload['role'] = UserRole.EDITOR
        payload['username'] = 'new_editor'
        serializer = ContributorRegistrationSerializer(
            data=payload,
            context={'request': self._mock_request(self.registrar_admin)}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_first_name_required(self):
        from apps.identity.users.serializers import ContributorRegistrationSerializer
        payload = self._valid_payload()
        del payload['first_name']
        serializer = ContributorRegistrationSerializer(
            data=payload,
            context={'request': self._mock_request(self.registrar_admin)}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('first_name', serializer.errors)

    def test_last_name_required(self):
        from apps.identity.users.serializers import ContributorRegistrationSerializer
        payload = self._valid_payload()
        del payload['last_name']
        serializer = ContributorRegistrationSerializer(
            data=payload,
            context={'request': self._mock_request(self.registrar_admin)}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('last_name', serializer.errors)

    def test_password_not_in_response_fields(self):
        """password and password_confirm are write_only."""
        from apps.identity.users.serializers import ContributorRegistrationSerializer
        serializer = ContributorRegistrationSerializer(
            data=self._valid_payload(),
            context={'request': self._mock_request(self.registrar_admin)}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn('password', serializer.data)
        self.assertNotIn('password_confirm', serializer.data)

