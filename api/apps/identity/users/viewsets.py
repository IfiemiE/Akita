from .models import AkitaUser
from .serializers import AkitaUserSerializer
from apps.common.permissions import IsEditorOrAbove
from rest_framework.viewsets import ReadOnlyModelViewSet
from django_filters.rest_framework import DjangoFilterBackend


class UserViewSet(ReadOnlyModelViewSet):
    """Public read-only user profiles."""
    queryset = AkitaUser.objects.filter(is_active=True)
    serializer_class = AkitaUserSerializer
    permission_classes = [IsEditorOrAbove]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['role', 'community', 'first_name', 'last_name']
 