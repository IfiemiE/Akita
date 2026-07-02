from django.db import models
from django.core.exceptions import ValidationError
from apps.infrastructure.core.models import Community
from apps.identity.users.models import AkitaUser


class SpeakerProfile(models.Model):
    """
    Physical speakers being documented. May or may not have a user account.
    """
    full_name = models.CharField(max_length=255)
    community = models.ForeignKey(
        Community,
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
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(community__isnull=True) |
                    models.Q(community_note='')
                ),
                name='speaker_community_mutex',
            )
        ]
        

    def clean(self):
        if self.community_id and self.community_note:
            raise ValidationError(
                "A speaker may have either a community FK or a community_note, "
                "not both."
            )

    def __str__(self):
        return self.full_name
