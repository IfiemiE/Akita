"""
tests/test_models.py

Model-layer tests for AkitaUser and SpeakerProfile.
No HTTP layer involved — models and their methods are exercised directly.

Fixture load order matters:
    fixtures = ['communities.json', 'akitauser.json', 'speakerprofile.json']

FIXTURE_DIRS in config/settings/test.py must include both:
    - apps/infrastructure/core/fixtures/   (communities.json lives here)
    
    
Run
---
  $ python manage.py test TEST_DOTTED_PATH -v 2 --settings=config.settings.test
      
where 
TEST_DOTTED_PATH = apps.identity.users.tests.test_models.CLASS.METHOD for a specific test METHOD
TEST_DOTTED_PATH = apps.identity.users.tests.test_model.CLASS for a specific test CLASS
TEST_DOTTED_PATH = apps.identity.users.tests.test_model for the specific test_models module
TEST_DOTTED_PATH = apps.identity.users.tests for all modules in the test folder
"""

from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.identity.users.models import AkitaUser, SpeakerProfile, UserRole
from apps.infrastructure.core.models import Community


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_bootstrap_superuser():
    """
    Return a shared superuser used as the default registrar in tests.
    Created once per test run via get_or_create; never conflicts with
    test-specific users because of the reserved '_bootstrap_su' username.
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
              is_active=True, speaks_for_self=True,
              registered_by='__auto__', **kwargs):
    """
    Create a minimal AkitaUser without hitting the fixture layer.

    The pre_save signal requires registered_by to be set for all
    non-superuser roles.  Pass registered_by=None explicitly only
    when testing the signal itself; in all other cases the bootstrap
    superuser is used automatically.

    Args:
        registered_by: An AkitaUser instance to use as registrar.
                       Defaults to '__auto__', which resolves to the
                       shared bootstrap superuser for non-superuser roles.
                       Pass None explicitly to test signal rejection.
    """
    if registered_by == '__auto__':
        registrar = None if role == UserRole.SUPERUSER else _get_bootstrap_superuser()
    else:
        registrar = registered_by  # explicit value (including None for signal tests)

    return AkitaUser.objects.create_user(
        username=username,
        password='testpass123',
        role=role,
        community=community,
        is_active=is_active,
        speaks_for_self=speaks_for_self,
        registered_by=registrar,
        **kwargs,
    )


# ===========================================================================
# AkitaUser — role level
# ===========================================================================

class UserRoleLevelTests(TestCase):

    def test_contributor_level_is_1(self):
        user = make_user('u_contrib', role=UserRole.CONTRIBUTOR)
        self.assertEqual(user.get_role_level(), 1)

    def test_editor_level_is_2(self):
        user = make_user('u_editor', role=UserRole.EDITOR)
        self.assertEqual(user.get_role_level(), 2)

    def test_admin_level_is_3(self):
        user = make_user('u_admin', role=UserRole.ADMIN)
        self.assertEqual(user.get_role_level(), 3)

    def test_superuser_level_is_4(self):
        user = make_user('u_super', role=UserRole.SUPERUSER)
        self.assertEqual(user.get_role_level(), 4)


# ===========================================================================
# AkitaUser — can_register_users
# ===========================================================================

class CanRegisterUsersTests(TestCase):

    def test_contributor_cannot_register(self):
        user = make_user('contrib', role=UserRole.CONTRIBUTOR)
        self.assertFalse(user.can_register_users())

    def test_editor_can_register(self):
        user = make_user('editor', role=UserRole.EDITOR)
        self.assertTrue(user.can_register_users())

    def test_admin_can_register(self):
        user = make_user('admin', role=UserRole.ADMIN)
        self.assertTrue(user.can_register_users())

    def test_superuser_can_register(self):
        user = make_user('super', role=UserRole.SUPERUSER)
        self.assertTrue(user.can_register_users())


# ===========================================================================
# AkitaUser — can_elevate_user
# ===========================================================================

class CanElevateUserTests(TestCase):

    def setUp(self):
        self.superuser  = make_user('super',   role=UserRole.SUPERUSER)
        self.admin      = make_user('admin',   role=UserRole.ADMIN)
        self.editor     = make_user('editor',  role=UserRole.EDITOR)
        self.contrib    = make_user('contrib', role=UserRole.CONTRIBUTOR)

    def test_superuser_can_elevate_anyone(self):
        for target in [self.admin, self.editor, self.contrib]:
            with self.subTest(target=target.role):
                self.assertTrue(self.superuser.can_elevate_user(target))

    def test_admin_cannot_elevate_superuser(self):
        self.assertFalse(self.admin.can_elevate_user(self.superuser))

    def test_admin_cannot_elevate_another_admin(self):
        another_admin = make_user('admin2', role=UserRole.ADMIN)
        self.assertFalse(self.admin.can_elevate_user(another_admin))

    def test_editor_cannot_elevate_contributor(self):
        # editor level=2, contributor level=1; 2 > (1+1) is False
        self.assertFalse(self.editor.can_elevate_user(self.contrib))

    def test_admin_can_elevate_contributor(self):
        # admin level=3, contributor level=1; 3 > (1+1) is True
        self.assertTrue(self.admin.can_elevate_user(self.contrib))

    def test_can_elevate_none_target_returns_false(self):
        self.assertFalse(self.superuser.can_elevate_user(None))

    def test_cannot_elevate_anonymous_level_zero(self):
        # A user whose role maps to level 0 (unknown role)
        odd_user = make_user('weird')
        odd_user.role = 'unknown_role'   # bypass choices validation
        odd_user.save()
        self.assertFalse(self.admin.can_elevate_user(odd_user))


# ===========================================================================
# AkitaUser — can_manage_user
# ===========================================================================

class CanManageUserTests(TestCase):

    def setUp(self):
        self.superuser  = make_user('super',   role=UserRole.SUPERUSER)
        self.admin      = make_user('admin',   role=UserRole.ADMIN)
        self.editor     = make_user('editor',  role=UserRole.EDITOR)
        self.contrib    = make_user('contrib', role=UserRole.CONTRIBUTOR)

    def test_higher_role_can_manage_lower(self):
        self.assertTrue(self.admin.can_manage_user(self.editor))
        self.assertTrue(self.admin.can_manage_user(self.contrib))
        self.assertTrue(self.superuser.can_manage_user(self.admin))

    def test_same_role_cannot_manage(self):
        another_admin = make_user('admin2', role=UserRole.ADMIN)
        self.assertFalse(self.admin.can_manage_user(another_admin))

    def test_lower_role_cannot_manage_higher(self):
        self.assertFalse(self.editor.can_manage_user(self.admin))
        self.assertFalse(self.contrib.can_manage_user(self.editor))

    def test_none_target_returns_false(self):
        self.assertFalse(self.admin.can_manage_user(None))


# ===========================================================================
# AkitaUser — can_approve_own
# ===========================================================================

class CanApproveOwnTests(TestCase):

    def setUp(self):
        self.user_a = make_user('user_a')
        self.user_b = make_user('user_b')

    def test_user_cannot_approve_own_upload(self):
        self.assertFalse(self.user_a.can_approve_own(self.user_a))

    def test_user_can_approve_other_users_upload(self):
        self.assertTrue(self.user_a.can_approve_own(self.user_b))


# ===========================================================================
# AkitaUser — full_name property
# ===========================================================================

class UserFullNameTests(TestCase):

    def test_full_name_returns_first_and_last(self):
        user = make_user('jdoe', first_name='John', last_name='Doe')
        self.assertEqual(user.full_name, 'John Doe')

    def test_full_name_empty_when_names_not_set(self):
        user = make_user('noname')
        self.assertEqual(user.full_name, '')


# ===========================================================================
# AkitaUser — __str__
# ===========================================================================

class UserStrTests(TestCase):

    def test_str_includes_username_and_role_display(self):
        user = make_user('ada', role=UserRole.ADMIN)
        self.assertIn('ada', str(user))
        self.assertIn('Admin', str(user))


# ===========================================================================
# AkitaUser — manager: create_user
# ===========================================================================

class AkitaUserManagerTests(TestCase):

    def setUp(self):
        self.registrar = AkitaUser.objects.create_superuser(
            username='mgr_bootstrap', password='pass'
        )

    def test_create_user_defaults_to_contributor(self):
        user = AkitaUser.objects.create_user(
            username='newbie', password='pass',
            registered_by=self.registrar
        )
        self.assertEqual(user.role, UserRole.CONTRIBUTOR)

    def test_create_user_without_username_raises(self):
        with self.assertRaises(ValueError):
            AkitaUser.objects.create_user(username='', password='pass')
        # No registered_by needed — ValueError fires before save() is reached

    def test_create_superuser_sets_flags(self):
        su = AkitaUser.objects.create_superuser(
            username='rootuser', password='strongpass'
        )
        self.assertTrue(su.is_staff)
        self.assertTrue(su.is_superuser)
        self.assertEqual(su.role, UserRole.SUPERUSER)
        # No registered_by needed — superuser is exempt from the signal

    def test_create_superuser_requires_is_staff_true(self):
        with self.assertRaises(ValueError):
            AkitaUser.objects.create_superuser(
                username='bad_su', password='pass', is_staff=False
            )

    def test_create_superuser_requires_is_superuser_true(self):
        with self.assertRaises(ValueError):
            AkitaUser.objects.create_superuser(
                username='bad_su2', password='pass', is_superuser=False
            )

    def test_email_is_normalised_on_create(self):
        user = AkitaUser.objects.create_user(
            username='emailuser', password='pass',
            email='Test@EXAMPLE.COM',
            registered_by=self.registrar
        )
        self.assertEqual(user.email, 'Test@example.com')

    def test_none_email_stored_as_empty(self):
        user = AkitaUser.objects.create_user(
            username='noemail', password='pass',
            email=None,
            registered_by=self.registrar
        )
        self.assertIsNone(user.email)
        
        
# ===========================================================================
# AkitaUser — elevation tracking fields
# ===========================================================================

class UserElevationFieldTests(TestCase):

    def test_elevation_fields_null_by_default(self):
        user = make_user('plain_contrib')
        self.assertIsNone(user.elevated_by)
        self.assertIsNone(user.elevated_at)
        self.assertEqual(user.elevation_notes, '')

    def test_elevation_fields_persist(self):
        admin   = make_user('adm', role=UserRole.ADMIN)
        contrib = make_user('ctrib', role=UserRole.CONTRIBUTOR)
        now = timezone.now()

        contrib.role         = UserRole.EDITOR
        contrib.elevated_by  = admin
        contrib.elevated_at  = now
        contrib.elevation_notes = 'Promoted after review'
        contrib.save()

        contrib.refresh_from_db()
        self.assertEqual(contrib.elevated_by, admin)
        self.assertEqual(contrib.elevation_notes, 'Promoted after review')


# ===========================================================================
# AkitaUser — community FK / speaks_for_self
# ===========================================================================

class UserCommunityTests(TestCase):
    fixtures = ['infrastructure/communities.json']

    def test_user_can_belong_to_community(self):
        community = Community.objects.get(name='agbobiri')
        user = make_user('villager', community=community)
        self.assertEqual(user.community, community)

    def test_user_community_can_be_null(self):
        user = make_user('diaspora', community=None)
        self.assertIsNone(user.community)

    def test_speaks_for_self_defaults_true(self):
        user = make_user('speaker')
        self.assertTrue(user.speaks_for_self)

    def test_speaks_for_self_can_be_false(self):
        user = make_user('researcher', speaks_for_self=False)
        self.assertFalse(user.speaks_for_self)


# ===========================================================================
# AkitaUser — registered_by relationship
# ===========================================================================

class RegisteredByTests(TestCase):

    def test_registered_by_set_correctly(self):
        editor  = make_user('ed', role=UserRole.EDITOR)
        contrib = make_user('ct', role=UserRole.CONTRIBUTOR)
        contrib.registered_by = editor
        contrib.save()
        contrib.refresh_from_db()
        self.assertEqual(contrib.registered_by, editor)

    def test_superuser_registered_by_is_null(self):
        """Superusers are the bootstrap role — registered_by stays null."""
        su = make_user('root_su', role=UserRole.SUPERUSER)
        self.assertIsNone(su.registered_by)

# ===========================================================================
# AkitaUser — ordering and is_active
# ===========================================================================

class UserQueryTests(TestCase):

    def test_active_users_queryable(self):
        make_user('active1', is_active=True)
        make_user('inactive1', is_active=False)
        active = AkitaUser.objects.filter(is_active=True)
        inactive = AkitaUser.objects.filter(is_active=False)
        self.assertGreaterEqual(active.count(), 1)
        self.assertGreaterEqual(inactive.count(), 1)


# ===========================================================================
# AkitaUser — registered_by signal enforcement
# ===========================================================================

class RegisteredBySignalTests(TestCase):
    """
    Tests for the pre_save signal:
        enforce_registered_by_for_non_superusers

    Rule: registered_by must be set for every non-superuser account.
          Superusers are exempt (bootstrapping use case).

    These tests pass registered_by=None explicitly to bypass the
    make_user() auto-fill and directly probe the signal's behaviour.
    """

    def setUp(self):
        # A real registrar for the positive-path tests
        self.registrar = make_user('signal_registrar', role=UserRole.SUPERUSER)

    # --- Rejection cases (null registered_by on non-superuser roles) ---

    def test_contributor_with_null_registered_by_raises(self):
        with self.assertRaises(ValidationError) as ctx:
            make_user(
                'no_registrar_contrib',
                role=UserRole.CONTRIBUTOR,
                registered_by=None,      # explicit bypass of auto-fill
            )
        self.assertIn('registered_by', ctx.exception.message_dict)

    def test_editor_with_null_registered_by_raises(self):
        with self.assertRaises(ValidationError) as ctx:
            make_user(
                'no_registrar_editor',
                role=UserRole.EDITOR,
                registered_by=None,
            )
        self.assertIn('registered_by', ctx.exception.message_dict)

    def test_admin_with_null_registered_by_raises(self):
        with self.assertRaises(ValidationError) as ctx:
            make_user(
                'no_registrar_admin',
                role=UserRole.ADMIN,
                registered_by=None,
            )
        self.assertIn('registered_by', ctx.exception.message_dict)

    def test_error_message_is_descriptive(self):
        """Signal error message should mention registered_by explicitly."""
        with self.assertRaises(ValidationError) as ctx:
            make_user(
                'no_registrar_msg_check',
                role=UserRole.CONTRIBUTOR,
                registered_by=None,
            )
        message = str(ctx.exception)
        self.assertIn('registered_by', message)

    # --- Exemption case (superuser may have null registered_by) ---

    def test_superuser_with_null_registered_by_is_allowed(self):
        """Superuser creation must never be blocked by the signal."""
        try:
            su = make_user(
                'exempt_superuser',
                role=UserRole.SUPERUSER,
                registered_by=None,
            )
        except ValidationError:
            self.fail(
                'Signal incorrectly rejected a superuser with null registered_by.'
            )
        self.assertIsNone(su.registered_by)

    # --- Acceptance cases (non-superuser roles with registered_by set) ---

    def test_contributor_with_registered_by_is_saved(self):
        user = make_user(
            'valid_contrib',
            role=UserRole.CONTRIBUTOR,
            registered_by=self.registrar,
        )
        user.refresh_from_db()
        self.assertEqual(user.registered_by, self.registrar)

    def test_editor_with_registered_by_is_saved(self):
        user = make_user(
            'valid_editor',
            role=UserRole.EDITOR,
            registered_by=self.registrar,
        )
        user.refresh_from_db()
        self.assertEqual(user.registered_by, self.registrar)

    def test_admin_with_registered_by_is_saved(self):
        user = make_user(
            'valid_admin',
            role=UserRole.ADMIN,
            registered_by=self.registrar,
        )
        user.refresh_from_db()
        self.assertEqual(user.registered_by, self.registrar)

    # --- Signal fires on UPDATE as well as INSERT ---

    def test_clearing_registered_by_on_existing_user_raises(self):
        """
        Signal fires on save() regardless of INSERT vs UPDATE.
        Clearing registered_by on an existing non-superuser must be rejected.
        """
        user = make_user('will_be_cleared', role=UserRole.CONTRIBUTOR)
        user.registered_by = None
        with self.assertRaises(ValidationError) as ctx:
            user.save()
        self.assertIn('registered_by', ctx.exception.message_dict)

    def test_updating_other_fields_does_not_break_existing_user(self):
        """
        A normal field update on a user who already has registered_by
        set must pass the signal without error.
        """
        user = make_user('stable_user', role=UserRole.CONTRIBUTOR)
        user.registration_notes = 'Updated note after signal added.'
        try:
            user.save()
        except ValidationError:
            self.fail(
                'Signal incorrectly rejected a valid update on a user '
                'who already has registered_by set.'
            )

# ===========================================================================
# SpeakerProfile — creation
# ===========================================================================

class SpeakerProfileCreationTests(TestCase):
    fixtures = ['infrastructure/communities.json']

    def setUp(self):
        self.documenter = make_user('doc_editor', role=UserRole.EDITOR)
        self.community  = Community.objects.get(name='kalaba')

    def test_create_minimal_speaker_profile(self):
        sp = SpeakerProfile.objects.create(
            full_name='Ebibuna Teteh',
            documented_by=self.documenter,
        )
        self.assertEqual(sp.full_name, 'Ebibuna Teteh')
        self.assertIsNone(sp.village)
        self.assertIsNone(sp.birth_year)
        self.assertTrue(sp.is_living)
        self.assertIsNone(sp.user_account)

    def test_create_full_speaker_profile(self):
        user = make_user('linked_speaker', role=UserRole.CONTRIBUTOR)
        sp = SpeakerProfile.objects.create(
            full_name='Angela Erigi',
            clan_name='Akita-Ama',
            village=self.community,
            birth_year=1960,
            is_living=True,
            user_account=user,
            documented_by=self.documenter,
        )
        sp.refresh_from_db()
        self.assertEqual(sp.clan_name, 'Akita-Ama')
        self.assertEqual(sp.village, self.community)
        self.assertEqual(sp.birth_year, 1960)
        self.assertEqual(sp.user_account, user)

    def test_deceased_speaker(self):
        sp = SpeakerProfile.objects.create(
            full_name='Elder Okonkwo',
            birth_year=1930,
            is_living=False,
            documented_by=self.documenter,
        )
        self.assertFalse(sp.is_living)

    def test_speaker_without_user_account(self):
        sp = SpeakerProfile.objects.create(
            full_name='Unknown Elder',
            documented_by=self.documenter,
        )
        self.assertIsNone(sp.user_account)

    def test_user_account_is_one_to_one(self):
        """A user can only be linked to one speaker profile."""
        user = make_user('unique_speaker')
        SpeakerProfile.objects.create(
            full_name='First Profile',
            user_account=user,
            documented_by=self.documenter,
        )
        with self.assertRaises(Exception):
            SpeakerProfile.objects.create(
                full_name='Duplicate Profile',
                user_account=user,
                documented_by=self.documenter,
            )


# ===========================================================================
# SpeakerProfile — __str__ and ordering
# ===========================================================================

class SpeakerProfileStrTests(TestCase):

    def setUp(self):
        self.documenter = make_user('doc2', role=UserRole.EDITOR)

    def test_str_returns_full_name(self):
        sp = SpeakerProfile.objects.create(
            full_name='Ngozi Eze',
            documented_by=self.documenter,
        )
        self.assertEqual(str(sp), 'Ngozi Eze')

    def test_default_ordering_is_by_full_name(self):
        SpeakerProfile.objects.create(full_name='Zara X', documented_by=self.documenter)
        SpeakerProfile.objects.create(full_name='Ada Y',  documented_by=self.documenter)
        names = list(SpeakerProfile.objects.values_list('full_name', flat=True))
        self.assertEqual(names, sorted(names))


# ===========================================================================
# SpeakerProfile — documented_by FK cascade behaviour
# ===========================================================================

class SpeakerProfileFKTests(TestCase):

    def test_documented_by_set_null_on_user_delete(self):
        doc = make_user('will_be_deleted', role=UserRole.EDITOR)
        sp  = SpeakerProfile.objects.create(
            full_name='Orphaned Speaker',
            documented_by=doc,
        )
        doc.delete()
        sp.refresh_from_db()
        self.assertIsNone(sp.documented_by)

    def test_village_set_null_on_community_delete(self):
        from apps.infrastructure.core.models import Community
        c = Community.objects.create(name='ayamabele')
        doc = make_user('doc3', role=UserRole.EDITOR)
        sp  = SpeakerProfile.objects.create(
            full_name='Village Speaker',
            village=c,
            documented_by=doc,
        )
        c.delete()
        sp.refresh_from_db()
        self.assertIsNone(sp.village)
