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
from django.db import IntegrityError
from apps.identity.users.models import AkitaUser, SpeakerProfile, UserRole
from apps.infrastructure.core.models import Community


def make_user(username, role=UserRole.CONTRIBUTOR, **kwargs):
    """
    Utility helper to build standardized user accounts for isolation tests.
    Automatically assigns or establishes a bootstrap registrar to satisfy 
    the pre_save account audit constraint.
    """
    if role == UserRole.SUPERUSER:
        return AkitaUser.objects.create_superuser(username=username, **kwargs)
        
    # Retrieve or bootstrap an initial record to fulfill the mandatory registered_by dependency
    registrar, _ = AkitaUser.objects.get_or_create(
        username='test_bootstrap_registrar',
        defaults={'role': UserRole.SUPERUSER, 'is_superuser': True, 'is_staff': True}
    )
    kwargs.setdefault('registered_by', registrar)
    return AkitaUser.objects.create_user(username=username, role=role, **kwargs)


# ===========================================================================
# AkitaUser — role level
# ===========================================================================

class UserRoleLevelTests(TestCase):

    def setUp(self):
        self.admin_user = make_user(username='admin', role=UserRole.ADMIN)
        self.contributor_user = make_user(username='contrib', role=UserRole.CONTRIBUTOR)
        self.editor_user = make_user(username='editor', role=UserRole.EDITOR)
        self.superuser_user = make_user(username='super', role=UserRole.SUPERUSER)

    def test_contributor_level_is_1(self):
        self.assertEqual(self.contributor_user.get_role_level(), 1)

    def test_editor_level_is_2(self):
        self.assertEqual(self.editor_user.get_role_level(), 2)

    def test_admin_level_is_3(self):
        self.assertEqual(self.admin_user.get_role_level(), 3)

    def test_superuser_level_is_4(self):
        self.assertEqual(self.superuser_user.get_role_level(), 4)


# ===========================================================================
# AkitaUser — can_register_users
# ===========================================================================

class CanRegisterUsersTests(TestCase):

    def setUp(self):
        self.system_initializer = make_user(username='root_reg', role=UserRole.SUPERUSER)
        self.admin_user = make_user(username='admin_reg', role=UserRole.ADMIN)
        self.editor_user = make_user(username='editor_reg', role=UserRole.EDITOR)
        self.contributor_user = make_user(username='contrib_reg', role=UserRole.CONTRIBUTOR)

    def test_contributor_cannot_register(self):
        self.assertFalse(self.contributor_user.can_register_users())

    def test_editor_can_register(self):
        self.assertTrue(self.editor_user.can_register_users())

    def test_admin_can_register(self):
        self.assertTrue(self.admin_user.can_register_users())

    def test_superuser_can_register(self):
        self.assertTrue(self.system_initializer.can_register_users())


# ===========================================================================
# AkitaUser — can_elevate_user
# ===========================================================================

class CanElevateUserTests(TestCase):

    def setUp(self):
        self.admin_user = make_user(username='admin_elevate', role=UserRole.ADMIN)
        self.system_initializer = make_user(username='root_elevate', role=UserRole.SUPERUSER)

    def test_superuser_can_elevate_anyone(self):
        another_admin = make_user(username='admin2', role=UserRole.ADMIN)
        self.assertTrue(self.system_initializer.can_elevate_user(another_admin))

    def test_admin_cannot_elevate_superuser(self):
        self.assertFalse(self.admin_user.can_elevate_user(self.system_initializer))

    def test_admin_cannot_elevate_another_admin(self):
        another_admin = make_user(username='admin3', role=UserRole.ADMIN)
        self.assertFalse(self.admin_user.can_elevate_user(another_admin))

    def test_admin_can_elevate_contributor(self):
        contrib = make_user(username='contrib2', role=UserRole.CONTRIBUTOR)
        self.assertTrue(self.admin_user.can_elevate_user(contrib))

    def test_editor_cannot_elevate_contributor(self):
        editor = make_user(username='editor2', role=UserRole.EDITOR)
        contrib = make_user(username='contrib3', role=UserRole.CONTRIBUTOR)
        self.assertFalse(editor.can_elevate_user(contrib))

    def test_can_elevate_none_target_returns_false(self):
        self.assertFalse(self.admin_user.can_elevate_user(None))

    def test_cannot_elevate_anonymous_level_zero(self):
        from django.contrib.auth.models import AnonymousUser
        odd_user = AnonymousUser()
        self.assertFalse(self.admin_user.can_elevate_user(odd_user))


