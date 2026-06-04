"""
apps/infrastructure/core/tests/test_combined.py
===============================================
Cross-model integration tests that load all four core fixtures
simultaneously and verify the models behave correctly together.

Why a separate file
-------------------
These tests exist outside the single-model scope of test_models.py and
test_api.py.  Keeping them here makes it immediately obvious from the
directory listing that cross-model / combined-fixture testing is present,
without having to open either of the other files to discover it.

Coverage
--------
  CombinedFixtureLoadTest   — DB state with all four fixtures loaded at once
  CombinedEndpointTest      — all four list endpoints reachable in one pass
  ModelIsolationTest        — deleting records in one model does not affect another

Fixtures (all four loaded for every class in this file)
--------
  infrastructure/community.json   → 5 Community records
  infrastructure/mediatag.json    → 8 MediaTag records
  infrastructure/category.json    → 9 Category records
  infrastructure/sitesetting.json → 8 SiteSetting records

Run
---
  # This file only
  python manage.py test apps.infrastructure.core.tests.test_combined \
      -v 2 --settings=config.settings.test

  # Full core test suite (all three files)
  python manage.py test apps.infrastructure.core.tests \
      -v 2 --settings=config.settings.test
"""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.infrastructure.core.models import Community, MediaTag, Category, SiteSetting


# Shared fixture list — every class in this file uses all four.
ALL_FIXTURES = [
    "infrastructure/community.json",
    "infrastructure/mediatag.json",
    "infrastructure/category.json",
    "infrastructure/sitesetting.json",
]


# ─────────────────────────────────────────────────────────────────────────────
# 1.  DB state — all four fixtures loaded together
# ─────────────────────────────────────────────────────────────────────────────

class CombinedFixtureLoadTest(APITestCase):
    """
    Verifies that all four fixture files can be loaded simultaneously without
    PK collisions, FK constraint errors, or data truncation.

    A failure here means the fixture files have conflicting primary keys or
    that one fixture references a FK that another fixture has not yet provided.
    Since Django loads fixtures in the order they are listed, dependency order
    must be respected: Community and MediaTag (no FK deps) first, then
    Category roots, then Category children, then SiteSetting.
    """

    fixtures = ALL_FIXTURES

    def test_community_record_count(self):
        """
        community.json defines 5 records.
        All 5 must be present after combined load — none silently dropped.
        """
        self.assertEqual(Community.objects.count(), 5)

    def test_mediatag_record_count(self):
        """
        mediatag.json defines 8 records.
        All 8 must be present after combined load.
        """
        self.assertEqual(MediaTag.objects.count(), 8)

    def test_category_record_count(self):
        """
        category.json defines 9 records (3 roots, 5 children, 1 grandchild).
        All 9 must be present after combined load, confirming that
        self-referencing FK relationships resolved correctly.
        """
        self.assertEqual(Category.objects.count(), 9)

    def test_sitesetting_record_count(self):
        """
        sitesetting.json defines 8 records.
        All 8 must be present after combined load.
        """
        self.assertEqual(SiteSetting.objects.count(), 8)

    def test_no_pk_collision_across_fixture_files(self):
        """
        Each model has its own DB table, so PKs are scoped per model and
        cannot collide across models.  This test confirms that the total
        record count matches the sum of all four fixture file sizes,
        meaning no fixture silently overwrote another model's records.
        """
        total = (
            Community.objects.count()
            + MediaTag.objects.count()
            + Category.objects.count()
            + SiteSetting.objects.count()
        )
        self.assertEqual(total, 30)

    def test_category_fk_relationships_intact(self):
        """
        Category uses a self-referencing FK.  After combined load, the
        parent→child→grandchild chain must be fully intact:
        Heritage → Oral Traditions → Folk Tales.
        """
        folk = Category.objects.get(slug="folk-tales")
        self.assertEqual(folk.parent.slug, "oral-traditions")
        self.assertEqual(folk.parent.parent.slug, "heritage")


# ─────────────────────────────────────────────────────────────────────────────
# 2.  API endpoints — all four reachable in a single test pass
# ─────────────────────────────────────────────────────────────────────────────

