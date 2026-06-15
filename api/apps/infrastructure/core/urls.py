from django.urls import path
from rest_framework.routers import DefaultRouter
from .viewsets import (
    LanguageViewSet,
    DialectViewSet,
    CommunityViewSet,
    MediaTagViewSet,
    CategoryViewSet,
    SiteSettingViewSet,
    AkitaCommunityViewSet,
)
router = DefaultRouter()
router.register('communities', CommunityViewSet, basename='community')
router.register('tags', MediaTagViewSet, basename='mediatag')
router.register('categories', CategoryViewSet, basename='category')
router.register('settings', SiteSettingViewSet, basename='sitesetting')
router.register('languages', LanguageViewSet, basename='language')
router.register('dialects', DialectViewSet, basename='dialect')
router.register('akita_communities', AkitaCommunityViewSet, basename='akita_community')

urlpatterns = router.urls