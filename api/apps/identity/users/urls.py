from django.urls import path
from rest_framework.routers import DefaultRouter
from .viewsets import UserViewSet


router = DefaultRouter()
router.register('contributors', UserViewSet, basename='user')

urlpatterns = router.urls