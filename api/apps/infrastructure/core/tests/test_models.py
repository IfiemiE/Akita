"""
Tests the model and serializer layer in isolation.
No HTTP client, no URL routing, no viewset logic.

Coverage
--------
  - Fixture integrity    : correct record counts, field values, DB constraints
  - Model behaviour      : __str__, ordering, blank fields, choice validation,
                           FK cascade, unique constraints
  - Serializer behaviour : field sets, output values, validation rejection

Fixtures
--------
  Declared per class. Django loads them from the path resolved against
  FIXTURE_DIRS (set to api/fixtures/ in config/settings/test.py), so the
  path prefix 'infrastructure/' navigates into the correct subdirectory.

  community.json   → 5 Community records  (1 inactive)
  mediatag.json    → 8 MediaTag records
  category.json    → 9 Category records   (3 roots, 5 children, 1 grandchild)
  sitesetting.json → 8 SiteSetting records

Run
---
$ python manage.py test TEST_DOTTED_PATH -v 2 --settings=config.settings.test
      
where 
TEST_DOTTED_PATH = apps.infrastructure.core.tests.test_models.CLASS.METHOD for a specific test METHOD
TEST_DOTTED_PATH = apps.infrastructure.core.tests.test_models.CLASS for a specific test CLASS
TEST_DOTTED_PATH = apps.infrastructure.core.tests.test_models for the specific test_models module
TEST_DOTTED_PATH = apps.infrastructure.core.tests for all modules in the test folder
"""

from django.test import TestCase

from apps.infrastructure.core.models import (
    Community, MediaTag, Category, SiteSetting
)
from apps.infrastructure.core.serializers import (
    CommunitySerializer,
    MediaTagSerializer,
    CategorySerializer,
    SiteSettingSerializer,
)


# ─────────────────────────────────────────────────────────────────────────────
# 1.  Community — fixture integrity & model behaviour
# ─────────────────────────────────────────────────────────────────────────────

class CommunityFixtureLoadTest(TestCase):
    """
    Verifies that community.json loads correctly and that the model's
    field constraints and Meta options behave as declared.
    """

    fixtures = ["infrastructure/communities.json"]

    # -- record counts --------------------------------------------------------

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

    # -- model meta -----------------------------------------------------------

    def test_ordering_is_alphabetical(self):
        """
        Meta.ordering = ['name'] must produce alphabetically sorted results
        without an explicit .order_by() call.
        """
        names = list(
            Community.objects.filter(is_active=True).values_list("name", flat=True)
        )
        self.assertEqual(names, sorted(names))

    # -- field constraints ----------------------------------------------------

    def test_blank_optional_fields_accepted(self):
        """
        alternate_names and description are both blank=True.
        They must accept empty strings without raising a ValidationError.
        """
        c = Community.objects.get(name="agbobiri")
        self.assertIsInstance(c.alternate_names, str)
        self.assertIsInstance(c.description, str)

    def test_str_returns_name(self):
        """
        __str__ is defined as 'return self.name'.
        Casting the instance to str must return the name value.
        """
        c = Community.objects.get(name="kalaba")
        self.assertEqual(str(c), "kalaba")


# ─────────────────────────────────────────────────────────────────────────────
# 2.  Community — serializer
# ─────────────────────────────────────────────────────────────────────────────

class CommunitySerializerTest(TestCase):
    """
    Unit-tests CommunitySerializer directly, without going through
    the API layer.  Checks field exposure and validation logic.
    """

    fixtures = ["infrastructure/communities.json"]

    def test_serializer_exposes_correct_fields(self):
        """
        Meta.fields declares exactly five fields.  The serialized output
        must contain those five keys and no others.
        """
        community = Community.objects.get(name="agbobiri")
        data = CommunitySerializer(community).data
        self.assertSetEqual(
            set(data.keys()),
            {"id", "name", "alternate_names", "description", "is_active"},
        )

    def test_serializer_values_match_db_record(self):
        """
        The serializer must faithfully mirror the values stored in the DB.
        'kalaba' is active — is_active must serialize as True.
        """
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
# 3.  MediaTag — fixture integrity & model behaviour
# ─────────────────────────────────────────────────────────────────────────────

