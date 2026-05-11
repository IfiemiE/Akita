from django.db import models

# Create your models here.

# constructions/models.py

from django.db import models

from lexicon.models import Dialect, MediaFile, Speaker, SemanticDomain
from core.models import Category


class ConstructionTopic(models.Model):
    """
    Major grammatical topic or construction (e.g., "Serial Verbs", 
    "Noun Class Agreement", "Focus Constructions")
    """
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    difficulty_level = models.CharField(max_length=20, choices=[
        ('beginner', 'Beginner'), 
        ('intermediate', 'Intermediate'), 
        ('advanced', 'Advanced')
    ])
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True
    )

    # Editorial
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title


class SentencePattern(models.Model):
    """
    Specific syntactic patterns discovered through elicitation.
    """
    construction_topic = models.ForeignKey(
        ConstructionTopic, on_delete=models.CASCADE, related_name='patterns'
    )

    name = models.CharField(max_length=150)
    structure = models.CharField(
        max_length=300, 
        help_text="Abstract structure: e.g., 'NEG + S + V + OBJ'"
    )
    explanation = models.TextField()

    # Elicitation metadata
    ELICITATION_CHOICES = [
        ('situational', 'Situational / Contextual'),
        ('stimulus', 'Picture/Video Stimulus'),
        ('translation', 'Controlled Translation'),
        ('narrative', 'Narrative Discourse'),
        ('paradigm', 'Paradigm Filling'),
        ('comparative', 'Dialectal Comparison'),
        ('other', 'Other'),
    ]
    elicitation_method = models.CharField(
        max_length=100, choices=ELICITATION_CHOICES
    )

    example_scenario = models.TextField(
        blank=True, 
        help_text="The scenario used to elicit this pattern"
    )

    dialect = models.ForeignKey(
        Dialect, on_delete=models.SET_NULL, null=True, blank=True
    )
    semantic_domain = models.ForeignKey(
        SemanticDomain, on_delete=models.SET_NULL, null=True, blank=True
    )

    audio_example = models.ForeignKey(
        MediaFile, on_delete=models.SET_NULL, null=True, blank=True, 
        limit_choices_to={'media_type': 'audio'}
    )

    is_core_pattern = models.BooleanField(
        default=False, 
        help_text="Fundamental rule of the language"
    )
    notes = models.TextField(blank=True)

    # Editorial
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['construction_topic', 'name']
        indexes = [
            models.Index(fields=['construction_topic', 'is_core_pattern']),
        ]

    def __str__(self):
        return f"{self.name} ({self.construction_topic.title})"


class PatternExample(models.Model):
    """
    Multiple real examples for each sentence pattern - very important 
    for learning & verification.
    """
    sentence_pattern = models.ForeignKey(
        SentencePattern, on_delete=models.CASCADE, related_name='examples'
    )

    text = models.TextField()
    translation = models.TextField()
    interlinear_gloss = models.TextField(blank=True)

    audio = models.ForeignKey(
        MediaFile, on_delete=models.SET_NULL, null=True, blank=True, 
        limit_choices_to={'media_type': 'audio'}
    )
    speaker = models.ForeignKey(
        Speaker, on_delete=models.SET_NULL, null=True, blank=True
    )
    dialect = models.ForeignKey(
        Dialect, on_delete=models.SET_NULL, null=True, blank=True
    )

    context = models.TextField(
        blank=True, 
        help_text="Situation in which this sentence is natural"
    )
    is_grammatical = models.BooleanField(default=True)

    order = models.PositiveSmallIntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Example for {self.sentence_pattern.name}"


class FixedExpression(models.Model):
    """
    Captures greetings, idioms, proverbs, fixed phrases, and culturally-bound 
    expressions that are said in a specific way and often carry non-literal meaning.
    """
    EXPRESSION_TYPE_CHOICES = [
        ('greeting', 'Greeting / Pleasantry'),
        ('farewell', 'Farewell'),
        ('idiom', 'Idiom'),
        ('proverb', 'Proverb / Saying'),
        ('cliche', 'Cultural Cliché'),
        ('politeness', 'Politeness Formula'),
        ('ritual', 'Ritual / Ceremonial Phrase'),
        ('other', 'Other Fixed Expression'),
    ]

    title = models.CharField(
        max_length=200, 
        help_text="Short descriptive title"
    )
    expression = models.TextField()

    literal_translation = models.TextField(blank=True)
    idiomatic_translation = models.TextField()
    explanation = models.TextField(
        blank=True, 
        help_text="When and how it is used"
    )

    # Cultural & Contextual Information
    cultural_note = models.TextField(
        blank=True, 
        help_text="Background story, folktale, or cultural significance"
    )
    typical_context = models.TextField(
        blank=True, 
        help_text="Situations where this expression is used"
    )

    expression_type = models.CharField(
        max_length=30, choices=EXPRESSION_TYPE_CHOICES
    )

    # Links to existing models
    dialect = models.ForeignKey(
        Dialect, on_delete=models.SET_NULL, null=True, blank=True
    )
    semantic_domain = models.ForeignKey(
        SemanticDomain, on_delete=models.SET_NULL, null=True, blank=True
    )

    # Multimedia support
    audio = models.ManyToManyField(
        MediaFile, blank=True, related_name='fixed_expression_audio'
    )
    video = models.ManyToManyField(
        MediaFile, blank=True, related_name='fixed_expression_video'
    )

    # Usage & Learning
    FREQUENCY_CHOICES = [
        ('very_common', 'Very Common'),
        ('common', 'Common'),
        ('situational', 'Situational'),
        ('rare', 'Rare'),
    ]
    frequency = models.CharField(
        max_length=50, blank=True, choices=FREQUENCY_CHOICES
    )

    is_teachable = models.BooleanField(
        default=True, 
        help_text="Should this be taught to learners?"
    )

    # Editorial
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['expression_type', 'title']
        indexes = [
            models.Index(fields=['expression_type', 'frequency']),
            models.Index(fields=['is_teachable', 'is_published']),
        ]

    def __str__(self):
        return f"{self.expression[:60]}... ({self.get_expression_type_display()})"


class ExpressionUsageExample(models.Model):
    """
    Different real-life contexts in which a fixed expression is used.
    """
    fixed_expression = models.ForeignKey(
        FixedExpression, on_delete=models.CASCADE, related_name='usage_examples'
    )

    situation = models.TextField()
    example_usage = models.TextField()
    translation = models.TextField()
    interlinear_gloss = models.TextField(blank=True)

    audio = models.ForeignKey(
        MediaFile, on_delete=models.SET_NULL, null=True, blank=True, 
        limit_choices_to={'media_type': 'audio'}
    )
    speaker = models.ForeignKey(
        Speaker, on_delete=models.SET_NULL, null=True, blank=True
    )

    order = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Usage: {self.situation[:60]}..."
