from rest_framework import serializers
from .models import SpeakerProfile
from apps.identity.users.models import AkitaUser


class SpeakerProfileSerializer(serializers.ModelSerializer):
    community_name = serializers.SerializerMethodField()
    user_account_username = serializers.SerializerMethodField()
    
    documented_by = serializers.PrimaryKeyRelatedField(
        queryset=AkitaUser.objects.all(),
        required=True,
        allow_null=False,
    )
    documented_by_name = serializers.CharField(source='documented_by.username', read_only=True)

    class Meta:
        model = SpeakerProfile
        fields = [
            'id', 'full_name', 'community', 'community_name',
            'birth_year', 'is_living', 'community_note',
            'speaker_user_account', 'user_account_username', 
            'documented_by', 'documented_by_name'
        ]

    def get_community_name(self, obj):
        return obj.community.name if obj.community else None

    def get_user_account_username(self, obj):
        return obj.speaker_user_account.username if obj.speaker_user_account else None