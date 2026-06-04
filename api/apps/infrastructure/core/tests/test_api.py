"""
Tests the HTTP/API layer for each viewset individually.
Every test goes through APIClient — URL routing, authentication,
permission classes, and response shape are all exercised here.

Coverage
--------
  CommunityViewSet      (ReadOnlyModelViewSet)
  MediaTagViewSet       (ReadOnlyModelViewSet)
  CategoryViewSet       (ReadOnlyModelViewSet)
  SiteSettingViewSet    (ModelViewSet — split permissions)
  ExplicitTeardownDemonstrationTest  (manual create→use→destroy pattern)

Not covered here
----------------
  Cross-model / combined fixture tests → see test_combined.py

Fixtures
--------
  Declared per class. Django resolves 'infrastructure/...' relative to
  each directory in FIXTURE_DIRS (api/fixtures/ in config/settings/test.py).

  community.json   → 5 Community records  (1 inactive: ikarama)
  mediatag.json    → 8 MediaTag records
  category.json    → 9 Category records   (3 roots, 5 children, 1 grandchild)
  sitesetting.json → 8 SiteSetting records

URL basenames expected in the router registration (urls.py):
  community   → CommunityViewSet
  mediatag    → MediaTagViewSet
  category    → CategoryViewSet
  sitesetting → SiteSettingViewSet

Run
---
  $ python manage.py test TEST_DOTTED_PATH -v 2 --settings=config.settings.test
      
where 
TEST_DOTTED_PATH = apps.infrastructure.core.tests.test_api.CLASS.METHOD for a specific test METHOD
TEST_DOTTED_PATH = apps.infrastructure.core.tests.test_api.CLASS for a specific test CLASS
TEST_DOTTED_PATH = apps.infrastructure.core.tests.test_api for the specific test_models module
TEST_DOTTED_PATH = apps.infrastructure.core.tests for all modules in the test folder
"""

from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from apps.infrastructure.core.models import Community, MediaTag, Category, SiteSetting

User = get_user_model()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_admin(username="admin", password="adminpass123"):
    """
    Create a superuser for write-permission tests.
    Uses a fast password hasher (MD5PasswordHasher) configured in
    config/settings/test.py so this call does not slow down the suite.
    """
    return User.objects.create_superuser(
        username=username, password=password, email=f"{username}@test.com"
    )


