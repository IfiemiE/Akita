from .models import AkitaUser, SpeakerProfile
from .serializers import AkitaUserSerializer, SpeakerProfileSerializer
from apps.common.permissions import IsAnonymousReadOnly
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework import permissions
from apps.common.permissions import IsContributor
from django_filters.rest_framework import DjangoFilterBackend


class UserViewSet(ReadOnlyModelViewSet):
    """Public read-only user profiles."""
    queryset = AkitaUser.objects.filter(is_active=True)
    serializer_class = AkitaUserSerializer
    permission_classes = [IsAnonymousReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['role', 'community', 'contributor_level']
 
    
class SpeakerProfileViewSet(ModelViewSet):
    """Speaker profiles: public read, contributor+ write."""
    queryset = SpeakerProfile.objects.all()
    serializer_class = SpeakerProfileSerializer
    permission_classes = [IsAnonymousReadOnly]

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [IsAnonymousReadOnly()]
        return [IsContributor()]