class MediaTagFixtureLoadTest(TestCase):
    """
    Verifies that mediatag.json loads correctly and that the model's
    unique constraints and ordering are in effect.
    """

    fixtures = ["infrastructure/mediatags.json"]

    def test_fixture_loads_eight_records(self):
        """
        The fixture contains 8 tags.  All must be inserted successfully,
        confirming no unique-constraint collisions exist within the file.
        """
        self.assertEqual(MediaTag.objects.count(), 8)

    def test_all_slugs_are_unique(self):
        """
        slug = models.SlugField(unique=True).
        Collecting all slugs into a set must produce the same count as the
        full queryset — no duplicates.
        """
        slugs = list(MediaTag.objects.values_list("slug", flat=True))
        self.assertEqual(len(slugs), len(set(slugs)))

    def test_ordering_is_alphabetical(self):
        """
        Meta.ordering = ['name'] must return tags in A→Z order without
        an explicit .order_by() call.
        """
        names = list(MediaTag.objects.values_list("name", flat=True))
        self.assertEqual(names, sorted(names))

    def test_str_returns_name(self):
        """__str__ is 'return self.name'."""
        tag = MediaTag.objects.get(name="Culture")
        self.assertEqual(str(tag), "Culture")


# ─────────────────────────────────────────────────────────────────────────────
# 4.  MediaTag — serializer
# ─────────────────────────────────────────────────────────────────────────────

class MediaTagSerializerTest(TestCase):

    fixtures = ["infrastructure/mediatags.json"]

    def test_serializer_exposes_correct_fields(self):
        """
        Meta.fields = ['id', 'name', 'slug', 'description'].
        No extra or missing keys must appear in the serialized output.
        """
        tag = MediaTag.objects.first()
        data = MediaTagSerializer(tag).data
        self.assertSetEqual(set(data.keys()), {"id", "name", "slug", "description"})

    def test_slug_value_matches_fixture(self):
        """
        The 'History' tag has slug='history' in the fixture.
        The serializer must reproduce that value exactly.
        """
        tag = MediaTag.objects.get(name="History")
        data = MediaTagSerializer(tag).data
        self.assertEqual(data["slug"], "history")


# ─────────────────────────────────────────────────────────────────────────────
# 5.  Category — fixture integrity & model behaviour
# ─────────────────────────────────────────────────────────────────────────────

class CategoryFixtureLoadTest(TestCase):
    """
    Verifies that category.json loads all 9 records with their FK
    relationships intact, and that the model's cascade and ordering
    behaviour works correctly.
    """

    fixtures = ["infrastructure/categories.json"]

    def test_fixture_loads_nine_records(self):
        """All 9 category rows must be present after fixture load."""
        self.assertEqual(Category.objects.count(), 9)

    def test_root_nodes_count(self):
        """
        Three categories have parent=null in the fixture:
        Heritage, Media, and Community Affairs.
        """
        roots = Category.objects.filter(parent__isnull=True)
        self.assertEqual(roots.count(), 3)

    def test_child_nodes_count(self):
        """
        Six categories have a non-null parent.
        (9 total minus 3 roots = 6 children/grandchildren.)
        """
        children = Category.objects.filter(parent__isnull=False)
        self.assertEqual(children.count(), 6)

    def test_grandchild_parent_chain_exists(self):
        """
        'folk-tales' is a grandchild: its parent is 'oral-traditions'
        and its grandparent is 'heritage'.  Both FK links must resolve
        to non-null objects.
        """
        folk = Category.objects.get(slug="folk-tales")
        self.assertIsNotNone(folk.parent)
        self.assertIsNotNone(folk.parent.parent)

    def test_cascade_delete_removes_children(self):
        """
        on_delete=CASCADE is set on the parent FK.
        Deleting 'heritage' must also delete its immediate children.
        This confirms the DB constraint is wired correctly.
        """
        heritage = Category.objects.get(slug="heritage")
        child_pks = list(heritage.children.values_list("pk", flat=True))
        heritage.delete()
        for pk in child_pks:
            self.assertFalse(Category.objects.filter(pk=pk).exists())

    def test_str_returns_name(self):
        """__str__ is 'return self.name'."""
        cat = Category.objects.get(slug="heritage")
        self.assertEqual(str(cat), "Heritage")


# ─────────────────────────────────────────────────────────────────────────────
# 6.  Category — serializer
# ─────────────────────────────────────────────────────────────────────────────

