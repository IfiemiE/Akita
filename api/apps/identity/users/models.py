from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinValueValidator, MaxValueValidator

class UserRole(models.TextChoices):
    CONTRIBUTOR = 'contributor', 'Contributor'
    EDITOR = 'editor', 'Editor/Moderator'
    ADMIN = 'admin', 'Admin'
    SUPERUSER = 'superuser', 'Superuser'


class AkitaUserManager(BaseUserManager):
    def create_user(self, username, email=None, password=None, role=None, **extra_fields):
        if not username:
            raise ValueError('The given username must be set')
        
        email = self.normalize_email(email) if email else None
        username = self.model.normalize_username(username)
        if role is None:
            role = UserRole.CONTRIBUTOR
        
        user = self.model(username=username, email=email, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(
            username, email, password,
            role=UserRole.SUPERUSER,
            **extra_fields
        )


class AkitaUser(AbstractUser):
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.CONTRIBUTOR,
        db_index=True
    )
    community = models.ForeignKey(
        'infrastructure_core.AkitaCommunity',
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
        help_text="Admin or Editor who physically identified/registered this contributor"
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
    email = models.EmailField(null=True, blank=True)
    objects = AkitaUserManager()
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

    def can_register_users(self):
        """Editors, Admins, and Superusers can register new users."""
        return self.role in [
            UserRole.SUPERUSER, UserRole.ADMIN, UserRole.EDITOR
        ]

    def can_elevate_user(self, target_user):
        """Only Admins and Superusers can elevate to Editor."""
        if not target_user:
            return False
        if self.role == UserRole.SUPERUSER:
            return True
        if target_user.get_role_level() == 0: # Anonymous user
            return False
        # non_superusers cannot elevate a user to their own level
        return self.get_role_level() > (target_user.get_role_level() + 1)

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
    community = models.ForeignKey(
        'infrastructure_core.Community',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='speakers',
        help_text="One of the five Akita clan communities, if the speaker is an original community member."
    )
    birth_year = models.PositiveSmallIntegerField(null=True, blank=True)
    is_living = models.BooleanField(default=True)
    community_note = models.CharField(
        max_length=255,
        blank=True,
        help_text="For speakers from outside the five Akita communities — specify their community of origin here (e.g. 'Peremabiri', 'Ekeremor')."
    )
    speaker_user_account = models.OneToOneField(
        AkitaUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='speaker_profile',
        help_text="For speakers who are also registered users"
    )
    documented_by = models.ForeignKey(
        AkitaUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='documented_speakers',
        help_text="The contributor: Interviewer/Narrator"
    )

    class Meta:
        ordering = ['full_name']

    def __str__(self):
        return self.full_name
