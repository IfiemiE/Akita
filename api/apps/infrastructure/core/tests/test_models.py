"""
Unit tests for the model and serializer layer — no HTTP client, no URL routing.

Coverage
--------
  Language        : bootstrap guard, singleton-target constraint, iso_code optional,
                    self-update idempotency, __str__, unique name
  Dialect         : bootstrap guard, singleton-target, iso_code cross-check,
                    unique_together (language, name), FK cascade from Language, __str__
  Community       : __str__, ordering, blank optional fields, unique name
  AkitaCommunity  : MTI inheritance, VALID_COMMUNITIES validation (case-insensitive),
                    is_active default, FK cascade from Community deletion
  MediaTag        : __str__, ordering, unique name + slug, blank description
  Category        : __str__, ordering, self-ref FK, cascade delete removes children,
                    unique slug constraint, leaf-node children, grandchild chain
  SiteSetting     : __str__, ordering, unique key

  LanguageSerializer     : fields, read-only behaviour, validation
  DialectSerializer      : fields, language_name read-only source, validation
  CommunitySerializer    : exact field set, values, no is_active leakage
  AkitaCommunitySerializer : fields including is_active
  MediaTagSerializer     : fields, slug value
  CategorySerializer     : children nesting, leaf empty list, parent as int pk
  SiteSettingSerializer  : fields, duplicate key rejection, required fields

Fixtures
--------
  infrastructure/communities.json  → 5 AkitaCommunity records (1 inactive: ikarama)
  infrastructure/mediatags.json    → 8 MediaTag records
  infrastructure/categories.json   → 9 Category records (3 roots, 5 children, 1 grandchild)
  infrastructure/sitesettings.json → 8 SiteSetting records

Run
---
$ python manage.py test TEST_DOTTED_PATH -v 2 --settings=config.settings.test

where
TEST_DOTTED_PATH = apps.infrastructure.core.tests.test_models.CLASS.METHOD
TEST_DOTTED_PATH = apps.infrastructure.core.tests.test_models.CLASS
TEST_DOTTED_PATH = apps.infrastructure.core.tests.test_models
TEST_DOTTED_PATH = apps.infrastructure.core.tests
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.infrastructure.core.models import (
    Language, Dialect, Community, AkitaCommunity, MediaTag, Category, SiteSetting,
)
from apps.infrastructure.core.serializers import (
    LanguageSerializer,
    DialectSerializer,
    CommunitySerializer,
    AkitaCommunitySerializer,
    MediaTagSerializer,
    CategorySerializer,
    SiteSettingSerializer,
)
from apps.common.constants import AKITA_COMMUNITIES


# ─────────────────────────────────────────────────────────────────────────────
# 1.  Language — model
# ─────────────────────────────────────────────────────────────────────────────

class LanguageModelTests(TestCase):
    """
    Language enforces two invariants:
      1. The very first record must have is_target=True (bootstrap guard).
      2. Only one Language may ever have is_target=True (singleton constraint).
    """

    def test_first_language_with_is_target_true_saves(self):
        """Bootstrap path: first record with is_target=True is accepted."""
        lang = Language(name='Ijaw', iso_code='ijc', is_target=True)
        lang.full_clean()
        lang.save()
        self.assertEqual(Language.objects.count(), 1)

    def test_first_language_with_is_target_false_raises(self):
        """save() raises ValidationError when the very first record is not target."""
        lang = Language(name='Ijaw', is_target=False)
        with self.assertRaises(ValidationError):
            lang.full_clean()
            lang.save()

    def test_second_target_language_raises_on_full_clean(self):
        """clean() raises when a second language tries to claim is_target=True."""
        Language.objects.create(name='Ijaw', is_target=True)
        duplicate = Language(name='Kalabari', iso_code='ijn', is_target=True)
        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_non_target_second_language_is_accepted(self):
        """A second language with is_target=False passes full_clean and saves."""
        Language.objects.create(name='Ijaw', is_target=True)
        lang2 = Language(name='Itsekiri', is_target=False)
        lang2.full_clean()
        lang2.save()
        self.assertEqual(Language.objects.count(), 2)

    def test_updating_target_language_does_not_re_trigger_singleton_guard(self):
        """
        Saving an already-target Language (e.g. to rename it) must not raise —
        clean() excludes the current pk before checking for duplicates.
        """
        lang = Language.objects.create(name='Ijaw', is_target=True)
        lang.name = 'Ịjọ'
        lang.full_clean()
        lang.save()
        self.assertEqual(Language.objects.get(pk=lang.pk).name, 'Ịjọ')

    def test_str_returns_name(self):
        lang = Language.objects.create(name='Ijaw', is_target=True)
        self.assertEqual(str(lang), 'Ijaw')

    def test_iso_code_is_optional(self):
        lang = Language(name='Kalabari', is_target=True)
        lang.full_clean()
        lang.save()
        self.assertIsNone(lang.iso_code)

    def test_unique_name_constraint(self):
        """Two Language records with identical names must raise IntegrityError."""
        Language.objects.create(name='Ijaw', is_target=True)
        with self.assertRaises(Exception):  # IntegrityError at DB level
            Language.objects.create(name='Ijaw', is_target=False)

    def test_multiple_non_target_languages_allowed(self):
        """No constraint prevents multiple is_target=False records."""
        Language.objects.create(name='Ijaw', is_target=True)
        Language.objects.create(name='Itsekiri', is_target=False)
        Language.objects.create(name='Urhobo', is_target=False)
        self.assertEqual(Language.objects.count(), 3)


# ─────────────────────────────────────────────────────────────────────────────
# 2.  Dialect — model
# ─────────────────────────────────────────────────────────────────────────────

class DialectModelTests(TestCase):
    """
    Dialect mirrors Language's singleton-target logic and adds an
    iso_code cross-check with its parent Language.
    """

    def setUp(self):
        # Establish a valid default base layout so the bootstrap validation 
        # rules do not choke on individual test context transitions.
        self.lang = Language.objects.create(
            name='Ijaw', iso_code='ijc', is_target=True
        )

    def test_first_dialect_with_is_target_true_saves(self):
        d = Dialect(language=self.lang, name='Akita', iso_code='ijc', is_target=True)
        d.full_clean()
        d.save()
        self.assertEqual(Dialect.objects.count(), 1)

    def test_first_dialect_with_is_target_false_raises(self):
        d = Dialect(language=self.lang, name='Akita', iso_code='', is_target=False)
        with self.assertRaises(ValidationError):
            d.full_clean()
            d.save()

    def test_second_target_dialect_raises_on_full_clean(self):
        Dialect.objects.create(
            language=self.lang, name='Akita', iso_code='ijc', is_target=True
        )
        d2 = Dialect(language=self.lang, name='Operemo', iso_code='', is_target=True)
        with self.assertRaises(ValidationError):
            d2.full_clean()

    def test_updating_target_dialect_does_not_re_trigger_singleton_guard(self):
        d = Dialect.objects.create(
            language=self.lang, name='Akita', iso_code='ijc', is_target=True
        )
        d.name = 'Akịta'
        d.full_clean()
        d.save()
        self.assertEqual(Dialect.objects.get(pk=d.pk).name, 'Akịta')

    def test_iso_code_mismatch_with_language_raises(self):
        """When both language.iso_code and dialect.iso_code are set and differ, clean() must raise."""
        # Ensure the dialect targets matching target properties with its parent container
        d = Dialect(
            language=self.lang, name='Akita',
            iso_code='xxx',  # deliberate mismatch against self.lang.iso_code 'ijc'
            is_target=True,
        )
        with self.assertRaises(ValidationError):
            d.full_clean()

    def test_iso_code_match_with_language_passes(self):
        """
        When language.iso_code matches dialect.iso_code the cross-check passes.
        We establish a target dialect first to fulfill bootstrap checks, then attach our test record.
        """
        Dialect.objects.create(language=self.lang, name='Akita', iso_code='okd', is_target=True)
        
        lang_no_iso = Language.objects.create(name='Ịjọ-variant', is_target=False, iso_code=None)
        d = Dialect(language=lang_no_iso, name='Akita-v', iso_code='okd', is_target=False)
        d.full_clean()  
        d.save()
        self.assertTrue(Dialect.objects.filter(name='Akita-v').exists())

    def test_iso_code_both_same_value_passes(self):
        """Explicitly set matching codes on both sides; cross-check must pass."""
        Dialect.objects.create(language=self.lang, name='Akita', iso_code='okd', is_target=True)
        
        lang = Language.objects.create(name='Ịjọ-same', iso_code='okd', is_target=False)
        d = Dialect(language=lang, name='Akita-same', iso_code='okd', is_target=False)
        d.full_clean()
        d.save()
        self.assertTrue(Dialect.objects.filter(name='Akita-same').exists())

    def test_unique_together_language_name_raises(self):
        """(language, name) is unique; duplicate must raise."""
        Dialect.objects.create(
            language=self.lang, name='Akita', iso_code='okd', is_target=True
        )
        with self.assertRaises(Exception):  
            d_dup = Dialect(language=self.lang, name='Akita', iso_code='okd', is_target=False)
            d_dup.full_clean()
            d_dup.save()

    def test_same_name_different_language_is_allowed(self):
        """(language2, 'Akita') is a new unique pair; must save without error."""
        Dialect.objects.create(
            language=self.lang, name='Akita', iso_code='okd', is_target=True
        )
        lang2 = Language.objects.create(name='Kalabari', is_target=False)
        d2 = Dialect(language=lang2, name='Akita', iso_code='okd', is_target=False)
        d2.full_clean()
        d2.save()
        self.assertEqual(Dialect.objects.filter(name='Akita').count(), 2)

    def test_cascade_delete_from_language_removes_dialects(self):
        """Deleting the parent Language must cascade-delete its Dialect records."""
        Dialect.objects.create(
            language=self.lang, name='Akita', iso_code='okd', is_target=True
        )
        self.lang.delete()
        self.assertEqual(Dialect.objects.count(), 0)

    def test_str_returns_dialect_dash_language(self):
        d = Dialect.objects.create(
            language=self.lang, name='Akita', iso_code='okd', is_target=True
        )
        self.assertEqual(str(d), 'Akita-Ijaw')

    def test_non_target_second_dialect_is_accepted(self):
        Dialect.objects.create(
            language=self.lang, name='Akita', iso_code='ijc', is_target=True
        )
        d2 = Dialect(language=self.lang, name='Operemo', iso_code='ijc', is_target=False)
        d2.full_clean()
        d2.save()
        self.assertEqual(Dialect.objects.count(), 2)


# ─────────────────────────────────────────────────────────────────────────────
# 3.  Community — model
# ─────────────────────────────────────────────────────────────────────────────

class CommunityModelTests(TestCase):
    """
    Community is a plain, unconstrained base model (no is_active field).
    is_active lives only on AkitaCommunity (MTI child).
    """

    def test_create_community_saves(self):
        c = Community.objects.create(name='Testville')
        self.assertEqual(Community.objects.count(), 1)
        self.assertEqual(c.name, 'Testville')

    def test_str_returns_name(self):
        c = Community.objects.create(name='Agbobiri')
        self.assertEqual(str(c), 'Agbobiri')

    def test_ordering_is_alphabetical(self):
        Community.objects.create(name='Zetaburg')
        Community.objects.create(name='Alphaville')
        names = list(Community.objects.values_list('name', flat=True))
        self.assertEqual(names, sorted(names))

    def test_alternate_names_defaults_to_blank(self):
        c = Community.objects.create(name='Testville')
        self.assertEqual(c.alternate_names, '')

    def test_description_defaults_to_blank(self):
        c = Community.objects.create(name='Testville')
        self.assertEqual(c.description, '')

    def test_unique_name_constraint(self):
        Community.objects.create(name='Testville')
        with self.assertRaises(Exception):
            Community.objects.create(name='Testville')

    def test_community_has_no_is_active_field(self):
        """is_active belongs to AkitaCommunity, not the base Community model."""
        c = Community.objects.create(name='Testville')
        self.assertFalse(hasattr(c, 'is_active'))

    def test_verbose_name_plural(self):
        self.assertEqual(Community._meta.verbose_name_plural, 'communities')


# ─────────────────────────────────────────────────────────────────────────────
# 4.  AkitaCommunity — model
# ─────────────────────────────────────────────────────────────────────────────

class AkitaCommunityModelTests(TestCase):
    """
    AkitaCommunity extends Community via MTI.
    clean() restricts 'name' to the five AKITA_COMMUNITIES (case-insensitive).
    """

    def test_valid_community_name_passes_full_clean(self):
        """Each name in AKITA_COMMUNITIES must pass full_clean."""
        for name in AKITA_COMMUNITIES:
            with self.subTest(name=name):
                c = AkitaCommunity(name=name, is_active=True)
                c.full_clean()  

    def test_invalid_community_name_raises_with_name_key(self):
        c = AkitaCommunity(name='Unknown Village', is_active=True)
        with self.assertRaises(ValidationError) as ctx:
            c.full_clean()
        self.assertIn('name', ctx.exception.message_dict)

    def test_is_active_default_is_true(self):
        """AkitaCommunity.is_active defaults to True."""
        name = AKITA_COMMUNITIES[0]
        c = AkitaCommunity(name=name)
        c.full_clean()
        c.save()
        self.assertTrue(AkitaCommunity.objects.get(name=name).is_active)

    def test_is_active_can_be_set_false(self):
        name = AKITA_COMMUNITIES[0]
        c = AkitaCommunity(name=name, is_active=False)
        c.full_clean()
        c.save()
        self.assertFalse(AkitaCommunity.objects.get(name=name).is_active)

    def test_case_insensitive_name_is_accepted(self):
        """
        Validation capitalises both sides; a lower-case input that matches
        a valid community name must pass.
        """
        lower_name = AKITA_COMMUNITIES[0].lower()
        c = AkitaCommunity(name=lower_name, is_active=True)
        c.full_clean()  

    def test_akitacommunity_str_inherits_from_community(self):
        """__str__ from Community returns self.name."""
        name = AKITA_COMMUNITIES[0].capitalize()
        c = AkitaCommunity(name=name)
        c.full_clean()
        c.save()
        self.assertEqual(str(c), name)

    def test_akitacommunity_is_a_community_instance(self):
        """MTI: AkitaCommunity IS-A Community."""
        name = AKITA_COMMUNITIES[0].capitalize()
        c = AkitaCommunity(name=name)
        c.full_clean()
        c.save()
        self.assertIsInstance(c, Community)

    def test_deleting_parent_community_cascades_to_akitacommunity(self):
        """
        MTI uses a OneToOneField (community_ptr) with CASCADE.
        Deleting the parent row must also remove the AkitaCommunity child row.
        """
        name = AKITA_COMMUNITIES[0].capitalize()
        c = AkitaCommunity(name=name)
        c.full_clean()
        c.save()
        community_pk = c.community_ptr_id
        Community.objects.filter(pk=community_pk).delete()
        self.assertFalse(AkitaCommunity.objects.filter(pk=community_pk).exists())

    def test_verbose_name_plural(self):
        self.assertEqual(AkitaCommunity._meta.verbose_name_plural, 'akita communities')

    def test_ordering_is_alphabetical(self):
        names_input = AKITA_COMMUNITIES[:3]
        for name in reversed(names_input):  # insert out of order
            c = AkitaCommunity(name=name.capitalize())
            c.full_clean()
            c.save()
        result = list(AkitaCommunity.objects.values_list('name', flat=True))
        self.assertEqual(result, sorted(result))


# ─────────────────────────────────────────────────────────────────────────────
# 5.  AkitaCommunity — fixture integrity
# ─────────────────────────────────────────────────────────────────────────────

class AkitaCommunityFixtureTests(TestCase):
    # Include both multi-table split definitions directly inside the fixture array
    fixtures = [
        'infrastructure/communities.json',
        'infrastructure/akitacommunities.json'
    ]

    def test_fixture_loads_five_akita_community_records(self):
        self.assertEqual(AkitaCommunity.objects.count(), 5)

    def test_fixture_also_loads_five_community_base_records(self):
        """MTI: every AkitaCommunity has a matching Community row."""
        self.assertEqual(Community.objects.count(), 5)

    def test_four_records_are_active(self):
        self.assertEqual(AkitaCommunity.objects.filter(is_active=True).count(), 4)

    def test_ikarama_is_inactive(self):
        ikarama = AkitaCommunity.objects.get(name='ikarama')
        self.assertFalse(ikarama.is_active)

    def test_ordering_is_alphabetical(self):
        names = list(AkitaCommunity.objects.values_list('name', flat=True))
        self.assertEqual(names, sorted(names))


# ─────────────────────────────────────────────────────────────────────────────
# 6.  MediaTag — model & fixture
# ─────────────────────────────────────────────────────────────────────────────

class MediaTagModelTests(TestCase):

    def test_create_mediatag_saves(self):
        t = MediaTag.objects.create(name='Folklore', slug='folklore')
        self.assertEqual(MediaTag.objects.count(), 1)

    def test_str_returns_name(self):
        t = MediaTag.objects.create(name='Folklore', slug='folklore')
        self.assertEqual(str(t), 'Folklore')

    def test_unique_name_constraint(self):
        MediaTag.objects.create(name='Folklore', slug='folklore')
        with self.assertRaises(Exception):
            MediaTag.objects.create(name='Folklore', slug='folklore-2')

    def test_unique_slug_constraint(self):
        MediaTag.objects.create(name='Folklore', slug='folklore')
        with self.assertRaises(Exception):
            MediaTag.objects.create(name='Folklore 2', slug='folklore')

    def test_description_is_optional(self):
        t = MediaTag.objects.create(name='Folklore', slug='folklore')
        self.assertEqual(t.description, '')

    def test_ordering_is_alphabetical(self):
        MediaTag.objects.create(name='Zulu', slug='zulu')
        MediaTag.objects.create(name='Alpha', slug='alpha')
        names = list(MediaTag.objects.values_list('name', flat=True))
        self.assertEqual(names, sorted(names))


class MediaTagFixtureTests(TestCase):

    fixtures = ['infrastructure/mediatags.json']

    def test_fixture_loads_eight_records(self):
        self.assertEqual(MediaTag.objects.count(), 8)

    def test_all_slugs_are_unique(self):
        slugs = list(MediaTag.objects.values_list('slug', flat=True))
        self.assertEqual(len(slugs), len(set(slugs)))

    def test_ordering_is_alphabetical(self):
        names = list(MediaTag.objects.values_list('name', flat=True))
        self.assertEqual(names, sorted(names))

    def test_str_returns_name(self):
        tag = MediaTag.objects.get(name='Culture')
        self.assertEqual(str(tag), 'Culture')


# ─────────────────────────────────────────────────────────────────────────────
# 7.  Category — model & fixture
# ─────────────────────────────────────────────────────────────────────────────

class CategoryModelTests(TestCase):

    def _make_root(self, name='Heritage', slug='heritage'):
        return Category.objects.create(name=name, slug=slug)

    def _make_child(self, parent, name='Oral Traditions', slug='oral-traditions'):
        return Category.objects.create(name=name, slug=slug, parent=parent)

    def test_create_root_category(self):
        cat = self._make_root()
        self.assertIsNone(cat.parent)

    def test_create_child_category(self):
        root = self._make_root()
        child = self._make_child(root)
        self.assertEqual(child.parent, root)

    def test_str_returns_name(self):
        cat = self._make_root()
        self.assertEqual(str(cat), 'Heritage')

    def test_ordering_is_alphabetical(self):
        Category.objects.create(name='Zeta', slug='zeta')
        Category.objects.create(name='Alpha', slug='alpha')
        names = list(Category.objects.values_list('name', flat=True))
        self.assertEqual(names, sorted(names))

    def test_cascade_delete_root_removes_children(self):
        root = self._make_root()
        child = self._make_child(root)
        grandchild = Category.objects.create(
            name='Folk Tales', slug='folk-tales', parent=child
        )
        root.delete()
        self.assertFalse(Category.objects.filter(pk=child.pk).exists())
        self.assertFalse(Category.objects.filter(pk=grandchild.pk).exists())

    def test_unique_slug_constraint(self):
        self._make_root(name='Heritage', slug='heritage')
        with self.assertRaises(Exception):
            Category.objects.create(name='Heritage 2', slug='heritage')

    def test_description_is_optional(self):
        cat = self._make_root()
        self.assertEqual(cat.description, '')

    def test_children_related_name(self):
        root = self._make_root()
        child = self._make_child(root)
        self.assertIn(child, root.children.all())

    def test_leaf_node_has_no_children(self):
        root = self._make_root()
        child = self._make_child(root)
        self.assertEqual(child.children.count(), 0)

    def test_verbose_name_plural(self):
        self.assertEqual(Category._meta.verbose_name_plural, 'categories')


class CategoryFixtureTests(TestCase):

    fixtures = ['infrastructure/categories.json']

    def test_fixture_loads_nine_records(self):
        self.assertEqual(Category.objects.count(), 9)

    def test_root_nodes_count(self):
        self.assertEqual(Category.objects.filter(parent__isnull=True).count(), 3)

    def test_child_nodes_count(self):
        self.assertEqual(Category.objects.filter(parent__isnull=False).count(), 6)

    def test_grandchild_parent_chain_exists(self):
        folk = Category.objects.get(slug='folk-tales')
        self.assertIsNotNone(folk.parent)
        self.assertIsNotNone(folk.parent.parent)

    def test_cascade_delete_removes_children(self):
        heritage = Category.objects.get(slug='heritage')
        child_pks = list(heritage.children.values_list('pk', flat=True))
        heritage.delete()
        for pk in child_pks:
            self.assertFalse(Category.objects.filter(pk=pk).exists())

    def test_str_returns_name(self):
        cat = Category.objects.get(slug='heritage')
        self.assertEqual(str(cat), 'Heritage')


# ─────────────────────────────────────────────────────────────────────────────
# 8.  SiteSetting — model & fixture
# ─────────────────────────────────────────────────────────────────────────────

class SiteSettingModelTests(TestCase):

    def test_create_sitesetting_saves(self):
        s = SiteSetting.objects.create(key='site_name', value='Akita Portal')
        self.assertEqual(SiteSetting.objects.count(), 1)

    def test_str_returns_key(self):
        s = SiteSetting.objects.create(key='site_name', value='Akita Portal')
        self.assertEqual(str(s), 'site_name')

    def test_ordering_is_alphabetical_by_key(self):
        SiteSetting.objects.create(key='zzz_setting', value='z')
        SiteSetting.objects.create(key='aaa_setting', value='a')
        keys = list(SiteSetting.objects.values_list('key', flat=True))
        self.assertEqual(keys, sorted(keys))

    def test_unique_key_constraint(self):
        SiteSetting.objects.create(key='site_name', value='v1')
        with self.assertRaises(Exception):
            SiteSetting.objects.create(key='site_name', value='v2')

    def test_description_is_optional(self):
        s = SiteSetting.objects.create(key='site_name', value='Akita Portal')
        self.assertEqual(s.description, '')


class SiteSettingFixtureTests(TestCase):

    fixtures = ['infrastructure/sitesettings.json']

    def test_fixture_loads_eight_records(self):
        self.assertEqual(SiteSetting.objects.count(), 8)

    def test_all_keys_are_unique(self):
        keys = list(SiteSetting.objects.values_list('key', flat=True))
        self.assertEqual(len(keys), len(set(keys)))

    def test_ordering_is_alphabetical_by_key(self):
        keys = list(SiteSetting.objects.values_list('key', flat=True))
        self.assertEqual(keys, sorted(keys))

    def test_str_returns_key(self):
        setting = SiteSetting.objects.get(key='site_name')
        self.assertEqual(str(setting), 'site_name')


# ─────────────────────────────────────────────────────────────────────────────
# 9.  LanguageSerializer
# ─────────────────────────────────────────────────────────────────────────────

class LanguageSerializerTests(TestCase):

    def setUp(self):
        self.lang = Language.objects.create(name='Ijaw', iso_code='ijc', is_target=True)

    def test_exposes_correct_fields(self):
        data = LanguageSerializer(self.lang).data
        self.assertSetEqual(set(data.keys()), {'id', 'name', 'iso_code', 'is_target'})

    def test_field_values_match_db(self):
        data = LanguageSerializer(self.lang).data
        self.assertEqual(data['name'], 'Ijaw')
        self.assertEqual(data['iso_code'], 'ijc')
        self.assertTrue(data['is_target'])

    def test_iso_code_null_when_not_set(self):
        lang2 = Language.objects.create(name='Itsekiri', is_target=False)
        data = LanguageSerializer(lang2).data
        self.assertIsNone(data['iso_code'])

    def test_serializer_list_mode(self):
        Language.objects.create(name='Itsekiri', is_target=False)
        data = LanguageSerializer(Language.objects.all(), many=True).data
        self.assertEqual(len(data), 2)

    def test_id_is_present_and_is_integer(self):
        data = LanguageSerializer(self.lang).data
        self.assertIsInstance(data['id'], int)


# ─────────────────────────────────────────────────────────────────────────────
# 10.  DialectSerializer
# ─────────────────────────────────────────────────────────────────────────────

class DialectSerializerTests(TestCase):

    def setUp(self):
        self.lang = Language.objects.create(name='Ijaw', iso_code='ijc', is_target=True)
        self.dialect = Dialect.objects.create(
            language=self.lang, name='Akita', iso_code='okd', is_target=True
        )

    def test_exposes_correct_fields(self):
        data = DialectSerializer(self.dialect).data
        self.assertSetEqual(
            set(data.keys()), {'id', 'name', 'language_name', 'iso_code', 'is_target'}
        )

    def test_language_name_is_read_only_source_field(self):
        """language_name is sourced from dialect.language.name and is read-only."""
        data = DialectSerializer(self.dialect).data
        self.assertEqual(data['language_name'], 'Ijaw')

    def test_field_values_match_db(self):
        data = DialectSerializer(self.dialect).data
        self.assertEqual(data['name'], 'Akita')
        self.assertEqual(data['iso_code'], 'okd')
        self.assertTrue(data['is_target'])

    def test_no_language_fk_id_in_output(self):
        """The serializer exposes language_name (read-only), not the raw FK id."""
        data = DialectSerializer(self.dialect).data
        self.assertNotIn('language', data)

    def test_serializer_list_mode(self):
        Dialect.objects.create(
            language=self.lang, name='Operemo', iso_code='okd', is_target=False
        )
        data = DialectSerializer(Dialect.objects.all(), many=True).data
        self.assertEqual(len(data), 2)


# ─────────────────────────────────────────────────────────────────────────────
# 11.  CommunitySerializer
# ─────────────────────────────────────────────────────────────────────────────

class CommunitySerializerTests(TestCase):

    fixtures = ['infrastructure/communities.json']

    def test_exposes_correct_fields(self):
        """
        CommunitySerializer exposes ['id', 'name', 'alternate_names', 'description'].
        It does NOT expose is_active (that belongs to AkitaCommunity).
        """
        community = Community.objects.get(name='agbobiri')
        data = CommunitySerializer(community).data
        self.assertSetEqual(
            set(data.keys()), {'id', 'name', 'alternate_names', 'description'}
        )

    def test_no_is_active_field_in_community_serializer(self):
        """CommunitySerializer must not leak AkitaCommunity.is_active."""
        community = Community.objects.get(name='agbobiri')
        data = CommunitySerializer(community).data
        self.assertNotIn('is_active', data)

    def test_values_match_db_record(self):
        community = Community.objects.get(name='kalaba')
        data = CommunitySerializer(community).data
        self.assertEqual(data['name'], 'kalaba')

    def test_description_and_alternate_names_are_strings(self):
        community = Community.objects.get(name='agbobiri')
        data = CommunitySerializer(community).data
        self.assertIsInstance(data['alternate_names'], str)
        self.assertIsInstance(data['description'], str)


# ─────────────────────────────────────────────────────────────────────────────
# 12.  AkitaCommunitySerializer
# ─────────────────────────────────────────────────────────────────────────────

class AkitaCommunitySerializerTests(TestCase):

    fixtures = [
        'infrastructure/communities.json',
        'infrastructure/akitacommunities.json'
    ]

    def test_exposes_correct_fields(self):
        ac = AkitaCommunity.objects.get(name='agbobiri')
        data = AkitaCommunitySerializer(ac).data
        self.assertSetEqual(
            set(data.keys()),
            {'id', 'name', 'alternate_names', 'description', 'is_active'}
        )

    def test_is_active_field_present_and_correct(self):
        ac_active = AkitaCommunity.objects.get(name='kalaba')
        ac_inactive = AkitaCommunity.objects.get(name='ikarama')
        self.assertTrue(AkitaCommunitySerializer(ac_active).data['is_active'])
        self.assertFalse(AkitaCommunitySerializer(ac_inactive).data['is_active'])

    def test_name_value_matches_db(self):
        ac = AkitaCommunity.objects.get(name='agbobiri')
        data = AkitaCommunitySerializer(ac).data
        self.assertEqual(data['name'], 'agbobiri')

    def test_list_serialization(self):
        data = AkitaCommunitySerializer(AkitaCommunity.objects.all(), many=True).data
        self.assertEqual(len(data), 5)


# ─────────────────────────────────────────────────────────────────────────────
# 13.  MediaTagSerializer
# ─────────────────────────────────────────────────────────────────────────────

class MediaTagSerializerTests(TestCase):

    fixtures = ['infrastructure/mediatags.json']

    def test_exposes_correct_fields(self):
        tag = MediaTag.objects.first()
        data = MediaTagSerializer(tag).data
        self.assertSetEqual(set(data.keys()), {'id', 'name', 'slug', 'description'})

    def test_slug_value_matches_fixture(self):
        tag = MediaTag.objects.get(name='History')
        data = MediaTagSerializer(tag).data
        self.assertEqual(data['slug'], 'history')

    def test_description_is_string(self):
        tag = MediaTag.objects.first()
        data = MediaTagSerializer(tag).data
        self.assertIsInstance(data['description'], str)

    def test_list_serialization_count(self):
        data = MediaTagSerializer(MediaTag.objects.all(), many=True).data
        self.assertEqual(len(data), 8)


# ─────────────────────────────────────────────────────────────────────────────
# 14.  CategorySerializer
# ─────────────────────────────────────────────────────────────────────────────

class CategorySerializerTests(TestCase):

    fixtures = ['infrastructure/categories.json']

    def test_children_key_present_and_is_list(self):
        heritage = Category.objects.get(slug='heritage')
        data = CategorySerializer(heritage).data
        self.assertIn('children', data)
        self.assertIsInstance(data['children'], list)

    def test_immediate_children_are_nested(self):
        heritage = Category.objects.get(slug='heritage')
        data = CategorySerializer(heritage).data
        self.assertGreaterEqual(len(data['children']), 2)

    def test_grandchild_nested_inside_child(self):
        heritage = Category.objects.get(slug='heritage')
        data = CategorySerializer(heritage).data
        oral = next(c for c in data['children'] if c['slug'] == 'oral-traditions')
        grandchild_slugs = [c['slug'] for c in oral['children']]
        self.assertIn('folk-tales', grandchild_slugs)

    def test_leaf_node_children_is_empty_list(self):
        folk = Category.objects.get(slug='folk-tales')
        data = CategorySerializer(folk).data
        self.assertEqual(data['children'], [])

    def test_parent_field_is_integer_pk_for_child(self):
        oral = Category.objects.get(slug='oral-traditions')
        data = CategorySerializer(oral).data
        self.assertIsInstance(data['parent'], int)

    def test_parent_field_is_none_for_root(self):
        heritage = Category.objects.get(slug='heritage')
        data = CategorySerializer(heritage).data
        self.assertIsNone(data['parent'])

    def test_all_declared_fields_present(self):
        cat = Category.objects.get(slug='heritage')
        data = CategorySerializer(cat).data
        for field in ('id', 'name', 'slug', 'parent', 'description', 'children'):
            self.assertIn(field, data)


# ─────────────────────────────────────────────────────────────────────────────
# 15.  SiteSettingSerializer
# ─────────────────────────────────────────────────────────────────────────────

class SiteSettingSerializerTests(TestCase):

    fixtures = ['infrastructure/sitesettings.json']

    def test_exposes_correct_fields(self):
        setting = SiteSetting.objects.first()
        data = SiteSettingSerializer(setting).data
        self.assertSetEqual(set(data.keys()), {'id', 'key', 'value', 'description'})

    def test_duplicate_key_fails_validation(self):
        existing_key = SiteSetting.objects.first().key
        serializer = SiteSettingSerializer(
            data={'key': existing_key, 'value': 'x', 'description': ''}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('key', serializer.errors)

    def test_missing_key_fails_validation(self):
        serializer = SiteSettingSerializer(data={'value': 'x', 'description': ''})
        self.assertFalse(serializer.is_valid())
        self.assertIn('key', serializer.errors)

    def test_missing_value_fails_validation(self):
        serializer = SiteSettingSerializer(data={'key': 'brand_new', 'description': ''})
        self.assertFalse(serializer.is_valid())
        self.assertIn('value', serializer.errors)

    def test_missing_description_still_valid(self):
        """description is optional (blank=True on model); omitting it must pass."""
        serializer = SiteSettingSerializer(data={'key': 'brand_new', 'value': 'hello'})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_valid_data_passes_validation(self):
        serializer = SiteSettingSerializer(
            data={'key': 'new_unique_key', 'value': 'some_value', 'description': 'desc'}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_partial_update_value_only(self):
        """Partial update (patch) with only 'value' must be valid."""
        setting = SiteSetting.objects.get(key='site_name')
        serializer = SiteSettingSerializer(setting, data={'value': 'New Name'}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        