class CategorySerializerTest(TestCase):
    """
    Unit-tests CategorySerializer.  The key behaviour under test is the
    recursive nesting produced by get_children() — a SerializerMethodField
    that calls CategorySerializer recursively on each child.
    """

    fixtures = ["infrastructure/categories.json"]

    def test_children_key_present_and_is_list(self):
        """
        Every serialized Category must include a 'children' key whose
        value is a list — even if it is empty.
        """
        heritage = Category.objects.get(slug="heritage")
        data = CategorySerializer(heritage).data
        self.assertIn("children", data)
        self.assertIsInstance(data["children"], list)

    def test_immediate_children_are_nested(self):
        """
        'heritage' has two immediate children in the fixture (Oral Traditions
        and Artefacts).  The serialized 'children' list must contain at least
        two items.
        """
        heritage = Category.objects.get(slug="heritage")
        data = CategorySerializer(heritage).data
        self.assertGreaterEqual(len(data["children"]), 2)

    def test_grandchild_nested_inside_child(self):
        """
        Recursive nesting must go at least two levels deep.
        'folk-tales' must appear inside oral-traditions.children within
        the serialized representation of 'heritage'.
        """
        heritage = Category.objects.get(slug="heritage")
        data = CategorySerializer(heritage).data
        oral = next(c for c in data["children"] if c["slug"] == "oral-traditions")
        grandchild_slugs = [c["slug"] for c in oral["children"]]
        self.assertIn("folk-tales", grandchild_slugs)

    def test_leaf_node_children_is_empty_list(self):
        """
        get_children() returns [] when obj.children.exists() is False.
        'folk-tales' has no children — its 'children' key must be [].
        This confirms the recursion terminates cleanly.
        """
        folk = Category.objects.get(slug="folk-tales")
        data = CategorySerializer(folk).data
        self.assertEqual(data["children"], [])

    def test_parent_field_is_integer_pk(self):
        """
        The 'parent' field is a raw PrimaryKeyRelatedField — it must
        serialize as an integer, not as a nested object.
        """
        oral = Category.objects.get(slug="oral-traditions")
        data = CategorySerializer(oral).data
        self.assertIsInstance(data["parent"], int)


# ─────────────────────────────────────────────────────────────────────────────
# 7.  SiteSetting — fixture integrity & model behaviour
# ─────────────────────────────────────────────────────────────────────────────

class SiteSettingFixtureLoadTest(TestCase):
    """
    Verifies that sitesetting.json loads all 8 records correctly and that
    the model's unique and ordering constraints are satisfied.
    """

    fixtures = ["infrastructure/sitesettings.json"]

    def test_fixture_loads_eight_records(self):
        """All 8 setting rows must be present after fixture load."""
        self.assertEqual(SiteSetting.objects.count(), 8)

    def test_all_keys_are_unique(self):
        """
        key = models.CharField(unique=True).
        Collecting keys into a set must give the same count as the queryset.
        """
        keys = list(SiteSetting.objects.values_list("key", flat=True))
        self.assertEqual(len(keys), len(set(keys)))

    def test_ordering_is_alphabetical_by_key(self):
        """
        Meta.ordering = ['key'] must return settings in A→Z key order
        without an explicit .order_by() call.
        """
        keys = list(SiteSetting.objects.values_list("key", flat=True))
        self.assertEqual(keys, sorted(keys))

    def test_str_returns_key(self):
        """__str__ is 'return self.key'."""
        setting = SiteSetting.objects.get(key="site_name")
        self.assertEqual(str(setting), "site_name")


# ─────────────────────────────────────────────────────────────────────────────
# 8.  SiteSetting — serializer
# ─────────────────────────────────────────────────────────────────────────────

class SiteSettingSerializerTest(TestCase):

    fixtures = ["infrastructure/sitesettings.json"]

    def test_serializer_exposes_correct_fields(self):
        """
        Meta.fields = ['id', 'key', 'value', 'description'].
        Serialized output must contain exactly those four keys.
        """
        setting = SiteSetting.objects.first()
        data = SiteSettingSerializer(setting).data
        self.assertSetEqual(set(data.keys()), {"id", "key", "value", "description"})

    def test_duplicate_key_fails_validation(self):
        """
        key has a unique constraint.  Submitting a key that already exists
        must cause is_valid() to return False with an error on 'key'.
        This is the serializer-layer enforcement of the DB constraint.
        """
        existing_key = SiteSetting.objects.first().key
        serializer = SiteSettingSerializer(
            data={"key": existing_key, "value": "x", "description": ""}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("key", serializer.errors)

    def test_missing_key_fails_validation(self):
        """
        'key' is a required field (no default, not blank).
        Omitting it must cause a validation error on 'key'.
        """
        serializer = SiteSettingSerializer(data={"value": "x", "description": ""})
        self.assertFalse(serializer.is_valid())
        self.assertIn("key", serializer.errors)

    def test_missing_value_fails_validation(self):
        """
        'value' is a required field.
        Omitting it must cause a validation error on 'value'.
        """
        serializer = SiteSettingSerializer(
            data={"key": "brand_new_key", "description": ""}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("value", serializer.errors)