# ===========================================================================
# AkitaUser — can_manage_user
# ===========================================================================

class CanManageUserTests(TestCase):

    def setUp(self):
        self.system_initializer = make_user(username='root_manage', role=UserRole.SUPERUSER)
        self.admin_user = make_user(username='admin_manage', role=UserRole.ADMIN)

    def test_higher_role_can_manage_lower(self):
        self.assertTrue(self.system_initializer.can_manage_user(self.admin_user))

    def test_lower_role_cannot_manage_higher(self):
        self.assertFalse(self.admin_user.can_manage_user(self.system_initializer))

    def test_same_role_cannot_manage(self):
        another_admin = make_user(username='admin_manage2', role=UserRole.ADMIN)
        self.assertFalse(self.admin_user.can_manage_user(another_admin))

    def test_none_target_returns_false(self):
        self.assertFalse(self.admin_user.can_manage_user(None))


# ===========================================================================
# AkitaUser — can_approve_own
# ===========================================================================

class CanApproveOwnTests(TestCase):

    def setUp(self):
        self.editor_user = make_user(username='editor_approve', role=UserRole.EDITOR)
        self.contributor_user = make_user(username='contrib_approve', role=UserRole.CONTRIBUTOR)

    def test_user_cannot_approve_own_upload(self):
        self.assertFalse(self.contributor_user.can_approve_own(self.contributor_user))

    def test_user_can_approve_other_users_upload(self):
        self.assertTrue(self.editor_user.can_approve_own(self.contributor_user))


# ===========================================================================
# AkitaUser — full_name property
# ===========================================================================

class UserFullNameTests(TestCase):

    def setUp(self):
        self.admin_user = make_user(username='admin_fullname', role=UserRole.ADMIN)

    def test_full_name_returns_first_and_last(self):
        user = AkitaUser.objects.create_user(
            username='jdoe',
            password='testpass123',
            first_name='John',
            last_name='Doe',
            registered_by=self.admin_user
        )
        self.assertEqual(user.full_name, 'John Doe')

    def test_full_name_empty_when_names_not_set(self):
        user = AkitaUser.objects.create_user(
            username='noname',
            password='testpass123',
            registered_by=self.admin_user
        )
        self.assertEqual(user.full_name, '')


# ===========================================================================
# AkitaUser — __str__
# ===========================================================================

class UserStrTests(TestCase):

    def setUp(self):
        self.system_initializer = make_user(username='root_str', role=UserRole.SUPERUSER)

    def test_str_includes_username_and_role_display(self):
        user = AkitaUser.objects.create_user(
            username='ada',
            password='testpass123',
            role=UserRole.ADMIN,
            registered_by=self.system_initializer
        )
        self.assertIn('ada', str(user))
        self.assertIn('Admin', str(user))


# ===========================================================================
# AkitaUser — manager: create_user
# ===========================================================================

