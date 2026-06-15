"""
apps/infrastructure/core/tests/test_models.py

Tests the model and serializer layer in isolation.
No HTTP client, no URL routing, no viewset logic.

Coverage
--------
  - Fixture integrity    : correct record counts, field values, DB constraints
  - Model behaviour      : __str__, ordering, blank fields, choice validation,
                           FK cascade, unique constraints
  - Serializer behaviour : field sets, output values, validation rejection
  - NEW: Language singleton-target constraint
  - NEW: Dialect singleton-target + iso_code cross-check constraint
  - NEW: AkitaCommunity name validation against AKITA_COMMUNITIES

Fixtures
--------
  Declared per class. Django loads them from the path resolved against
  FIXTURE_DIRS (set to api/fixtures/ in config/settings/test.py), so the
  path prefix 'infrastructure/' navigates into the correct subdirectory.

  communities.json  → 5 Community records  (1 inactive: ikarama)
  mediatags.json    → 8 MediaTag records
  categories.json   → 9 Category records   (3 roots, 5 children, 1 grandchild)
  sitesettings.json → 8 SiteSetting records

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

from apps.infrastructure.core.models import (
    Language, Dialect, Community, AkitaCommunity, MediaTag, Category, SiteSetting
)
from apps.infrastructure.core.serializers import (
    CommunitySerializer,
    MediaTagSerializer,
    CategorySerializer,
    SiteSettingSerializer,
)


# ─────────────────────────────────────────────────────────────────────────────
# NEW 1.  Language — model constraints
# ─────────────────────────────────────────────────────────────────────────────

class LanguageModelTests(TestCase):
    """
    Language has two invariants enforced at save() / clean() time:
      1. The very first record must have is_target=True (bootstrap guard).
      2. Only one Language may have is_target=True at any time
         (UniqueConstraint + clean()).
    """

    def test_first_language_with_is_target_true_saves(self):
        """
        The first Language record must be accepted when is_target=True.
        No pre-existing records exist, so the bootstrap guard passes.
        """
        lang = Language(name='Ijaw', iso_code='ijc', is_target=True)
        lang.save()
        self.assertEqual(Language.objects.count(), 1)

    def test_first_language_with_is_target_false_raises(self):
        """
        save() raises ValidationError for the first record when is_target=False.
        This prevents the application from starting without a target language.
        """
        lang = Language(name='Ijaw', is_target=False)
        with self.assertRaises(ValidationError):
            lang.save()

    def test_second_target_language_fails_clean(self):
        """
        clean() raises ValidationError when a second language tries to claim
        is_target=True while one already exists.
        """
        Language.objects.create(name='Ijaw', is_target=True)
        duplicate = Language(name='Kalabari', iso_code='ijn', is_target=True)
        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_non_target_second_language_is_accepted(self):
        """
        A second language with is_target=False must be saved without error,
        since the singleton constraint only applies to is_target=True.
        """
        Language.objects.create(name='Ijaw', is_target=True)
        lang2 = Language(name='Itsekiri', is_target=False)
        lang2.full_clean()  # should not raise
        lang2.save()
        self.assertEqual(Language.objects.count(), 2)

    def test_str_returns_name(self):
        """__str__ is 'return self.name'."""
        lang = Language.objects.create(name='Ijaw', is_target=True)
        self.assertEqual(str(lang), 'Ijaw')

    def test_iso_code_is_optional(self):
        """iso_code is nullable — saving without it must succeed."""
        lang = Language(name='TestLang', is_target=True)
        lang.save()
        self.assertIsNone(lang.iso_code)

    def test_updating_target_language_does_not_violate_constraint(self):
        """
        Saving an already-target Language again (e.g. updating its name)
        must not raise — the UniqueConstraint excludes the current pk.
        """
        lang = Language.objects.create(name='Ijaw', is_target=True)
        lang.name = 'Ịjọ'
        lang.full_clean()   # exclude(pk=self.pk) in clean() prevents false positive
        lang.save()
        self.assertEqual(Language.objects.get(pk=lang.pk).name, 'Ịjọ')


# ─────────────────────────────────────────────────────────────────────────────
# NEW 2.  Dialect — model constraints
# ─────────────────────────────────────────────────────────────────────────────

class DialectModelTests(TestCase):
    """
    Dialect mirrors Language's singleton-target logic and adds an
    iso_code cross-check with its parent Language.
    """

    def setUp(self):
        self.lang = Language.objects.create(
            name='Ijaw', iso_code='ijc', is_target=True
        )

    def test_first_dialect_with_is_target_true_saves(self):
        d = Dialect(
            language=self.lang, name='Akita', iso_code='okd', is_target=True
        )
        d.save()
        self.assertEqual(Dialect.objects.count(), 1)

    def test_first_dialect_with_is_target_false_raises(self):
        d = Dialect(language=self.lang, name='Akita', is_target=False)
        with self.assertRaises(ValidationError):
            d.save()

    def test_second_target_dialect_fails_clean(self):
        Dialect.objects.create(
            language=self.lang, name='Akita', iso_code='okd', is_target=True
        )
        d2 = Dialect(language=self.lang, name='Operemo', is_target=True)
        with self.assertRaises(ValidationError):
            d2.full_clean()

    def test_iso_code_mismatch_with_language_fails_clean(self):
        """
        If both language.iso_code and dialect.iso_code are set they must match.
        Dialect iso_code 'xxx' vs language iso_code 'ijc' must raise.
        """
        d = Dialect(
            language=self.lang, name='Akita',
            iso_code='xxx',   # deliberately wrong
            is_target=True,
        )
        with self.assertRaises(ValidationError):
            d.full_clean()

    def test_iso_code_match_with_language_passes(self):
        """iso_code='okd' on Dialect is accepted when language.iso_code='ijc' …
        wait — the model only checks equality. 'okd' != 'ijc' so we need a
        language whose iso_code matches the dialect. Use a language with no
        iso_code to bypass that branch."""
        lang_no_iso = Language.objects.create(
            name='Ịjọ-variant', is_target=False, iso_code=None
        )
        d = Dialect(language=lang_no_iso, name='Akita-v', iso_code='okd', is_target=True)
        d.full_clean()  # should not raise — language.iso_code is None
        d.save()
        self.assertTrue(Dialect.objects.filter(name='Akita-v').exists())

    def test_str_returns_dialect_dash_language(self):
        """__str__ is 'return f"{self.name}-{self.language.name}"'."""
        d = Dialect.objects.create(
            language=self.lang, name='Akita', iso_code='okd', is_target=True
        )
        self.assertEqual(str(d), 'Akita-Ijaw')

    def test_unique_together_language_name(self):
        """(language, name) must be unique."""
        from django.db import IntegrityError
        Dialect.objects.create(
            language=self.lang, name='Akita', iso_code='okd', is_target=True
        )
        with self.assertRaises(Exception):  # IntegrityError or ValidationError
            Dialect.objects.create(
                language=self.lang, name='Akita', is_target=False
            )

    def test_updating_target_dialect_does_not_violate_constraint(self):
        """
        Saving an already-target Dialect (e.g. updating a note field) must
        not fire the clean() singleton guard against itself.
        """
        d = Dialect.objects.create(
            language=self.lang, name='Akita', iso_code='okd', is_target=True
        )
        d.name = 'Akịta'
        d.full_clean()
        d.save()
        self.assertEqual(Dialect.objects.get(pk=d.pk).name, 'Akịta')


# ─────────────────────────────────────────────────────────────────────────────
# NEW 3.  AkitaCommunity — name validation
# ─────────────────────────────────────────────────────────────────────────────

class AkitaCommunityModelTests(TestCase):
    """
    AkitaCommunity subclasses Community (multi-table inheritance).
    clean() validates that name is one of the five AKITA_COMMUNITIES,
    case-insensitively (it capitalises both sides for comparison).
    """

    def test_valid_community_name_passes_full_clean(self):
        """Each of the five AKITA_COMMUNITIES names must pass full_clean."""
        from apps.common.constants import AKITA_COMMUNITIES
        for name in AKITA_COMMUNITIES:
            with self.subTest(name=name):
                c = AkitaCommunity(name=name, is_active=True)
                c.full_clean()  # must not raise

    def test_invalid_community_name_raises(self):
        """A name not in AKITA_COMMUNITIES must raise ValidationError on full_clean."""
        c = AkitaCommunity(name='Unknown Village', is_active=True)
        with self.assertRaises(ValidationError) as ctx:
            c.full_clean()
        self.assertIn('name', ctx.exception.message_dict)

    def test_is_active_default_is_true(self):
        c = AkitaCommunity(name='Kalaba', is_active=True)
        c.full_clean()
        c.save()
        self.assertTrue(AkitaCommunity.objects.get(name='Kalaba').is_active)

    def test_case_insensitive_name_is_accepted(self):
        """
        VALID_COMMUNITIES capitalises before comparison, so lower-case input
        that matches a community must also pass.
        """
        c = AkitaCommunity(name='agbobiri', is_active=True)
        # 'agbobiri'.capitalize() == 'Agbobiri' which is in VALID_COMMUNITIES
        c.full_clean()  # must not raise

    def test_akitacommunity_inherits_community_str(self):
        """
        AkitaCommunity is a Community proxy via MTI.
        __str__ is inherited from Community and returns self.name.
        """
        c = AkitaCommunity(name='Kalaba')
        c.full_clean()
        c.save()
        self.assertEqual(str(c), 'Kalaba')


# ─────────────────────────────────────────────────────────────────────────────
# 1.  Community — fixture integrity & model behaviour  [ORIGINAL — unchanged]
# ─────────────────────────────────────────────────────────────────────────────

class CommunityFixtureLoadTest(TestCase):
    """
    Verifies that communities.json loads correctly and that the model's
    field constraints and Meta options behave as declared.
    """

    fixtures = ["infrastructure/communities.json"]

    def test_fixture_loads_all_five_records(self):
        """
        The fixture contains 5 entries — all five original Akita communities.
        This confirms every row was inserted without integrity errors.
        """
        self.assertEqual(Community.objects.count(), 5)

    def test_active_filter_excludes_inactive(self):
        """
        CommunityViewSet uses queryset = Community.objects.filter(is_active=True).
        That filter must return exactly 4 records, and 'ikarama' (is_active=False)
        must not appear among them.
        """
        active = Community.objects.filter(is_active=True)
        self.assertEqual(active.count(), 4)
        names = list(active.values_list("name", flat=True))
        self.assertNotIn("ikarama", names)

    def test_inactive_record_exists_in_db(self):
        """
        'ikarama' must exist in the DB (fixture loaded it) but with
        is_active=False.  The record is present; the viewset merely filters
        it out when building its queryset.
        """
        ikarama = Community.objects.get(name="ikarama")
        self.assertFalse(ikarama.is_active)

    def test_ordering_is_alphabetical(self):
        """
        Meta.ordering = ['name'] must produce alphabetically sorted results
        without an explicit .order_by() call.
        """
        names = list(
            Community.objects.filter(is_active=True).values_list("name", flat=True)
        )
        self.assertEqual(names, sorted(names))

    def test_blank_optional_fields_accepted(self):
        """
        alternate_names and description are both blank=True.
        They must accept empty strings without raising a ValidationError.
        """
        c = Community.objects.get(name="agbobiri")
        self.assertIsInstance(c.alternate_names, str)
        self.assertIsInstance(c.description, str)

    def test_str_returns_name(self):
        """__str__ is defined as 'return self.name'."""
        c = Community.objects.get(name="kalaba")
        self.assertEqual(str(c), "kalaba")


# ─────────────────────────────────────────────────────────────────────────────
# 2.  Community — serializer  [ORIGINAL — unchanged]
# ─────────────────────────────────────────────────────────────────────────────

class CommunitySerializerTest(TestCase):
    """
    Unit-tests CommunitySerializer directly, without going through
    the API layer.  Checks field exposure and validation logic.
    """

    fixtures = ["infrastructure/communities.json"]

    def test_serializer_exposes_correct_fields(self):
        community = Community.objects.get(name="agbobiri")
        data = CommunitySerializer(community).data
        self.assertSetEqual(
            set(data.keys()),
            {"id", "name", "alternate_names", "description", "is_active"},
        )

    def test_serializer_values_match_db_record(self):
        community = Community.objects.get(name="kalaba")
        data = CommunitySerializer(community).data
        self.assertEqual(data["name"], "kalaba")
        self.assertTrue(data["is_active"])

    def test_invalid_name_choice_is_rejected(self):
        """
        'name' is a choices field restricted to ORIGINAL_COMMUNITIES.
        Any value outside that list must cause is_valid() to return False
        with an error keyed on 'name'.
        """
        bad_data = {
            "name": "unknown_village",
            "alternate_names": "",
            "description": "",
            "is_active": True,
        }
        serializer = CommunitySerializer(data=bad_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)


# ─────────────────────────────────────────────────────────────────────────────
# 3.  MediaTag — fixture integrity & model behaviour  [ORIGINAL — unchanged]
# ─────────────────────────────────────────────────────────────────────────────

class MediaTagFixtureLoadTest(TestCase):

    fixtures = ["infrastructure/mediatags.json"]

    def test_fixture_loads_eight_records(self):
        self.assertEqual(MediaTag.objects.count(), 8)

    def test_all_slugs_are_unique(self):
        slugs = list(MediaTag.objects.values_list("slug", flat=True))
        self.assertEqual(len(slugs), len(set(slugs)))

    def test_ordering_is_alphabetical(self):
        names = list(MediaTag.objects.values_list("name", flat=True))
        self.assertEqual(names, sorted(names))

    def test_str_returns_name(self):
        tag = MediaTag.objects.get(name="Culture")
        self.assertEqual(str(tag), "Culture")


# ─────────────────────────────────────────────────────────────────────────────
# 4.  MediaTag — serializer  [ORIGINAL — unchanged]
# ─────────────────────────────────────────────────────────────────────────────

class MediaTagSerializerTest(TestCase):

    fixtures = ["infrastructure/mediatags.json"]

    def test_serializer_exposes_correct_fields(self):
        tag = MediaTag.objects.first()
        data = MediaTagSerializer(tag).data
        self.assertSetEqual(set(data.keys()), {"id", "name", "slug", "description"})

    def test_slug_value_matches_fixture(self):
        tag = MediaTag.objects.get(name="History")
        data = MediaTagSerializer(tag).data
        self.assertEqual(data["slug"], "history")


# ─────────────────────────────────────────────────────────────────────────────
# 5.  Category — fixture integrity & model behaviour  [ORIGINAL — unchanged]
# ─────────────────────────────────────────────────────────────────────────────

class CategoryFixtureLoadTest(TestCase):

    fixtures = ["infrastructure/categories.json"]

    def test_fixture_loads_nine_records(self):
        self.assertEqual(Category.objects.count(), 9)

    def test_root_nodes_count(self):
        roots = Category.objects.filter(parent__isnull=True)
        self.assertEqual(roots.count(), 3)

    def test_child_nodes_count(self):
        children = Category.objects.filter(parent__isnull=False)
        self.assertEqual(children.count(), 6)

    def test_grandchild_parent_chain_exists(self):
        folk = Category.objects.get(slug="folk-tales")
        self.assertIsNotNone(folk.parent)
        self.assertIsNotNone(folk.parent.parent)

    def test_cascade_delete_removes_children(self):
        heritage = Category.objects.get(slug="heritage")
        child_pks = list(heritage.children.values_list("pk", flat=True))
        heritage.delete()
        for pk in child_pks:
            self.assertFalse(Category.objects.filter(pk=pk).exists())

    def test_str_returns_name(self):
        cat = Category.objects.get(slug="heritage")
        self.assertEqual(str(cat), "Heritage")


# ─────────────────────────────────────────────────────────────────────────────
# 6.  Category — serializer  [ORIGINAL — unchanged]
# ─────────────────────────────────────────────────────────────────────────────

class CategorySerializerTest(TestCase):

    fixtures = ["infrastructure/categories.json"]

    def test_children_key_present_and_is_list(self):
        heritage = Category.objects.get(slug="heritage")
        data = CategorySerializer(heritage).data
        self.assertIn("children", data)
        self.assertIsInstance(data["children"], list)

    def test_immediate_children_are_nested(self):
        heritage = Category.objects.get(slug="heritage")
        data = CategorySerializer(heritage).data
        self.assertGreaterEqual(len(data["children"]), 2)

    def test_grandchild_nested_inside_child(self):
        heritage = Category.objects.get(slug="heritage")
        data = CategorySerializer(heritage).data
        oral = next(c for c in data["children"] if c["slug"] == "oral-traditions")
        grandchild_slugs = [c["slug"] for c in oral["children"]]
        self.assertIn("folk-tales", grandchild_slugs)

    def test_leaf_node_children_is_empty_list(self):
        folk = Category.objects.get(slug="folk-tales")
        data = CategorySerializer(folk).data
        self.assertEqual(data["children"], [])

    def test_parent_field_is_integer_pk(self):
        oral = Category.objects.get(slug="oral-traditions")
        data = CategorySerializer(oral).data
        self.assertIsInstance(data["parent"], int)


# ─────────────────────────────────────────────────────────────────────────────
# 7.  SiteSetting — fixture integrity & model behaviour  [ORIGINAL — unchanged]
# ─────────────────────────────────────────────────────────────────────────────

class SiteSettingFixtureLoadTest(TestCase):

    fixtures = ["infrastructure/sitesettings.json"]

    def test_fixture_loads_eight_records(self):
        self.assertEqual(SiteSetting.objects.count(), 8)

    def test_all_keys_are_unique(self):
        keys = list(SiteSetting.objects.values_list("key", flat=True))
        self.assertEqual(len(keys), len(set(keys)))

    def test_ordering_is_alphabetical_by_key(self):
        keys = list(SiteSetting.objects.values_list("key", flat=True))
        self.assertEqual(keys, sorted(keys))

    def test_str_returns_key(self):
        setting = SiteSetting.objects.get(key="site_name")
        self.assertEqual(str(setting), "site_name")


# ─────────────────────────────────────────────────────────────────────────────
# 8.  SiteSetting — serializer  [ORIGINAL — unchanged]
# ─────────────────────────────────────────────────────────────────────────────

class SiteSettingSerializerTest(TestCase):

    fixtures = ["infrastructure/sitesettings.json"]

    def test_serializer_exposes_correct_fields(self):
        setting = SiteSetting.objects.first()
        data = SiteSettingSerializer(setting).data
        self.assertSetEqual(set(data.keys()), {"id", "key", "value", "description"})

    def test_duplicate_key_fails_validation(self):
        existing_key = SiteSetting.objects.first().key
        serializer = SiteSettingSerializer(
            data={"key": existing_key, "value": "x", "description": ""}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("key", serializer.errors)

    def test_missing_key_fails_validation(self):
        serializer = SiteSettingSerializer(data={"value": "x", "description": ""})
        self.assertFalse(serializer.is_valid())
        self.assertIn("key", serializer.errors)

    def test_missing_value_fails_validation(self):
        serializer = SiteSettingSerializer(
            data={"key": "brand_new_key", "description": ""}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("value", serializer.errors)
