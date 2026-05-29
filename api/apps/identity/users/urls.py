from django.urls import path
from rest_framework.routers import DefaultRouter
from .viewsets import (
    UserViewSet,
    SpeakerProfileViewSet,
)
router = DefaultRouter()
router.register('enrolled', UserViewSet, basename='user')
router.register('speakers', SpeakerProfileViewSet, basename='speaker')

urlpatterns = router.urls