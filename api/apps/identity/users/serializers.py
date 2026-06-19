from rest_framework import serializers
from .models import UserRole, AkitaUser, SpeakerProfile
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from apps.common.permissions import get_user_role_level


class AkitaUserSerializer(serializers.ModelSerializer):
    community_name = serializers.SerializerMethodField()
    registered_by_name = serializers.CharField(source='registered_by.username', read_only=True)
    elevated_by_name = serializers.SerializerMethodField()
    role_level = serializers.IntegerField(source='get_role_level', read_only=True)
    
    def get_community_name(self, obj):
        return obj.community.name if obj.community_id else None

    def get_elevated_by_name(self, obj):
        return obj.elevated_by.username if obj.elevated_by_id else None

    class Meta:
        model = AkitaUser
        fields = [
            'id', 'username', 'first_name', 'slug', 'last_name', 'email',
            'role', 'role_level', 'community', 'community_name',
            'registered_by', 'registered_by_name', 'registration_date',
            'registration_notes', 'speaks_for_self',
            'elevated_by', 'elevated_by_name', 'elevated_at', 'elevation_notes',
            'date_joined', 'is_active'
        ]
        read_only_fields = [
            'role', 'slug', 'role_level', 'registered_by', 'registration_date',
            'elevated_by', 'elevated_at', 'date_joined'
        ]


class ContributorRegistrationSerializer(serializers.ModelSerializer):
    """Admin/Editor/Superuser: register a new user with role strictly below their own."""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(
        choices=UserRole.choices,
        default=UserRole.CONTRIBUTOR,
        help_text="Role for the new user. Must be strictly below registrar's role level."
    )

    class Meta:
        model = AkitaUser
        fields = [
            'username', 'password', 'password_confirm',
            'first_name', 'last_name', 'email',
            'role', 'community', 'registration_notes', 'speaks_for_self'
        ]
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def validate_role(self, value):
        """Ensure registrar can only assign roles strictly below their own level."""
        registrar = self.context['request'].user
        registrar_level = registrar.get_role_level()
        target_level = get_user_role_level(value)

        if target_level >= registrar_level:
            available = [
                r for r, label in UserRole.choices 
                if get_user_role_level(r) < registrar_level
            ]
            raise serializers.ValidationError(
                f"Cannot assign role '{value}' — you may only register users with roles below your own level "
                f"({registrar.role}). Available: {', '.join(available)}."
            )
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        user = AkitaUser.objects.create_user(**validated_data)
        user.registered_by = self.context['request'].user
        user.save()
        return user


class UserManagementSerializer(serializers.ModelSerializer):
    community_name = serializers.SerializerMethodField()
    registered_by_name = serializers.CharField(source='registered_by.username', read_only=True)
    elevated_by_name = serializers.SerializerMethodField()
    role_level = serializers.IntegerField(source='get_role_level', read_only=True)
    
    def get_community_name(self, obj):
        return obj.community.name if obj.community_id else None

    def get_elevated_by_name(self, obj):
        return obj.elevated_by.username if obj.elevated_by_id else None

    class Meta:
        model = AkitaUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'role_level', 'is_active',
            'community', 'community_name',
            'registered_by', 'registered_by_name', 'registration_date',
            'registration_notes', 'speaks_for_self',
            'elevated_by', 'elevated_by_name', 'elevated_at', 'elevation_notes'
        ]
        read_only_fields = [
            'registered_by', 'registration_date',
            'elevated_by', 'elevated_at'
        ]


class UserElevationSerializer(serializers.Serializer):
    """Rank ladder: Contributor < Editor < Admin < Superuser"""
    user_id = serializers.IntegerField()
    elevation_notes = serializers.CharField(required=False, allow_blank=True)
    new_role = serializers.ChoiceField(
        choices= [
            ('editor', 'Editor/Moderator'),
            ('admin', 'Admin'),
            ('superuser', 'Superuser')
        ],
        default = 'editor',
        help_text = "For non-superusers: assigned role must be strictly below session user's own current role"
        
    )
    
    def validate_user_id(self, value):
        try:
            self._new_role_user = AkitaUser.objects.get(pk=value)
            self._session_user = self.context['request'].user  
        except AkitaUser.DoesNotExist:
            raise serializers.ValidationError("User not found.")
        if self._new_role_user == UserRole.SUPERUSER:
            raise serializers.ValidationError("SuperUsers cannot be elevated.")
        if self._new_role_user == self.context['request'].user:
            raise serializers.ValidationError("Cannot elevate yourself.")
        if not self._session_user.can_elevate_user(self._new_role_user):
            raise serializers.ValidationError('Cannot elevate this user')
        return value
    
    def validate_new_role(self, value): 
        #new_role_user = self._new_role_user
        if  get_user_role_level(self._new_role_user.role) <= get_user_role_level(self.new_role):
            raise serializers.ValidationError('assigned new role should be higher than current role')
        return value

    def create(self, validated_data):
        user = AkitaUser.objects.get(pk=validated_data['user_id'])
        user.role = self.new_role
        user.elevated_by = self.context['request'].user
        user.elevated_at = timezone.now()
        user.elevation_notes = validated_data.get('elevation_notes', '')
        user.save()
        return user


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