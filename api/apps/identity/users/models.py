from django.db import models
from django.contrib.auth.models import AbstractUser
#from apps.infrastructure.core.models import Community
from django.core.validators import MinValueValidator, MaxValueValidator

class UserRole(models.TextChoices):
    CONTRIBUTOR = 'contributor', 'Contributor'
    EDITOR = 'editor', 'Editor/Moderator'
    ADMIN = 'admin', 'Admin'
    SUPERUSER = 'superuser', 'Superuser'


class AkitaUser(AbstractUser):
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.CONTRIBUTOR,
        db_index=True
    )
    community = models.ForeignKey(
        'infrastructure_core.Community',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members'
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
        help_text="This user is also a speaker"
    )
    is_active = models.BooleanField(default=True)

    # Elevation tracking (Contributor → Editor only)
    elevated_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='elevated_users'
    )
    elevated_at = models.DateTimeField(null=True, blank=True)
    elevation_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-date_joined']

    @property
    def full_name(self):
        return super().get_full_name()
    
    def get_role_level(self):
        """Return numeric privilege level for comparison."""
        levels = {
            UserRole.CONTRIBUTOR: 1,
            UserRole.EDITOR: 2,
            UserRole.ADMIN: 3,
            UserRole.SUPERUSER: 4,
        }
        return levels.get(self.role, 0)

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
        Higher roles can deactivate lower roles.
        Same role or lower role cannot deactivate higher.
        """
        if not target_user:
            return False
        return self.get_role_level() > target_user.get_role_level()

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
        'infrastructure_core.Community',
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

