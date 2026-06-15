"""
apps/infrastructure/core/tests/test_api.py

Tests the HTTP/API layer for each viewset individually.
Every test goes through APIClient — URL routing, authentication,
permission classes, and response shape are all exercised here.

Coverage
--------
  CommunityViewSet       (ReadOnlyModelViewSet)
  AkitaCommunityViewSet  (ReadOnlyModelViewSet) — NEW
  MediaTagViewSet        (ReadOnlyModelViewSet)
  CategoryViewSet        (ReadOnlyModelViewSet)
  SiteSettingViewSet     (ModelViewSet — split permissions)
  ExplicitTeardownDemonstrationTest  (manual create→use→destroy pattern)

Not covered here
----------------
  Cross-model / combined fixture tests → see test_combined.py
  Language / Dialect model tests       → see test_models.py

Fixtures
--------
  Declared per class. Django resolves 'infrastructure/...' relative to
  each directory in FIXTURE_DIRS (api/fixtures/ in config/settings/test.py).

  communities.json  → 5 Community records  (1 inactive: ikarama)
  mediatags.json    → 8 MediaTag records
  categories.json   → 9 Category records   (3 roots, 5 children, 1 grandchild)
  sitesettings.json → 8 SiteSetting records

URL basenames expected in the router registration (urls.py):
  community       → CommunityViewSet
  akitacommunity  → AkitaCommunityViewSet   [NEW]
  mediatag        → MediaTagViewSet
  category        → CategoryViewSet
  sitesetting     → SiteSettingViewSet

Run
---
  $ python manage.py test TEST_DOTTED_PATH -v 2 --settings=config.settings.test
"""

from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from apps.infrastructure.core.models import Community, AkitaCommunity, MediaTag, Category, SiteSetting

User = get_user_model()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers  [ORIGINAL — unchanged]
# ─────────────────────────────────────────────────────────────────────────────

def make_admin(username="admin", password="adminpass123"):
    return User.objects.create_superuser(
        username=username, password=password, email=f"{username}@test.com"
    )


