from django.db import models
from django.contrib.auth.models import AbstractUser
from apps.infrastructure.core.models import Community
from django.core.validators import MinValueValidator, MaxValueValidator

class UserRole(models.TextChoices):
    SUPERUSER = 'superuser', 'Superuser'
    ADMIN = 'admin', 'Admin'
    EDITOR = 'editor', 'Editor/Moderator'
    CONTRIBUTOR = 'contributor', 'Contributor'


class AkitaUser(AbstractUser):
    """
    Custom user model with role hierarchy, community affiliation,
    contributor levels, and elevation tracking.
    """
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.CONTRIBUTOR,
        db_index=True
    )
    community = models.ForeignKey(
        Community,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members'
    )
    contributor_level = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(99)],
        help_text="Higher levels can deactivate lower levels (1-99)"
    )
    registered_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registered_users',
        help_text="Admin or Editor who physically identified this contributor"
    )
    registration_date = models.DateTimeField(auto_now_add=True)
    registration_notes = models.TextField(
        blank=True,
        help_text="Context of physical identification"
    )
    speaks_for_self = models.BooleanField(
        default=True,
        help_text="This contributor is also a speaker"
    )
    # Elevation tracking (Contributor → Editor)
    elevated_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='elevated_users',
        help_text="Admin who promoted this user to Editor"
    )
    elevated_at = models.DateTimeField(null=True, blank=True)
    elevation_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-contributor_level', 'date_joined']

    def can_register_contributor(self):
        """Editors, Admins, and Superusers can register contributors."""
        return self.role in [
            UserRole.SUPERUSER, UserRole.ADMIN, UserRole.EDITOR
        ]

    def can_elevate_to_editor(self):
        """Only Admins and Superusers can elevate to Editor."""
        return self.role in [UserRole.SUPERUSER, UserRole.ADMIN]

    def can_manage_user(self, target_user):
        """
        Higher-level contributors can deactivate lower levels.
        Same-level deactivation is blocked.
        Superusers can deactivate other superusers (exception).
        """
        if self.role == UserRole.SUPERUSER:
            return True
        if self.role == UserRole.ADMIN and target_user.role != UserRole.SUPERUSER:
            return True
        if self.role == UserRole.EDITOR and target_user.role == UserRole.CONTRIBUTOR:
            return self.contributor_level > target_user.contributor_level
        if self.role == UserRole.CONTRIBUTOR and target_user.role == UserRole.CONTRIBUTOR:
            return self.contributor_level > target_user.contributor_level
        return False

    def can_approve_own(self, upload_owner):
        """No one can approve their own uploads."""
        return self != upload_owner

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class SpeakerProfile(models.Model):
    """
    Physical speakers being documented. May or may not have a user account.
    """
    full_name = models.CharField(max_length=255)
    clan_name = models.CharField(max_length=255, blank=True)
    village = models.ForeignKey(
        Community,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='speakers'
    )
    birth_year = models.PositiveSmallIntegerField(null=True, blank=True)
    is_living = models.BooleanField(default=True)
    user_account = models.OneToOneField(
        AkitaUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='speaker_profile'
    )
    documented_by = models.ForeignKey(
        AkitaUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='documented_speakers'
    )

    class Meta:
        ordering = ['full_name']

    def __str__(self):
        return self.full_name

