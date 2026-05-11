from django.db import models
from django.utils import timezone
# from core.models import MediaTag
# from users.models import akitaUser

# Create your models here.

# culture/models.py

from django.db import models

from users.models import AkitaUser
from lexicon.models import MediaFile
from core.models import Category, MediaTag


class CulturalDomain(models.Model):
    """Broad cultural categories: Food, Festival, Dance, Folktale, Ritual, Craft, etc."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(
        max_length=50, blank=True, 
        help_text="Font Awesome or similar icon class"
    )
    order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class CulturalItem(models.Model):
    """
    Main model for cultural content.
    Flexible base for most cultural entries.
    """
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    domain = models.ForeignKey(
        CulturalDomain, on_delete=models.CASCADE, related_name='items'
    )

    # Content
    description = models.TextField()
    cultural_significance = models.TextField(blank=True)
    historical_context = models.TextField(blank=True)

    # Multimedia
    images = models.ManyToManyField(
        MediaFile, related_name='culture_images', blank=True
    )
    videos = models.ManyToManyField(
        MediaFile, related_name='culture_videos', 
        limit_choices_to={'media_type': 'video'}, blank=True
    )
    audio = models.ManyToManyField(
        MediaFile, related_name='culture_audio', 
        limit_choices_to={'media_type': 'audio'}, blank=True
    )

    # Classification
    categories = models.ManyToManyField(Category, blank=True)
    tags = models.ManyToManyField(MediaTag, blank=True)

    # Metadata
    location = models.CharField(
        max_length=200, blank=True, 
        help_text="Village, region, etc."
    )
    season_or_period = models.CharField(max_length=100, blank=True)
    associated_communities = models.TextField(blank=True)

    # Community & Moderation
    contributed_by = models.ForeignKey(
        AkitaUser, on_delete=models.SET_NULL, null=True, 
        related_name='cultural_contributions'
    )
    is_published = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        AkitaUser, on_delete=models.SET_NULL, null=True, blank=True, 
        related_name='approved_cultural_items'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['domain', 'is_published']),
            models.Index(fields=['is_published', 'created_at']),
        ]

    def __str__(self):
        return f"{self.title} ({self.domain.name})"


class Folktale(CulturalItem):
    """Specific extension for stories."""
    moral_lesson = models.TextField(blank=True)
    characters = models.TextField(blank=True)
    full_text = models.TextField()
    storyteller = models.CharField(max_length=200, blank=True)
    recorded_date = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Folktale"
        verbose_name_plural = "Folktales"


class Recipe(CulturalItem):
    """For traditional foods."""
    ingredients = models.TextField()
    preparation_steps = models.TextField()
    preparation_time = models.CharField(max_length=50, blank=True)
    serving_size = models.CharField(max_length=50, blank=True)
    dietary_notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Recipe"
        verbose_name_plural = "Recipes"


class Dance(CulturalItem):
    """For traditional dances."""
    number_of_performers = models.CharField(max_length=50, blank=True)
    costume_description = models.TextField(blank=True)
    music_instruments = models.TextField(blank=True)
    steps_description = models.TextField(blank=True)
    occasion = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "Dance"
        verbose_name_plural = "Dances"