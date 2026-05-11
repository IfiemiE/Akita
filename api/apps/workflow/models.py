from django.db import models

# Create your models here.

# workflow/models.py

from django.db import models
from django.utils import timezone

from users.models import AkitaUser
from lexicon.models import Language, Dialect, Speaker, MediaFile


class PendingFile(models.Model):
    """
    A single raw file in the staging area, always linked to a contributor.

    Physically lives in pending/ and is never served on the frontend.
    When an admin promotes a file to the live library, they create a new
    MediaFile record (which writes to media/) using this file as the source.
    """
    contributor = models.ForeignKey(
        AkitaUser, on_delete=models.CASCADE,
        related_name='pending_files',
    )
    file = models.FileField(
        upload_to='pending/%Y/%m/%d/',
        help_text="Raw upload, stored in the private pending/ directory."
    )
    media_type = models.CharField(
        max_length=10, choices=MediaFile.TYPE_CHOICES
    )
    original_name = models.CharField(
        max_length=255, blank=True,
        help_text="The filename as submitted by the contributor."
    )
    description = models.CharField(
        max_length=255, blank=True,
        help_text="Contributor's description of this file."
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    # Set to the MediaFile created from this file when promoted by the admin.
    promoted_to = models.OneToOneField(
        MediaFile, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='promoted_from',
        help_text="The MediaFile record created when this pending file was approved."
    )

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return (
            f"{self.get_media_type_display()} — "
            f"{self.original_name or self.file.name} "
            f"({'promoted' if self.promoted_to_id else 'pending'})"
        )

    @property
    def is_promoted(self):
        return self.promoted_to_id is not None


class PendingSubmission(models.Model):
    """
    Staging area for ALL contributor-submitted content — text, files, or both.

    Workflow
    --------
    1. Contributor creates a submission (status='draft'), attaching text
       and/or raw files. Files are written to pending/ and never exposed publicly.
    2. Contributor finalises and submits (status='submitted'). Record becomes
       read-only on the contributor's side.
    3. Administrator reviews. They may edit text fields and file metadata
       directly on this record before deciding.
         - Approve  → admin manually creates MediaFile record(s) from approved
                       file(s), which writes them to media/, then links those
                       MediaFile records to appropriate live model(s).
         - Reject   → status set to 'rejected' with written feedback.
                       Contributor may revise and resubmit.
    4. A submission may be approved in parts: some files promoted, others
       discarded. The admin handles this per file via the review interface.
    """

    # --- Status ---
    STATUS_DRAFT     = 'draft'
    STATUS_SUBMITTED = 'submitted'
    STATUS_APPROVED  = 'approved'
    STATUS_REJECTED  = 'rejected'

    STATUS_CHOICES = [
        (STATUS_DRAFT,     'Draft'),
        (STATUS_SUBMITTED, 'Submitted'),
        (STATUS_APPROVED,  'Approved'),
        (STATUS_REJECTED,  'Rejected'),
    ]

    # --- Destination content type ---
    TYPE_LEXICAL         = 'lexical_entry'
    TYPE_SENSE           = 'sense'
    TYPE_EXAMPLE         = 'example'
    TYPE_PRONUNCIATION   = 'pronunciation'
    TYPE_CULTURAL        = 'cultural_item'
    TYPE_EXPRESSION      = 'fixed_expression'
    TYPE_PATTERN         = 'sentence_pattern'
    TYPE_COMMUNITY       = 'community_note'
    TYPE_MEDIA_ONLY      = 'media_only'
    TYPE_OTHER           = 'other'

    CONTENT_TYPE_CHOICES = [
        (TYPE_LEXICAL,       'Lexical Entry'),
        (TYPE_SENSE,         'Word Sense / Definition'),
        (TYPE_EXAMPLE,       'Example Sentence'),
        (TYPE_PRONUNCIATION, 'Pronunciation'),
        (TYPE_CULTURAL,      'Cultural Item'),
        (TYPE_EXPRESSION,    'Fixed Expression / Proverb'),
        (TYPE_PATTERN,       'Grammar / Sentence Pattern'),
        (TYPE_COMMUNITY,     'Community Note'),
        (TYPE_MEDIA_ONLY,    'Media File Only'),
        (TYPE_OTHER,         'Other'),
    ]

    # --- Core ---
    contributor = models.ForeignKey(
        AkitaUser, on_delete=models.CASCADE,
        related_name='pending_submissions',
        limit_choices_to={'role': AkitaUser.CONTRIBUTOR},
    )
    content_type = models.CharField(
        max_length=30, choices=CONTENT_TYPE_CHOICES,
        help_text="Which live model is this submission destined for?"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT
    )
    priority = models.PositiveSmallIntegerField(
        default=0, 
        help_text="Higher number = higher priority in admin queue"
    )

    # --- Text payload ---
    title = models.CharField(
        max_length=255, blank=True,
        help_text="Headword, expression title, cultural item name, etc."
    )
    body = models.TextField(
        blank=True,
        help_text=(
            "Main text content: definition, full expression, example "
            "sentence, cultural description, community note, etc."
        )
    )
    translation = models.TextField(
        blank=True,
        help_text="English or gloss-language translation."
    )
    interlinear_gloss = models.TextField(
        blank=True,
        help_text="Morpheme-by-morpheme gloss, if provided."
    )
    notes = models.TextField(
        blank=True,
        help_text=(
            "Contributor's contextual notes, source information, or any "
            "additional context for the reviewer."
        )
    )

    # --- Classification hints ---
    language = models.ForeignKey(
        Language, on_delete=models.SET_NULL, null=True, blank=True
    )
    dialect = models.ForeignKey(
        Dialect, on_delete=models.SET_NULL, null=True, blank=True
    )
    speaker = models.ForeignKey(
        Speaker, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Speaker who produced the content, if known."
    )

    # --- Raw file attachments (pending/ directory only) ---
    audio_files = models.ManyToManyField(
        PendingFile,
        blank=True,
        related_name='used_in_audio',
        limit_choices_to={'media_type': MediaFile.AUDIO},
        help_text="Audio recordings attached to this submission."
    )
    video_files = models.ManyToManyField(
        PendingFile,
        blank=True,
        related_name='used_in_video',
        limit_choices_to={'media_type': MediaFile.VIDEO},
        help_text="Video files attached to this submission."
    )
    image_files = models.ManyToManyField(
        PendingFile,
        blank=True,
        related_name='used_in_image',
        limit_choices_to={'media_type': MediaFile.IMAGE},
        help_text="Images attached to this submission."
    )

    # --- Review ---
    assigned_to = models.ForeignKey(
        AkitaUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_submissions',
        help_text="Admin assigned to review this submission"
    )
    reviewed_by = models.ForeignKey(
        AkitaUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_submissions',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(
        blank=True,
        help_text="Admin feedback to the contributor on approval or rejection."
    )

    # --- Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Set when the contributor finalises and submits for review."
    )

    class Meta:
        ordering = ['-priority', '-submitted_at', '-created_at']
        verbose_name = "Pending Submission"
        verbose_name_plural = "Pending Submissions"
        indexes = [
            models.Index(fields=['status', 'content_type', 'priority']),
            models.Index(fields=['contributor', 'status']),
            models.Index(fields=['assigned_to', 'status']),
        ]

    def __str__(self):
        return (
            f"[{self.get_status_display()}] "
            f"{self.get_content_type_display()} "
            f"by {self.contributor.username} "
            f"— "{self.title or self.body[:60]}""
        )

    @property
    def is_editable(self):
        """True when the contributor is still permitted to make changes."""
        return self.status in (self.STATUS_DRAFT, self.STATUS_REJECTED)

    def submit(self):
        """Contributor finalises — locks the record for admin review."""
        self.status = self.STATUS_SUBMITTED
        self.submitted_at = timezone.now()
        self.save(update_fields=['status', 'submitted_at'])

    def approve(self, reviewed_by, notes=''):
        """Admin approves after promoting files and linking live content."""
        self.status = self.STATUS_APPROVED
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'review_notes'])

    def reject(self, reviewed_by, notes=''):
        """Admin returns to contributor with feedback; re-opens for editing."""
        self.status = self.STATUS_REJECTED
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'review_notes'])