class CombinedEndpointTest(APITestCase):
    """
    Confirms that all four list endpoints return 200 when all fixtures are
    loaded together.  This catches URL configuration or import errors that
    might only surface when multiple apps are active simultaneously.
    """

    fixtures = ALL_FIXTURES

    def test_all_list_endpoints_return_200(self):
        """
        Each viewset's list URL must return 200 for an unauthenticated client.
        subTest is used so every URL is checked independently — a single
        failure does not mask failures on subsequent URLs.
        """
        urls = [
            ("community-list",   reverse("community-list")),
            ("mediatag-list",    reverse("mediatag-list")),
            ("category-list",    reverse("category-list")),
            ("sitesetting-list", reverse("sitesetting-list")),
        ]
        for name, url in urls:
            with self.subTest(endpoint=name):
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_community_list_count_with_all_fixtures_loaded(self):
        """
        Loading all fixtures must not inflate the community count.
        The community list endpoint must still return only 4 active records,
        unaffected by the presence of the other three fixture sets.
        """
        response = self.client.get(reverse("community-list"))
        self.assertEqual(len(response.data), 4)

    def test_category_list_count_with_all_fixtures_loaded(self):
        """
        Category list returns root nodes only (3).
        Loading all fixtures must not alter that count.
        """
        response = self.client.get(reverse("category-list"))
        self.assertEqual(len(response.data), 3)

    def test_mediatag_list_count_with_all_fixtures_loaded(self):
        """
        MediaTag list has no filtering — 8 records must be returned.
        """
        response = self.client.get(reverse("mediatag-list"))
        self.assertEqual(len(response.data), 8)

    def test_sitesetting_list_count_with_all_fixtures_loaded(self):
        """
        SiteSetting list has no filtering — 8 records must be returned.
        """
        response = self.client.get(reverse("sitesetting-list"))
        self.assertEqual(len(response.data), 8)


# ─────────────────────────────────────────────────────────────────────────────
# 3.  Model isolation — deleting one model must not affect another
# ─────────────────────────────────────────────────────────────────────────────

class ModelIsolationTest(APITestCase):
    """
    Confirms that the four core models are independent of one another —
    no unexpected FK relationships or shared state exist between them.

    Each test deletes all records of one model and asserts that the other
    three models are unaffected.  Django's transaction rollback restores
    the DB to the fixture state between each test method.
    """

    fixtures = ALL_FIXTURES

    def test_deleting_all_categories_does_not_affect_communities(self):
        """
        Community and Category share no FK relationship.
        Deleting every Category must leave all 5 Community records intact.
        """
        Category.objects.all().delete()
        self.assertEqual(Community.objects.count(), 5)

    def test_deleting_all_communities_does_not_affect_categories(self):
        """
        Deleting every Community must leave all 9 Category records intact.
        """
        Community.objects.all().delete()
        self.assertEqual(Category.objects.count(), 9)

    def test_deleting_all_mediatags_does_not_affect_sitesettings(self):
        """
        MediaTag and SiteSetting share no FK relationship.
        Deleting every MediaTag must leave all 8 SiteSetting records intact.
        """
        MediaTag.objects.all().delete()
        self.assertEqual(SiteSetting.objects.count(), 8)

    def test_deleting_all_sitesettings_does_not_affect_mediatags(self):
        """
        Deleting every SiteSetting must leave all 8 MediaTag records intact.
        """
        SiteSetting.objects.all().delete()
        self.assertEqual(MediaTag.objects.count(), 8)

    def test_deleting_all_communities_does_not_affect_sitesettings(self):
        """
        Community and SiteSetting share no FK relationship.
        """
        Community.objects.all().delete()
        self.assertEqual(SiteSetting.objects.count(), 8)

    def test_deleting_all_categories_does_not_affect_mediatags(self):
        """
        Category and MediaTag share no FK relationship.
        """
        Category.objects.all().delete()
        self.assertEqual(MediaTag.objects.count(), 8)