def make_regular_user(username="user", password="userpass123"):
    """
    Create a non-admin authenticated user for permission-denial tests.
    This user must be refused on all write operations to SiteSettingViewSet.
    """
    return User.objects.create_user(
        username=username, password=password, email=f"{username}@test.com"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1.  CommunityViewSet
# ─────────────────────────────────────────────────────────────────────────────

class CommunityViewSetTest(APITestCase):
    """
    CommunityViewSet is a ReadOnlyModelViewSet with:
      queryset           = Community.objects.filter(is_active=True)

    Expected behaviour
    ------------------
    - GET list/retrieve → 200 for all clients (unauthenticated or not)
    - Inactive community ('ikarama') absent from list and returns 404 on retrieve
    - POST / PUT / DELETE → 405 (route not registered by ReadOnlyModelViewSet)
    """

    fixtures = ["infrastructure/communities.json"]

    def setUp(self):
        self.client = APIClient()
        self.list_url = reverse("community-list")

    # -- list -----------------------------------------------------------------

    def test_list_returns_200(self):
        """
        Unauthenticated GET on the list endpoint must return 200.
        IsAnonymousReadOnly permits all read requests.
        """
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_excludes_inactive_community(self):
        """
        The viewset queryset filters to is_active=True.
        Only 4 of the 5 fixture records are active — exactly 4 must be returned.
        """
        response = self.client.get(self.list_url)
        self.assertEqual(len(response.data), 4)

    def test_inactive_community_absent_from_list(self):
        """
        'ikarama' has is_active=False in the fixture.
        It must not appear anywhere in the list response body.
        """
        response = self.client.get(self.list_url)
        names = [item["name"] for item in response.data]
        self.assertNotIn("ikarama", names)

    def test_list_results_are_alphabetically_ordered(self):
        """
        Meta.ordering = ['name'] must be reflected in the API response.
        The name values must appear in sorted order.
        """
        response = self.client.get(self.list_url)
        names = [item["name"] for item in response.data]
        self.assertEqual(names, sorted(names))

    def test_list_items_contain_all_declared_fields(self):
        """
        Each item in the list response must expose all five serializer fields:
        id, name, alternate_names, description, is_active.
        """
        response = self.client.get(self.list_url)
        first = response.data[0]
        for field in ("id", "name", "alternate_names", "description", "is_active"):
            self.assertIn(field, first)

    # -- retrieve -------------------------------------------------------------

    def test_retrieve_active_community_returns_200(self):
        """
        GET on a detail URL for an active community must return 200
        with the correct name in the response body.
        """
        pk = Community.objects.get(name="agbobiri").pk
        url = reverse("community-detail", kwargs={"pk": pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "agbobiri")

    def test_retrieve_inactive_community_returns_404(self):
        """
        'ikarama' is excluded from the viewset queryset.
        Requesting its detail URL must return 404 — the record exists in the
        DB but the viewset cannot see it through its filtered queryset.
        """
        pk = Community.objects.get(name="ikarama").pk
        url = reverse("community-detail", kwargs={"pk": pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # -- write prohibition ----------------------------------------------------

    def test_post_returns_405(self):
        """
        ReadOnlyModelViewSet does not register a create route.
        POST must return 405 Method Not Allowed.
        """
        payload = {"name": "agbobiri", "alternate_names": "", "description": "", "is_active": True}
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_put_returns_405(self):
        """PUT must return 405 — no update route registered."""
        pk = Community.objects.get(name="agbobiri").pk
        url = reverse("community-detail", kwargs={"pk": pk})
        response = self.client.put(url, {"name": "agbobiri"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_returns_405(self):
        """DELETE must return 405 — no destroy route registered."""
        pk = Community.objects.get(name="agbobiri").pk
        url = reverse("community-detail", kwargs={"pk": pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


# ─────────────────────────────────────────────────────────────────────────────
# 2.  MediaTagViewSet
# ─────────────────────────────────────────────────────────────────────────────

class MediaTagViewSetTest(APITestCase):
    """
    MediaTagViewSet is a ReadOnlyModelViewSet with:
      queryset           = MediaTag.objects.all()

    No queryset filtering is applied — all records are always returned.
    """

    fixtures = ["infrastructure/mediatags.json"]

    def setUp(self):
        self.client = APIClient()
        self.list_url = reverse("mediatag-list")

    def test_list_returns_200(self):
        """Unauthenticated GET must return 200."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_returns_all_eight_records(self):
        """
        No filtering on MediaTagViewSet — all 8 fixture records must be
        returned in the list response.
        """
        response = self.client.get(self.list_url)
        self.assertEqual(len(response.data), 8)

    def test_retrieve_by_pk_returns_correct_record(self):
        """
        Detail URL for the 'Culture' tag must return 200 with
        name='Culture' in the response body.
        """
        pk = MediaTag.objects.get(name="Culture").pk
        url = reverse("mediatag-detail", kwargs={"pk": pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Culture")

    def test_post_returns_405(self):
        """No create route registered — POST must return 405."""
        response = self.client.post(
            self.list_url, {"name": "New", "slug": "new"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_unauthenticated_read_is_permitted(self):
        """
        IsAnonymousReadOnly must allow reads with no credentials.
        Explicitly clearing auth and retrying must still return 200.
        """
        self.client.force_authenticate(user=None)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────────────────────
# 3.  CategoryViewSet
# ─────────────────────────────────────────────────────────────────────────────

class CategoryViewSetTest(APITestCase):
    """
    CategoryViewSet is a ReadOnlyModelViewSet with:
      queryset           = Category.objects.filter(parent__isnull=True)

    The list endpoint returns only root nodes.  Children are nested inside
    each root's serialized representation via CategorySerializer.get_children().
    The retrieve endpoint is NOT filtered — any PK is accessible directly.
    """

    fixtures = ["infrastructure/categories.json"]

    def setUp(self):
        self.client = APIClient()
        self.list_url = reverse("category-list")

    # -- list -----------------------------------------------------------------

    def test_list_returns_200(self):
        """Unauthenticated GET must return 200."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_returns_only_root_nodes(self):
        """
        queryset filters to parent__isnull=True — 3 root nodes in the fixture.
        Each item in the response must have parent=null.
        """
        response = self.client.get(self.list_url)
        self.assertEqual(len(response.data), 3)
        for item in response.data:
            self.assertIsNone(item["parent"])

    def test_list_root_nodes_contain_nested_children(self):
        """
        CategorySerializer.get_children() recursively nests children.
        The 'heritage' root must have at least 2 items in its 'children' list.
        """
        response = self.client.get(self.list_url)
        heritage = next(i for i in response.data if i["slug"] == "heritage")
        self.assertGreaterEqual(len(heritage["children"]), 2)

    # -- retrieve -------------------------------------------------------------

    def test_retrieve_root_node_by_pk(self):
        """
        GET on a root node's detail URL must return 200 with the
        correct slug in the response body.
        """
        pk = Category.objects.get(slug="media").pk
        url = reverse("category-detail", kwargs={"pk": pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["slug"], "media")

    def test_retrieve_child_node_directly(self):
        """
        The retrieve action uses the base queryset (all categories), not the
        list queryset (roots only).  A child node must be accessible directly
        via its detail URL even though it does not appear in the list.
        """
        pk = Category.objects.get(slug="oral-traditions").pk
        url = reverse("category-detail", kwargs={"pk": pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # -- write prohibition ----------------------------------------------------

    def test_post_returns_405(self):
        """No create route — POST must return 405."""
        payload = {"name": "Test", "slug": "test", "parent": None, "description": ""}
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_returns_405(self):
        """No destroy route — DELETE must return 405."""
        pk = Category.objects.get(slug="governance").pk
        url = reverse("category-detail", kwargs={"pk": pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


# ─────────────────────────────────────────────────────────────────────────────
# 4.  SiteSettingViewSet — read path
# ─────────────────────────────────────────────────────────────────────────────

class SiteSettingViewSetReadTest(APITestCase):
    """
    SiteSettingViewSet is a full ModelViewSet.  get_permissions() returns
    IsAnonymousReadOnly for safe methods (GET, HEAD, OPTIONS), and
    IsAdminOrAbove for unsafe methods.

    This class covers the read path only — no authentication needed.
    """

    fixtures = ["infrastructure/sitesettings.json"]

    def setUp(self):
        self.client = APIClient()
        self.list_url = reverse("sitesetting-list")

    def test_list_returns_200_for_anonymous_client(self):
        """
        Unauthenticated GET on the list endpoint must return 200.
        get_permissions() uses IsAnonymousReadOnly for safe methods.
        """
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_returns_all_eight_settings(self):
        """
        No queryset filtering on SiteSettingViewSet.
        All 8 fixture records must appear in the list response.
        """
        response = self.client.get(self.list_url)
        self.assertEqual(len(response.data), 8)

    def test_retrieve_existing_setting_returns_200(self):
        """
        GET on a detail URL for a known key must return 200 with the
        correct key value in the response body.
        """
        pk = SiteSetting.objects.get(key="site_name").pk
        url = reverse("sitesetting-detail", kwargs={"pk": pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["key"], "site_name")

    def test_retrieve_nonexistent_pk_returns_404(self):
        """
        Requesting a PK that does not exist must return 404, not 500.
        DRF's get_object() raises Http404 which is rendered as a 404 response.
        """
        url = reverse("sitesetting-detail", kwargs={"pk": 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ─────────────────────────────────────────────────────────────────────────────
# 5.  SiteSettingViewSet — write path (permission matrix)
# ─────────────────────────────────────────────────────────────────────────────

class SiteSettingViewSetWriteTest(APITestCase):
    """
    Covers all unsafe HTTP methods and the full permission matrix:

      Anonymous user  → 403 on all writes
      Regular user    → 403 on all writes  (IsAdminOrAbove blocks non-admins)
      Admin user      → 201 / 200 / 204 as appropriate

    Also covers validation errors returned through the API (400).
    """

    fixtures = ["infrastructure/sitesettings.json"]

    def setUp(self):
        self.client = APIClient()
        self.list_url = reverse("sitesetting-list")
        self.admin = make_admin()
        self.regular_user = make_regular_user()

    # -- POST -----------------------------------------------------------------

    def test_admin_can_create_new_setting(self):
        """
        Admin POST with valid data must return 201 Created.
        The new record must exist in the DB after the request.
        """
        self.client.force_authenticate(user=self.admin)
        payload = {"key": "new_setting", "value": "hello", "description": "A new setting"}
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["key"], "new_setting")
        self.assertTrue(SiteSetting.objects.filter(key="new_setting").exists())

    def test_anonymous_user_cannot_create(self):
        """
        Unauthenticated POST must return 403.
        IsAnonymousReadOnly blocks all writes for unauthenticated clients.
        """
        payload = {"key": "hacked", "value": "pwned", "description": ""}
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_regular_user_cannot_create(self):
        """
        An authenticated but non-admin user must receive 403.
        IsAdminOrAbove gates all write operations to admin-level users.
        """
        self.client.force_authenticate(user=self.regular_user)
        payload = {"key": "hacked", "value": "pwned", "description": ""}
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_duplicate_key_returns_400(self):
        """
        Admin POST with a key that already exists must return 400 Bad Request.
        The unique constraint is enforced at the serializer level, so the
        error detail must contain 'key' as a field error.
        """
        self.client.force_authenticate(user=self.admin)
        payload = {"key": "site_name", "value": "Clash", "description": ""}
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("key", response.data)

    # -- PUT ------------------------------------------------------------------

    def test_admin_can_fully_update_setting(self):
        """
        Admin PUT with all required fields must return 200 and update the
        'value' field in the response body.
        """
        self.client.force_authenticate(user=self.admin)
        pk = SiteSetting.objects.get(key="maintenance_mode").pk
        url = reverse("sitesetting-detail", kwargs={"pk": pk})
        payload = {"key": "maintenance_mode", "value": "true", "description": "Updated by test"}
        response = self.client.put(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["value"], "true")

    def test_anonymous_user_cannot_put(self):
        """Unauthenticated PUT must return 403."""
        pk = SiteSetting.objects.get(key="maintenance_mode").pk
        url = reverse("sitesetting-detail", kwargs={"pk": pk})
        response = self.client.put(
            url,
            {"key": "maintenance_mode", "value": "true", "description": ""},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # -- PATCH ----------------------------------------------------------------

    def test_admin_can_partially_update_value(self):
        """
        Admin PATCH with only 'value' must return 200.
        The new value must be reflected in both the response body and the DB.
        """
        self.client.force_authenticate(user=self.admin)
        pk = SiteSetting.objects.get(key="items_per_page").pk
        url = reverse("sitesetting-detail", kwargs={"pk": pk})
        response = self.client.patch(url, {"value": "50"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["value"], "50")
        self.assertEqual(SiteSetting.objects.get(pk=pk).value, "50")

    def test_anonymous_user_cannot_patch(self):
        """Unauthenticated PATCH must return 403."""
        pk = SiteSetting.objects.get(key="items_per_page").pk
        url = reverse("sitesetting-detail", kwargs={"pk": pk})
        response = self.client.patch(url, {"value": "50"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # -- DELETE ---------------------------------------------------------------

    def test_admin_can_delete_setting(self):
        """
        Admin DELETE must return 204 No Content.
        The record must no longer exist in the DB after the request.
        """
        self.client.force_authenticate(user=self.admin)
        pk = SiteSetting.objects.get(key="social_twitter").pk
        url = reverse("sitesetting-detail", kwargs={"pk": pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(SiteSetting.objects.filter(pk=pk).exists())

    def test_anonymous_user_cannot_delete(self):
        """
        Unauthenticated DELETE must return 403.
        The record must still exist in the DB — the deletion was blocked.
        """
        pk = SiteSetting.objects.get(key="social_twitter").pk
        url = reverse("sitesetting-detail", kwargs={"pk": pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(SiteSetting.objects.filter(pk=pk).exists())

    def test_regular_user_cannot_delete(self):
        """
        Authenticated but non-admin DELETE must return 403.
        IsAdminOrAbove rejects any user who is not admin-level.
        """
        self.client.force_authenticate(user=self.regular_user)
        pk = SiteSetting.objects.get(key="social_twitter").pk
        url = reverse("sitesetting-detail", kwargs={"pk": pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ─────────────────────────────────────────────────────────────────────────────
# 6.  Explicit teardown demonstration
# ─────────────────────────────────────────────────────────────────────────────

class ExplicitTeardownDemonstrationTest(APITestCase):
    """
    Demonstrates the manual create → use → destroy pattern.

    Django's TestCase rolls back every test automatically via transaction
    wrapping, so explicit deletion is never required in normal tests.
    This class is illustrative — it shows the pattern for situations where
    you need it: file-system side-effects, external service calls, or when
    you want to assert on the post-delete DB state within the same test.

    No fixtures are declared at the class level; all records are created
    and destroyed programmatically within each test method.
    """

    def _create_all_records(self):
        """Programmatically create one record per model."""
        self.community = Community.objects.create(
            name="kalaba",
            alternate_names="Kalaba Quarters",
            description="Test community",
            is_active=True,
        )
        self.tag = MediaTag.objects.create(
            name="TestTag",
            slug="test-tag",
            description="A tag for testing",
        )
        self.root_cat = Category.objects.create(
            name="Root",
            slug="root",
            description="Root category",
        )
        self.child_cat = Category.objects.create(
            name="Child",
            slug="child",
            parent=self.root_cat,
            description="Child category",
        )
        self.setting = SiteSetting.objects.create(
            key="test_key",
            value="test_value",
            description="Temp setting",
        )

    def _destroy_all_records(self):
        """
        Explicitly delete every record created by _create_all_records().
        Child category is listed before root to be explicit, though CASCADE
        would handle it either way.
        """
        SiteSetting.objects.filter(key="test_key").delete()
        Category.objects.filter(slug__in=["child", "root"]).delete()
        MediaTag.objects.filter(slug="test-tag").delete()
        Community.objects.filter(name="kalaba").delete()

    def test_create_use_and_destroy_records(self):
        """
        Full manual lifecycle across all four models:
        1. Create records programmatically
        2. Verify they are reachable via the API
        3. Explicitly delete them
        4. Assert they are gone from the DB

        The try/finally guarantees step 4 runs even if step 2 or 3 raises.
        """
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
        """
        Exercises the complete CRUD lifecycle for SiteSetting through
        the API as an admin user:

          POST   → 201  (record created)
          GET    → 200  (record readable)
          PATCH  → 200  (record updated, new value confirmed)
          DELETE → 204  (record deleted)
          GET    → 404  (deletion confirmed via API)
        """
        admin = make_admin(username="admin2")
        self.client.force_authenticate(user=admin)
        list_url = reverse("sitesetting-list")

        # CREATE
        payload = {
            "key": "lifecycle_key",
            "value": "lifecycle_value",
            "description": "Lifecycle test",
        }
        post_resp = self.client.post(list_url, payload, format="json")
        self.assertEqual(post_resp.status_code, status.HTTP_201_CREATED)
        created_pk = post_resp.data["id"]

        # READ
        detail_url = reverse("sitesetting-detail", kwargs={"pk": created_pk})
        get_resp = self.client.get(detail_url)
        self.assertEqual(get_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(get_resp.data["value"], "lifecycle_value")

        # UPDATE
        patch_resp = self.client.patch(detail_url, {"value": "updated_value"}, format="json")
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_resp.data["value"], "updated_value")

        # DESTROY
        del_resp = self.client.delete(detail_url)
        self.assertEqual(del_resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(SiteSetting.objects.filter(pk=created_pk).exists())

        # CONFIRM GONE VIA API
        gone_resp = self.client.get(detail_url)
        self.assertEqual(gone_resp.status_code, status.HTTP_404_NOT_FOUND)
