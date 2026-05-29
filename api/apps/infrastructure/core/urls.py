from django.urls import path
from rest_framework.routers import DefaultRouter
from .viewsets import (
    CommunityViewSet,
    MediaTagViewSet,
    CategoryViewSet,
    SiteSettingViewSet,
)
router = DefaultRouter()
router.register('communities', CommunityViewSet, basename='community')
router.register('tags', MediaTagViewSet, basename='tag')
router.register('categories', CategoryViewSet, basename='category')
router.register('settings', SiteSettingViewSet, basename='sitesetting')

urlpatterns = router.urls