from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.


# users/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class AkitaUser(AbstractUser):
    """
    A custom User model with tiered permission system for the dictionary platform.

    Roles:
    - Contributor: Can submit content for review (requires approval)
    - Administrator: Can moderate content and users
    - Superuser: Full system access
    """
    CONTRIBUTOR = 'contributor'
    ADMINISTRATOR = 'administrator'
    SUPERUSER = 'superuser'

    ROLE_CHOICES = [
        (CONTRIBUTOR, 'Contributor'),
        (ADMINISTRATOR, 'Administrator'),
        (SUPERUSER, 'Superuser'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=CONTRIBUTOR)
    is_approved = models.BooleanField(default=False, verbose_name="Approved")
    full_name = models.CharField(max_length=150, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True, help_text="Short bio or reason for contributing")

    date_approved = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, 
        related_name='approved_users'
    )

    # Audit & security fields
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    login_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    def save(self, *args, **kwargs):
        # Auto-approve superusers
        if self.role == self.SUPERUSER and not self.is_approved:
            self.is_approved = True
            self.date_approved = timezone.now()
        super().save(*args, **kwargs)
