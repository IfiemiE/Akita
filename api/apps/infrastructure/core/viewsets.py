from apps.infrastructure.core.models import Community, MediaTag, Category, SiteSetting
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from apps.infrastructure.core.serializers import (
    CommunitySerializer, MediaTagSerializer, CategorySerializer, SiteSettingSerializer
)
from apps.common.permissions import IsAnonymousReadOnly

class CommunityViewSet(ReadOnlyModelViewSet):
    """Public read-only access to communities."""
    queryset = Community.objects.filter(is_active=True)
    serializer_class = CommunitySerializer
    permission_classes = [IsAnonymousReadOnly]


class MediaTagViewSet(ReadOnlyModelViewSet):
    """Public read-only access to tags."""
    queryset = MediaTag.objects.all()
    serializer_class = MediaTagSerializer
    permission_classes = [IsAnonymousReadOnly]


class CategoryViewSet(ReadOnlyModelViewSet):
    """Public read-only access to categories."""
    queryset = Category.objects.filter(parent__isnull=True)
    serializer_class = CategorySerializer
    permission_classes = [IsAnonymousReadOnly]


class SiteSettingViewSet(ModelViewSet):
    """Admin write, others read-only."""
    queryset = SiteSetting.objects.all()
    serializer_class = SiteSettingSerializer
    permission_classes = [IsAdminOrAbove]

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [IsAnonymousReadOnly()]
        return super().get_permissions()

