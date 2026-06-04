from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework import permissions

from .models import Community, MediaTag, Category, SiteSetting
from .serializers import (
    CommunitySerializer, MediaTagSerializer, CategorySerializer, SiteSettingSerializer
)
from apps.common.permissions import IsAnonymousReadOnly, IsAdminOrAbove


class CommunityViewSet(ReadOnlyModelViewSet):
    """Public read-only access to communities."""
    queryset = Community.objects.filter(is_active=True)
    serializer_class = CommunitySerializer
    

class MediaTagViewSet(ReadOnlyModelViewSet):
    """Public read-only access to tags."""
    queryset = MediaTag.objects.all()
    serializer_class = MediaTagSerializer
    

class CategoryViewSet(ReadOnlyModelViewSet):
    """Public read-only access to categories."""
    serializer_class = CategorySerializer

    def get_queryset(self):
        if self.action == 'list':
            return Category.objects.filter(parent__isnull=True)
        return Category.objects.all()
    

class SiteSettingViewSet(ModelViewSet):
    """Admin write, others read-only."""
    queryset = SiteSetting.objects.all()
    serializer_class = SiteSettingSerializer
    permission_classes = [IsAdminOrAbove]

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [IsAnonymousReadOnly()]
        return super().get_permissions()
