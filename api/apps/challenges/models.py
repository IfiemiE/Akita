from django.db import models

# Create your models here.
# challenges/models.py

from django.db import models
from django.utils import timezone

from users.models import AkitaUser
from lexicon.models import MediaFile, Dialect
from core.models import Category


class Challenge(models.Model):
    """
    Main model for language learning challenges.
    Flexible enough to handle word hunting, translations, speech recording, etc.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('ended', 'Ended'),
        ('archived', 'Archived'),
    ]

    TYPE_CHOICES = [
        ('word_hunt', 'Word Hunt (Rare word / Dialectal variant)'),
        ('translation', 'Translate English to Local Dialect'),
        ('reverse_translation', 'Find Translation from Other Dialects'),
        ('speech_translation', 'Translate Speech / Text (e.g. Lord's Prayer)'),
        ('reading_challenge', 'Reading & Pronunciation Challenge'),
        ('creative', 'Creative Use / Storytelling'),
        ('other', 'Other'),
    ]

    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    challenge_type = models.CharField(max_length=50, choices=TYPE_CHOICES)

    description = models.TextField()
    instructions = models.TextField()

    # Duration
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    # Media for the challenge itself
    image = models.ForeignKey(
        MediaFile, on_delete=models.SET_NULL, null=True, blank=True, 
        limit_choices_to={'media_type': 'image'}, related_name='challenge_images'
    )
    audio = models.ForeignKey(
        MediaFile, on_delete=models.SET_NULL, null=True, blank=True, 
        limit_choices_to={'media_type': 'audio'}, related_name='challenge_audio'
    )
    video = models.ForeignKey(
        MediaFile, on_delete=models.SET_NULL, null=True, blank=True, 
        limit_choices_to={'media_type': 'video'}, related_name='challenge_video'
    )

    # Categorization & Targeting
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True
    )
    target_dialect = models.ForeignKey(
        Dialect, on_delete=models.SET_NULL, null=True, blank=True
    )

    # Reward / Motivation
    points_reward = models.PositiveIntegerField(default=50)
    is_featured = models.BooleanField(default=False)
    max_attempts = models.PositiveSmallIntegerField(
        default=1, 
        help_text="Maximum submissions allowed per user (1 = one submission only)"
    )

    created_by = models.ForeignKey(
        AkitaUser, on_delete=models.SET_NULL, null=True, related_name='created_challenges'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['status', 'start_date']),
            models.Index(fields=['challenge_type', 'status']),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_challenge_type_display()})"

    @property
    def is_active(self):
        return self.status == 'active' and self.start_date <= timezone.now() <= self.end_date


class ChallengeSubmission(models.Model):
    """
    Solutions submitted by users (contributors).
    """
    challenge = models.ForeignKey(
        Challenge, on_delete=models.CASCADE, related_name='submissions'
    )
    user = models.ForeignKey(
        AkitaUser, on_delete=models.CASCADE, related_name='challenge_submissions'
    )

    attempt_number = models.PositiveSmallIntegerField(default=1)

    content = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    # Multimedia support
    audio = models.ManyToManyField(
        MediaFile, blank=True, related_name='submission_audio'
    )
    video = models.ManyToManyField(
        MediaFile, blank=True, related_name='submission_video'
    )
    images = models.ManyToManyField(
        MediaFile, blank=True, related_name='submission_images'
    )

    # For reverse translation challenges
    source_dialect = models.ForeignKey(
        Dialect, on_delete=models.SET_NULL, null=True, blank=True
    )
    borrowed_word = models.CharField(max_length=200, blank=True)

    submitted_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        AkitaUser, on_delete=models.SET_NULL, null=True, blank=True, 
        related_name='approved_submissions'
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-submitted_at']
        unique_together = ('challenge', 'user', 'attempt_number')
        indexes = [
            models.Index(fields=['challenge', 'user']),
            models.Index(fields=['is_approved', 'submitted_at']),
        ]

    def __str__(self):
        return f"Submission #{self.attempt_number} by {self.user.username} for {self.challenge.title}"


class SelectedSolution(models.Model):
    """
    Winning / Best solutions chosen by administrators.
    These are displayed publicly for a limited time.
    """
    challenge = models.ForeignKey(
        Challenge, on_delete=models.CASCADE, related_name='selected_solutions'
    )
    submission = models.ForeignKey(ChallengeSubmission, on_delete=models.CASCADE)

    rank = models.PositiveSmallIntegerField(default=1)
    reason = models.TextField(blank=True)
    displayed_until = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['rank', '-created_at']
        unique_together = ('challenge', 'submission')

    def __str__(self):
        return f"#{self.rank} - {self.submission.user.username}"


class ChallengeParticipation(models.Model):
    """Track users who joined a challenge (optional engagement tracking)."""
    challenge = models.ForeignKey(
        Challenge, on_delete=models.CASCADE, related_name='participants'
    )
    user = models.ForeignKey(
        AkitaUser, on_delete=models.CASCADE, related_name='challenge_participations'
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    is_notified = models.BooleanField(default=False, help_text="Reminder notification sent")

    class Meta:
        unique_together = ('challenge', 'user')
        ordering = ['-joined_at']

    def __str__(self):
        return f"{self.user.username} in {self.challenge.title}"