class AkitaUserManagerTests(TestCase):

    def setUp(self):
        self.system_initializer = make_user(username='root_mgr', role=UserRole.SUPERUSER)
        self.admin_user = make_user(username='admin_mgr', role=UserRole.ADMIN)

    def test_create_user_defaults_to_contributor(self):
        user = AkitaUser.objects.create_user(
            username='newbie',
            password='pass',
            registered_by=self.admin_user
        )
        self.assertEqual(user.role, UserRole.CONTRIBUTOR)

    def test_create_user_without_username_raises(self):
        with self.assertRaises(ValueError):
            AkitaUser.objects.create_user(username='', password='pass')

    def test_create_superuser_sets_flags(self):
        su = AkitaUser.objects.create_superuser(
            username='rootuser',
            password='strongpass',
            registered_by=self.system_initializer
        )
        self.assertTrue(su.is_staff)
        self.assertTrue(su.is_superuser)
        self.assertEqual(su.role, UserRole.SUPERUSER)

    def test_create_superuser_requires_is_staff_true(self):
        with self.assertRaises(ValueError):
            AkitaUser.objects.create_superuser(
                username='bad_su',
                password='pass',
                is_staff=False
            )

    def test_create_superuser_requires_is_superuser_true(self):
        with self.assertRaises(ValueError):
            AkitaUser.objects.create_superuser(
                username='bad_su2',
                password='pass',
                is_superuser=False
            )

    def test_email_is_normalised_on_create(self):
        user = AkitaUser.objects.create_user(
            username='emailuser',
            password='pass',
            email='Test@EXAMPLE.COM',
            registered_by=self.admin_user
        )
        self.assertEqual(user.email, 'Test@example.com')

    def test_none_email_stored_as_empty(self):
        user = AkitaUser.objects.create_user(
            username='noemail',
            password='pass',
            email=None,
            registered_by=self.admin_user
        )
        self.assertIsNone(user.email)
        
        
# ===========================================================================
# AkitaUser — elevation tracking fields
# ===========================================================================

class UserElevationFieldTests(TestCase):

    def setUp(self):
        self.admin_user = make_user(username='admin_elevation', role=UserRole.ADMIN)
        self.contributor_user = make_user(username='contrib_elevation', role=UserRole.CONTRIBUTOR)

    def test_elevation_fields_null_by_default(self):
        self.assertIsNone(self.contributor_user.elevated_by)
        self.assertIsNone(self.contributor_user.elevated_at)
        self.assertEqual(self.contributor_user.elevation_notes, '')

    def test_elevation_fields_persist(self):
        now = timezone.now()
        self.contributor_user.role = UserRole.EDITOR
        self.contributor_user.elevated_by = self.admin_user
        self.contributor_user.elevated_at = now
        self.contributor_user.elevation_notes = 'Promoted after review'
        self.contributor_user.save()

        self.contributor_user.refresh_from_db()
        self.assertEqual(self.contributor_user.elevated_by, self.admin_user)
        self.assertEqual(self.contributor_user.elevation_notes, 'Promoted after review')


# ===========================================================================
# AkitaUser — registered_by signal enforcement
# ===========================================================================

class RegisteredBySignalTests(TestCase):
    """Isolates accountability checks during user creation lifecycle layers."""

    def test_contributor_with_null_registered_by_raises(self):
        with self.assertRaises(ValidationError) as ctx:
            AkitaUser.objects.create_user(
                username='no_registrar_contrib',
                password='testpass123',
                role=UserRole.CONTRIBUTOR,
                registered_by=None,
            )
        self.assertIn('registered_by', ctx.exception.message_dict)

    def test_superuser_with_null_registered_by_is_allowed(self):
        try:
            su = AkitaUser.objects.create_superuser(
                username='exempt_superuser',
                password='testpass123',
                registered_by=None,
            )
        except ValidationError:
            self.fail('Signal incorrectly rejected a superuser with null registered_by.')
        self.assertIsNone(su.registered_by)

    def test_clearing_registered_by_on_existing_user_raises(self):
        bootstrap_su = AkitaUser.objects.create_superuser(username='b_su', password='p')
        user = AkitaUser.objects.create_user(
            username='will_be_cleared',
            password='testpass123',
            role=UserRole.CONTRIBUTOR,
            registered_by=bootstrap_su
        )
        user.registered_by = None
        with self.assertRaises(ValidationError) as ctx:
            user.save()
        self.assertIn('registered_by', ctx.exception.message_dict)


# ===========================================================================
# SpeakerProfile — creation & constraints
# ===========================================================================

class SpeakerProfileCreationTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.community = Community.objects.create(name='kalaba')

    def setUp(self):
        self.editor_user = make_user(username='editor_speaker', role=UserRole.EDITOR)
        self.contributor_user = make_user(username='contrib_speaker', role=UserRole.CONTRIBUTOR)

    def test_create_minimal_speaker_profile(self):
        sp = SpeakerProfile.objects.create(
            full_name='Ebibuna Teteh',
            documented_by=self.editor_user,
        )
        self.assertEqual(sp.full_name, 'Ebibuna Teteh')
        self.assertIsNone(sp.community)
        self.assertIsNone(sp.birth_year)
        self.assertTrue(sp.is_living)
        self.assertIsNone(sp.speaker_user_account)

    def test_create_full_speaker_profile(self):
        sp = SpeakerProfile.objects.create(
            full_name='Angela Erigi',
            community=self.community,
            birth_year=1960,
            is_living=True,
            speaker_user_account=self.contributor_user,
            documented_by=self.editor_user,
        )
        sp.refresh_from_db()
        self.assertEqual(sp.community, self.community)
        self.assertEqual(sp.birth_year, 1960)
        self.assertEqual(sp.speaker_user_account, self.contributor_user)

    def test_speaker_with_external_community_note(self):
        sp = SpeakerProfile.objects.create(
            full_name='Pere Okoro',
            community_note='Peremabiri',
            documented_by=self.editor_user
        )
        self.assertEqual(sp.community_note, 'Peremabiri')
        self.assertIsNone(sp.community)

    def test_community_mutex_validation_raises_clean_error(self):
        sp = SpeakerProfile(
            full_name='Confused Speaker',
            community=self.community,
            community_note='Ekeremor',
            documented_by=self.editor_user
        )
        with self.assertRaises(ValidationError):
            sp.clean()

    def test_community_mutex_database_constraint(self):
        sp = SpeakerProfile(
            full_name='Invalid Db Entry',
            community=self.community,
            community_note='Ekeremor',
            documented_by=self.editor_user
        )
        with self.assertRaises(IntegrityError):
            sp.save()

    def test_speaker_user_account_is_one_to_one(self):
        SpeakerProfile.objects.create(
            full_name='First Profile',
            speaker_user_account=self.contributor_user,
            documented_by=self.editor_user,
        )
        with self.assertRaises(IntegrityError):
            SpeakerProfile.objects.create(
                full_name='Duplicate Profile',
                speaker_user_account=self.contributor_user,
                documented_by=self.editor_user,
            )


# ===========================================================================
# SpeakerProfile — __str__ and ordering
# ===========================================================================

class SpeakerProfileStrAndOrderingTests(TestCase):

    def setUp(self):
        self.editor_user = make_user(username='editor_str_ordering', role=UserRole.EDITOR)

    def test_str_returns_full_name(self):
        sp = SpeakerProfile.objects.create(
            full_name='Ngozi Eze',
            documented_by=self.editor_user,
        )
        self.assertEqual(str(sp), 'Ngozi Eze')

    def test_default_ordering_is_by_full_name(self):
        SpeakerProfile.objects.create(full_name='Zara X', documented_by=self.editor_user)
        SpeakerProfile.objects.create(full_name='Ada Y',  documented_by=self.editor_user)
        
        names = list(SpeakerProfile.objects.values_list('full_name', flat=True))
        self.assertEqual(names, sorted(names))


# ===========================================================================
# SpeakerProfile — FK cascade behaviour
# ===========================================================================

class SpeakerProfileFKTests(TestCase):

    def setUp(self):
        self.admin_user = make_user(username='admin_fk_cascade', role=UserRole.ADMIN)
        self.editor_user = make_user(username='editor_fk_cascade', role=UserRole.EDITOR)

    def test_documented_by_set_null_on_user_delete(self):
        transient_doc = AkitaUser.objects.create_user(
            username='will_be_deleted',
            password='testpass123',
            role=UserRole.EDITOR,
            registered_by=self.admin_user
        )
        sp = SpeakerProfile.objects.create(
            full_name='Orphaned Speaker',
            documented_by=transient_doc,
        )
        transient_doc.delete()
        sp.refresh_from_db()
        self.assertIsNone(sp.documented_by)

    def test_community_set_null_on_community_delete(self):
        c = Community.objects.create(name='ayamabele')
        sp = SpeakerProfile.objects.create(
            full_name='Village Speaker',
            community=c,
            documented_by=self.editor_user,
        )
        c.delete()
        sp.refresh_from_db()
        self.assertIsNone(sp.community)
        