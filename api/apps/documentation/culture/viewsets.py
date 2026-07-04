from .models import SpeakerProfile
from .serializers import SpeakerProfileSerializer
from apps.common.permissions import IsAnonymousReadOnly, IsContributor
from rest_framework.viewsets import ModelViewSet
from rest_framework import permissions


class SpeakerProfileViewSet(ModelViewSet):
    """Speaker profiles: public read, contributor+ write."""
    queryset = SpeakerProfile.objects.all()
    serializer_class = SpeakerProfileSerializer
    permission_classes = [IsAnonymousReadOnly]

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [IsAnonymousReadOnly()]
        return [IsContributor()]