def make_regular_user(username="user", password="userpass123"):
    return User.objects.create_user(
        username=username, password=password, email=f"{username}@test.com"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1.  CommunityViewSet  [ORIGINAL — unchanged]
# ─────────────────────────────────────────────────────────────────────────────

class CommunityViewSetTest(APITestCase):
    """
    CommunityViewSet is a ReadOnlyModelViewSet with:
      queryset = Community.objects.all()

    Expected behaviour
    ------------------
    - GET list/retrieve → 200 for all clients (unauthenticated or not)
    - POST / PUT / DELETE → 405 (route not registered by ReadOnlyModelViewSet)
    """

    fixtures = ["infrastructure/communities.json"]

    def setUp(self):
        self.client = APIClient()
        self.list_url = reverse("community-list")

    def test_list_returns_200(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_excludes_inactive_community(self):
        """
        CommunityViewSet has no is_active filter on Community itself —
        but the fixture has 5 records; all 5 are returned.
        NOTE: is_active filtering is on AkitaCommunityViewSet, not here.
        """
        response = self.client.get(self.list_url)
        self.assertEqual(len(response.data), 5)

    def test_inactive_community_present_in_list(self):
        """
        CommunityViewSet returns all Community records, including ikarama.
        Active filtering belongs to AkitaCommunityViewSet.
        """
        response = self.client.get(self.list_url)
        names = [item["name"] for item in response.data]
        self.assertIn("ikarama", names)

    def test_list_results_are_alphabetically_ordered(self):
        response = self.client.get(self.list_url)
        names = [item["name"] for item in response.data]
        self.assertEqual(names, sorted(names))

    def test_list_items_contain_all_declared_fields(self):
        response = self.client.get(self.list_url)
        first = response.data[0]
        for field in ("id", "name", "alternate_names", "description", "is_active"):
            self.assertIn(field, first)

    def test_retrieve_community_returns_200(self):
        pk = Community.objects.get(name="agbobiri").pk
        url = reverse("community-detail", kwargs={"pk": pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "agbobiri")

    def test_post_returns_405(self):
        payload = {"name": "agbobiri", "alternate_names": "", "description": ""}
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_put_returns_405(self):
        pk = Community.objects.get(name="agbobiri").pk
        url = reverse("community-detail", kwargs={"pk": pk})
        response = self.client.put(url, {"name": "agbobiri"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_returns_405(self):
        pk = Community.objects.get(name="agbobiri").pk
        url = reverse("community-detail", kwargs={"pk": pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


# ─────────────────────────────────────────────────────────────────────────────
# NEW 2.  AkitaCommunityViewSet
# ─────────────────────────────────────────────────────────────────────────────

class AkitaCommunityViewSetTest(APITestCase):
    """
    AkitaCommunityViewSet is a ReadOnlyModelViewSet with:
      queryset = AkitaCommunity.objects.filter(is_active=True)

    Expected behaviour
    ------------------
    - GET list → 200; only active records returned
    - Inactive record ('ikarama') absent from list, 404 on retrieve
    - POST / PUT / DELETE → 405
    """

    fixtures = ["infrastructure/communities.json"]

    def setUp(self):
        self.client = APIClient()
        self.list_url = reverse("akitacommunity-list")

    def test_list_returns_200(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_returns_only_active_communities(self):
        """
        AkitaCommunityViewSet.queryset = AkitaCommunity.objects.filter(is_active=True).
        Only 4 of the 5 fixture records are active — exactly 4 must be returned.
        """
        response = self.client.get(self.list_url)
        self.assertEqual(len(response.data), 4)

    def test_inactive_ikarama_absent_from_list(self):
        """'ikarama' has is_active=False — must not appear in the list."""
        response = self.client.get(self.list_url)
        names = [item["name"] for item in response.data]
        self.assertNotIn("ikarama", names)

    def test_retrieve_active_akita_community_returns_200(self):
        pk = AkitaCommunity.objects.get(name="agbobiri").pk
        url = reverse("akitacommunity-detail", kwargs={"pk": pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "agbobiri")

    def test_retrieve_inactive_akita_community_returns_404(self):
        """
        'ikarama' is excluded from the queryset via is_active=False.
        Requesting its detail must return 404.
        """
        pk = AkitaCommunity.objects.get(name="ikarama").pk
        url = reverse("akitacommunity-detail", kwargs={"pk": pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_results_are_alphabetically_ordered(self):
        response = self.client.get(self.list_url)
        names = [item["name"] for item in response.data]
        self.assertEqual(names, sorted(names))

    def test_post_returns_405(self):
        """ReadOnlyModelViewSet — no create route."""
        response = self.client.post(
            self.list_url,
            {"name": "Agbobiri", "is_active": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_returns_405(self):
        pk = AkitaCommunity.objects.get(name="kalaba").pk
        url = reverse("akitacommunity-detail", kwargs={"pk": pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_unauthenticated_read_is_permitted(self):
        """IsAnonymousReadOnly allows all read requests without credentials."""
        self.client.force_authenticate(user=None)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────────────────────
# 3.  MediaTagViewSet  [ORIGINAL — unchanged]
# ─────────────────────────────────────────────────────────────────────────────

class MediaTagViewSetTest(APITestCase):

    fixtures = ["infrastructure/mediatags.json"]

    def setUp(self):
        self.client = APIClient()
        self.list_url = reverse("mediatag-list")

    def test_list_returns_200(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_returns_all_eight_records(self):
        response = self.client.get(self.list_url)
        self.assertEqual(len(response.data), 8)

    def test_retrieve_by_pk_returns_correct_record(self):
        pk = MediaTag.objects.get(name="Culture").pk
        url = reverse("mediatag-detail", kwargs={"pk": pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Culture")

    def test_post_returns_405(self):
        response = self.client.post(
            self.list_url, {"name": "New", "slug": "new"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_unauthenticated_read_is_permitted(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────────────────────
# 4.  CategoryViewSet  [ORIGINAL — unchanged]
# ─────────────────────────────────────────────────────────────────────────────

class CategoryViewSetTest(APITestCase):

    fixtures = ["infrastructure/categories.json"]

    def setUp(self):
        self.client = APIClient()
        self.list_url = reverse("category-list")

    def test_list_returns_200(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_returns_only_root_nodes(self):
        response = self.client.get(self.list_url)
        self.assertEqual(len(response.data), 3)
        for item in response.data:
            self.assertIsNone(item["parent"])

    def test_list_root_nodes_contain_nested_children(self):
        response = self.client.get(self.list_url)
        heritage = next(i for i in response.data if i["slug"] == "heritage")
        self.assertGreaterEqual(len(heritage["children"]), 2)

    def test_retrieve_root_node_by_pk(self):
        pk = Category.objects.get(slug="media").pk
        url = reverse("category-detail", kwargs={"pk": pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["slug"], "media")

    def test_retrieve_child_node_directly(self):
        pk = Category.objects.get(slug="oral-traditions").pk
        url = reverse("category-detail", kwargs={"pk": pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_returns_405(self):
        payload = {"name": "Test", "slug": "test", "parent": None, "description": ""}
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_returns_405(self):
        pk = Category.objects.get(slug="heritage").pk
        url = reverse("category-detail", kwargs={"pk": pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


# ─────────────────────────────────────────────────────────────────────────────
# 5.  SiteSettingViewSet — read path  [ORIGINAL — unchanged]
# ─────────────────────────────────────────────────────────────────────────────

class SiteSettingViewSetReadTest(APITestCase):

    fixtures = ["infrastructure/sitesettings.json"]

    def setUp(self):
        self.client = APIClient()
        self.list_url = reverse("sitesetting-list")

    def test_list_returns_200_for_anonymous_client(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_returns_all_eight_settings(self):
        response = self.client.get(self.list_url)
        self.assertEqual(len(response.data), 8)

    def test_retrieve_existing_setting_returns_200(self):
        pk = SiteSetting.objects.get(key="site_name").pk
        url = reverse("sitesetting-detail", kwargs={"pk": pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["key"], "site_name")

    def test_retrieve_nonexistent_pk_returns_404(self):
        url = reverse("sitesetting-detail", kwargs={"pk": 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ─────────────────────────────────────────────────────────────────────────────
# 6.  SiteSettingViewSet — write path  [ORIGINAL — unchanged]
# ─────────────────────────────────────────────────────────────────────────────

class SiteSettingViewSetWriteTest(APITestCase):

    fixtures = ["infrastructure/sitesettings.json"]

    def setUp(self):
        self.client = APIClient()
        self.list_url = reverse("sitesetting-list")
        self.admin = make_admin()
        self.regular_user = make_regular_user()

    def test_admin_can_create_new_setting(self):
        self.client.force_authenticate(user=self.admin)
        payload = {"key": "new_setting", "value": "hello", "description": "A new setting"}
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["key"], "new_setting")
        self.assertTrue(SiteSetting.objects.filter(key="new_setting").exists())

    def test_anonymous_user_cannot_create(self):
        payload = {"key": "hacked", "value": "pwned", "description": ""}
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_regular_user_cannot_create(self):
        self.client.force_authenticate(user=self.regular_user)
        payload = {"key": "hacked", "value": "pwned", "description": ""}
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_duplicate_key_returns_400(self):
        self.client.force_authenticate(user=self.admin)
        payload = {"key": "site_name", "value": "Clash", "description": ""}
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("key", response.data)

    def test_admin_can_fully_update_setting(self):
        self.client.force_authenticate(user=self.admin)
        pk = SiteSetting.objects.get(key="maintenance_mode").pk
        url = reverse("sitesetting-detail", kwargs={"pk": pk})
        payload = {"key": "maintenance_mode", "value": "true", "description": "Updated by test"}
        response = self.client.put(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["value"], "true")

    def test_anonymous_user_cannot_put(self):
        pk = SiteSetting.objects.get(key="maintenance_mode").pk
        url = reverse("sitesetting-detail", kwargs={"pk": pk})
        response = self.client.put(
            url,
            {"key": "maintenance_mode", "value": "true", "description": ""},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_partially_update_value(self):
        self.client.force_authenticate(user=self.admin)
        pk = SiteSetting.objects.get(key="items_per_page").pk
        url = reverse("sitesetting-detail", kwargs={"pk": pk})
        response = self.client.patch(url, {"value": "50"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["value"], "50")
        self.assertEqual(SiteSetting.objects.get(pk=pk).value, "50")

    def test_anonymous_user_cannot_patch(self):
        pk = SiteSetting.objects.get(key="items_per_page").pk
        url = reverse("sitesetting-detail", kwargs={"pk": pk})
        response = self.client.patch(url, {"value": "50"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_delete_setting(self):
        self.client.force_authenticate(user=self.admin)
        pk = SiteSetting.objects.get(key="social_twitter").pk
        url = reverse("sitesetting-detail", kwargs={"pk": pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(SiteSetting.objects.filter(pk=pk).exists())

    def test_anonymous_user_cannot_delete(self):
        pk = SiteSetting.objects.get(key="social_twitter").pk
        url = reverse("sitesetting-detail", kwargs={"pk": pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(SiteSetting.objects.filter(pk=pk).exists())

    def test_regular_user_cannot_delete(self):
        self.client.force_authenticate(user=self.regular_user)
        pk = SiteSetting.objects.get(key="social_twitter").pk
        url = reverse("sitesetting-detail", kwargs={"pk": pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ─────────────────────────────────────────────────────────────────────────────
# 7.  Explicit teardown demonstration  [ORIGINAL — unchanged]
# ─────────────────────────────────────────────────────────────────────────────

class ExplicitTeardownDemonstrationTest(APITestCase):

    def _create_all_records(self):
        self.community = Community.objects.create(
            name="kalaba",
            alternate_names="Kalaba Quarters",
            description="Test community",
        )
        self.tag = MediaTag.objects.create(
            name="TestTag", slug="test-tag", description="A tag for testing",
        )
        self.root_cat = Category.objects.create(
            name="Root", slug="root", description="Root category",
        )
        self.child_cat = Category.objects.create(
            name="Child", slug="child", parent=self.root_cat,
            description="Child category",
        )
        self.setting = SiteSetting.objects.create(
            key="test_key", value="test_value", description="Temp setting",
        )

    def _destroy_all_records(self):
        SiteSetting.objects.filter(key="test_key").delete()
        Category.objects.filter(slug__in=["child", "root"]).delete()
        MediaTag.objects.filter(slug="test-tag").delete()
        Community.objects.filter(name="kalaba").delete()

    def test_create_use_and_destroy_records(self):
        self._create_all_records()
        try:
            self.assertTrue(Community.objects.filter(name="kalaba").exists())
            url = reverse("community-list")
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            names = [r["name"] for r in response.data]
            self.assertIn("kalaba", names)
        finally:
            self._destroy_all_records()
            self.assertFalse(Community.objects.filter(name="kalaba").exists())
            self.assertFalse(MediaTag.objects.filter(slug="test-tag").exists())
            self.assertFalse(Category.objects.filter(slug="root").exists())
            self.assertFalse(SiteSetting.objects.filter(key="test_key").exists())

    def test_admin_full_crud_lifecycle_on_sitesetting(self):
        admin = make_admin(username="admin2")
        self.client.force_authenticate(user=admin)
        list_url = reverse("sitesetting-list")

        payload = {
            "key": "lifecycle_key", "value": "lifecycle_value",
            "description": "Lifecycle test",
        }
        post_resp = self.client.post(list_url, payload, format="json")
        self.assertEqual(post_resp.status_code, status.HTTP_201_CREATED)
        created_pk = post_resp.data["id"]

        detail_url = reverse("sitesetting-detail", kwargs={"pk": created_pk})
        get_resp = self.client.get(detail_url)
        self.assertEqual(get_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(get_resp.data["value"], "lifecycle_value")

        patch_resp = self.client.patch(detail_url, {"value": "updated_value"}, format="json")
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_resp.data["value"], "updated_value")

        del_resp = self.client.delete(detail_url)
        self.assertEqual(del_resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(SiteSetting.objects.filter(pk=created_pk).exists())

        gone_resp = self.client.get(detail_url)
        self.assertEqual(gone_resp.status_code, status.HTTP_404_NOT_FOUND)
