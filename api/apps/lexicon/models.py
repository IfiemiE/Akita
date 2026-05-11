from django.db import models

# Create your models here.

# lexicon/models.py

from django.db import models
from django.db.models import Q, CheckConstraint
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from users.models import AkitaUser


# =============================================================================
# 1. FOUNDATION MODELS
# =============================================================================

class Language(models.Model):
    """
    Represents a language in the system.
    Distinguishes the target low-resource language from gloss/translation languages.
    """
    name = models.CharField(max_length=100)
    iso_code = models.CharField(max_length=10, blank=True, help_text="ISO 639-3 code")
    glottocode = models.CharField(max_length=20, blank=True, help_text="Glottolog code")
    is_target = models.BooleanField(
        default=False, 
        help_text="True if this is the primary language being documented"
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Dialect(models.Model):
    """
    Captures dialectal variation within the target language.
    Enables dialect-specific entries, pronunciations, and examples.
    """
    language = models.ForeignKey(
        Language, on_delete=models.CASCADE, related_name='dialects'
    )
    name = models.CharField(max_length=100)
    region = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('language', 'name')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.language.name})"


class Speaker(models.Model):
    """
    Individual speakers of the target language.
    Tracks provenance, sociolinguistic metadata, and reliability.
    """
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=20, blank=True)
    dialect = models.ForeignKey(
        Dialect, on_delete=models.SET_NULL, null=True, blank=True
    )
    birthplace = models.CharField(max_length=200, blank=True)
    education = models.CharField(max_length=200, blank=True)
    occupation = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name or 'Unnamed'}"


class MediaFile(models.Model):
    """
    Central multimedia storage for audio, video, and images.
    Supports rich documentation of oral languages.
    """
    AUDIO = 'audio'
    VIDEO = 'video'
    IMAGE = 'image'
    TYPE_CHOICES = [(AUDIO, 'Audio'), (VIDEO, 'Video'), (IMAGE, 'Image')]

    file = models.FileField(upload_to='media/%Y/%m/%d/')
    media_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    description = models.CharField(max_length=255, blank=True)

    # Technical metadata
    duration = models.DurationField(null=True, blank=True, help_text="For audio/video")
    file_size = models.PositiveIntegerField(null=True, blank=True, help_text="In bytes")
    checksum = models.CharField(max_length=64, blank=True, help_text="SHA-256 hash")

    # Provenance
    uploaded_by = models.ForeignKey(
        AkitaUser, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='uploaded_media'
    )
    speaker = models.ForeignKey(
        Speaker, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='media_recordings'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.media_type} - {self.file.name}"


# =============================================================================
# 2. ORTHOGRAPHY SYSTEMS
# =============================================================================

class OrthographicSystem(models.Model):
    """
    Represents a distinct orthographic/writing system for the target language.
    Supports multiple orthographies (e.g., missionary, revised, phonemic, phonetic).
    """
    name = models.CharField(max_length=100, help_text="e.g., 'Standard Orthography', 'Phonemic', 'Missionary'")
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    language = models.ForeignKey(
        Language, on_delete=models.CASCADE, related_name='orthographic_systems',
        limit_choices_to={'is_target': True}
    )

    is_primary = models.BooleanField(
        default=False, 
        help_text="The default orthography used for headwords and search"
    )
    is_active = models.BooleanField(default=True)

    # Metadata
    developed_by = models.CharField(max_length=255, blank=True)
    year_developed = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_primary', 'name']
        verbose_name = "Orthographic System"
        verbose_name_plural = "Orthographic Systems"

    def __str__(self):
        return f"{self.name} ({self.language.name})"

    def save(self, *args, **kwargs):
        # Ensure only one primary orthography per language
        if self.is_primary:
            OrthographicSystem.objects.filter(
                language=self.language, is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class Grapheme(models.Model):
    """
    Individual characters/symbols in an orthographic system.
    Includes IPA reference and audio demonstration.
    """
    orthographic_system = models.ForeignKey(
        OrthographicSystem, on_delete=models.CASCADE, related_name='graphemes'
    )
    symbol = models.CharField(
        max_length=20, 
        help_text="The written character (may be digraph or with diacritics)"
    )
    description = models.TextField(blank=True)

    # IPA reference
    ipa_character = models.CharField(
        max_length=50, 
        blank=True,
        help_text="Closest IPA equivalent or phonetic description"
    )

    # Audio demonstration
    audio = models.ForeignKey(
        MediaFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'media_type': 'audio'},
        related_name='grapheme_audio',
        help_text="Audio demonstrating the sound of this grapheme"
    )

    collation_order = models.PositiveIntegerField()

    # Featured example words for literacy materials
    featured_examples = models.ManyToManyField(
        'LexicalEntry',
        through='GraphemeFeaturedExample',
        related_name='featured_in_graphemes',
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('orthographic_system', 'symbol')
        ordering = ['collation_order']

    def __str__(self):
        return f"{self.symbol} ({self.orthographic_system.name})"


class GraphemeFeaturedExample(models.Model):
    """Links graphemes to example words with position notes for literacy materials."""
    grapheme = models.ForeignKey(Grapheme, on_delete=models.CASCADE)
    entry = models.ForeignKey('LexicalEntry', on_delete=models.CASCADE)
    order = models.PositiveSmallIntegerField(default=0)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ('grapheme', 'entry')
        ordering = ['order']

    def __str__(self):
        return f"{self.grapheme.symbol} in {self.entry.lemma}"


class OrthographyMapping(models.Model):
    """
    Maps equivalent forms across orthographic systems.
    e.g., 'ny' in System A = 'ɲ' in System B
    """
    from_system = models.ForeignKey(
        OrthographicSystem, on_delete=models.CASCADE, related_name='mappings_from'
    )
    to_system = models.ForeignKey(
        OrthographicSystem, on_delete=models.CASCADE, related_name='mappings_to'
    )
    from_grapheme = models.CharField(max_length=20)
    to_grapheme = models.CharField(max_length=20)
    context = models.CharField(
        max_length=255, blank=True,
        help_text="Phonological or positional context for this mapping"
    )
    is_regular = models.BooleanField(
        default=True, 
        help_text="False for exceptions/irregular mappings"
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_system', 'to_system', 'from_grapheme')
        ordering = ['from_system', 'from_grapheme']
        verbose_name = "Orthography Mapping"
        verbose_name_plural = "Orthography Mappings"

    def __str__(self):
        return f"{self.from_grapheme} ({self.from_system.name}) → {self.to_grapheme} ({self.to_system.name})"


# =============================================================================
# 3. MORPHOLOGICAL & SEMANTIC FOUNDATION
# =============================================================================

class Root(models.Model):
    """
    Morphological roots for languages with productive morphology.
    Enables derivation tracking and etymological understanding.
    """
    root_form = models.CharField(max_length=50, unique=True)
    meaning = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['root_form']

    def __str__(self):
        return self.root_form


class SemanticDomain(models.Model):
    """
    Hierarchical semantic domains (thesaurus-style classification).
    Example: 1.5 → Living Things → 1.5.2 → Plants
    """
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150)
    parent = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, 
        related_name='subdomains'
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"


class PartOfSpeech(models.Model):
    """Part of speech categories (Noun, Verb, Ideophone, etc.)."""
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class GrammaticalCategory(models.Model):
    """
    Language-specific grammatical categories (Noun Class, Valency, Tone Pattern, etc.).
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


# =============================================================================
# 4. CORE LEXICAL ENTRY
# =============================================================================

class LexicalEntry(models.Model):
    """
    The central model representing a dictionary headword/entry.
    Combines orthography, morphology, grammar, pronunciation, and multimedia.
    """
    lemma = models.CharField(max_length=200, db_index=True)
    language = models.ForeignKey(
        Language, on_delete=models.CASCADE, 
        limit_choices_to={'is_target': True}
    )
    dialect = models.ForeignKey(
        Dialect, on_delete=models.SET_NULL, null=True, blank=True
    )
    part_of_speech = models.ForeignKey(
        PartOfSpeech, on_delete=models.SET_NULL, null=True, blank=True
    )

    # Morphology
    root = models.ForeignKey(
        Root, on_delete=models.SET_NULL, null=True, blank=True, 
        related_name='derived_entries'
    )

    # Orthographic representation
    orthographic_system = models.ForeignKey(
        OrthographicSystem, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='entries',
        help_text="The orthography this lemma is written in"
    )

    # Isolation audio (word said in isolation)
    isolated_audio = models.ManyToManyField(
        MediaFile, 
        related_name='isolated_in', 
        limit_choices_to={'media_type': 'audio'}, 
        blank=True
    )

    # Frequency and usage
    frequency_note = models.CharField(max_length=50, blank=True)
    register = models.CharField(max_length=50, blank=True)

    # Editorial
    notes = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)

    # Homonym handling
    homonym_number = models.PositiveSmallIntegerField(
        default=0, 
        help_text="0 if not a homonym; 1, 2, 3... for homonyms with same POS"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('lemma', 'language', 'dialect', 'part_of_speech', 'homonym_number')
        verbose_name_plural = "Lexical Entries"
        ordering = ['lemma', 'homonym_number']
        indexes = [
            models.Index(fields=['lemma', 'language']),
            models.Index(fields=['is_published', 'language']),
        ]

    def __str__(self):
        return f"{self.lemma} ({self.language.name})"


class VariantForm(models.Model):
    """Alternative spellings, pronunciations, or dialectal variants."""
    entry = models.ForeignKey(
        LexicalEntry, on_delete=models.CASCADE, related_name='variants'
    )
    form = models.CharField(max_length=200)
    dialect = models.ForeignKey(
        Dialect, on_delete=models.SET_NULL, null=True, blank=True
    )
    orthographic_system = models.ForeignKey(
        OrthographicSystem, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="If this variant uses a different orthography"
    )
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('entry', 'form')
        ordering = ['form']

    def __str__(self):
        return f"{self.form} (variant of {self.entry.lemma})"


class Pronunciation(models.Model):
    """
    Rich pronunciation data including IPA, speaker variation, and audio.
    Critical for tonal and phonologically complex languages.
    """
    entry = models.ForeignKey(
        LexicalEntry, on_delete=models.CASCADE, related_name='pronunciations'
    )
    ipa = models.CharField(max_length=500, help_text="IPA transcription")
    dialect = models.ForeignKey(
        Dialect, on_delete=models.SET_NULL, null=True, blank=True
    )
    speaker = models.ForeignKey(
        Speaker, on_delete=models.SET_NULL, null=True, blank=True
    )
    note = models.CharField(max_length=255, blank=True)
    audio = models.ManyToManyField(
        MediaFile, limit_choices_to={'media_type': 'audio'}, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['entry', 'dialect', 'speaker']

    def __str__(self):
        return f"/{self.ipa}/ ({self.entry.lemma})"


class GrammaticalFeature(models.Model):
    """Language-specific grammatical features (e.g., Noun Class 3/4, Causative)."""
    entry = models.ForeignKey(
        LexicalEntry, on_delete=models.CASCADE, related_name='grammatical_features'
    )
    category = models.ForeignKey(GrammaticalCategory, on_delete=models.CASCADE)
    value = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('entry', 'category')
        ordering = ['category', 'value']

    def __str__(self):
        return f"{self.category.name}: {self.value} ({self.entry.lemma})"


class Inflection(models.Model):
    """Inflected forms (paradigms) such as plural, past tense, etc."""
    entry = models.ForeignKey(
        LexicalEntry, on_delete=models.CASCADE, related_name='inflections'
    )
    label = models.CharField(max_length=100, help_text="e.g., 'plural', 'past tense'")
    form = models.CharField(max_length=200)
    dialect = models.ForeignKey(
        Dialect, on_delete=models.SET_NULL, null=True, blank=True
    )
    audio = models.ManyToManyField(
        MediaFile, limit_choices_to={'media_type': 'audio'}, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['label', 'form']

    def __str__(self):
        return f"{self.label}: {self.form} ({self.entry.lemma})"


# =============================================================================
# 5. SENSES & USAGE
# =============================================================================

class Sense(models.Model):
    """
    Individual senses/meanings of a polysemous word.
    Captures definitions, translations, cultural notes, semantic domains, 
    ideophones, and revitalization metadata.
    """
    entry = models.ForeignKey(
        LexicalEntry, on_delete=models.CASCADE, related_name='senses'
    )
    order = models.PositiveIntegerField(default=1)

    # Core content
    definition = models.TextField()
    translation = models.TextField(blank=True, help_text="English or gloss-language translation")

    # Gloss language (supports multiple gloss languages)
    gloss_language = models.ForeignKey(
        Language, on_delete=models.CASCADE, related_name='glosses',
        limit_choices_to={'is_target': False},
        help_text="Language of the translation/definition"
    )

    # Classification
    domains = models.ManyToManyField(SemanticDomain, blank=True)

    # Special types
    is_ideophone = models.BooleanField(default=False)
    reduplication_pattern = models.CharField(max_length=100, blank=True)

    # Usage metadata
    register = models.CharField(max_length=50, blank=True)
    usage_labels = models.CharField(max_length=100, blank=True)

    # Cultural content
    cultural_note = models.TextField(blank=True)

    # Etymology (sense-specific when different from entry-wide)
    etymology_note = models.TextField(blank=True)

    # Editorial
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['entry', 'order']
        unique_together = ('entry', 'order')
        indexes = [
            models.Index(fields=['entry', 'order']),
            models.Index(fields=['is_ideophone', 'is_published']),
        ]

    def __str__(self):
        return f"Sense {self.order} of {self.entry.lemma}"


class Example(models.Model):
    """
    Naturalistic example sentences with translations and multimedia.
    Gold standard for endangered language documentation.
    """
    # Polymorphic parent: either attached to a Sense or directly to LexicalEntry
    sense = models.ForeignKey(
        Sense, on_delete=models.CASCADE, related_name='examples', 
        null=True, blank=True
    )
    entry = models.ForeignKey(
        LexicalEntry, on_delete=models.CASCADE, related_name='direct_examples', 
        null=True, blank=True
    )

    text = models.TextField()
    translation = models.TextField()
    interlinear_gloss = models.TextField(blank=True)

    # Multimedia
    audio = models.ManyToManyField(
        MediaFile, limit_choices_to={'media_type': 'audio'}, blank=True
    )
    video = models.ManyToManyField(
        MediaFile, limit_choices_to={'media_type': 'video'}, blank=True
    )

    # Provenance
    speaker = models.ForeignKey(
        Speaker, on_delete=models.SET_NULL, null=True, blank=True
    )
    dialect = models.ForeignKey(
        Dialect, on_delete=models.SET_NULL, null=True, blank=True
    )

    # Context
    context = models.TextField(blank=True, help_text="Situation where this sentence is natural")
    is_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            CheckConstraint(
                check=Q(sense__isnull=False, entry__isnull=True) | 
                      Q(sense__isnull=True, entry__isnull=False),
                name='example_has_one_parent'
            ),
        ]

    def __str__(self):
        return f"Example: {self.text[:60]}..."


class Collocation(models.Model):
    """Common word combinations and phrases."""
    sense = models.ForeignKey(
        Sense, on_delete=models.CASCADE, related_name='collocations', 
        null=True, blank=True
    )
    entry = models.ForeignKey(
        LexicalEntry, on_delete=models.CASCADE, related_name='collocations', 
        null=True, blank=True
    )
    expression = models.CharField(max_length=300)
    translation = models.TextField(blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['expression']
        constraints = [
            CheckConstraint(
                check=Q(sense__isnull=False, entry__isnull=True) | 
                      Q(sense__isnull=True, entry__isnull=False),
                name='collocation_has_one_parent'
            ),
        ]

    def __str__(self):
        return self.expression


# =============================================================================
# 6. RELATIONS & SUPPLEMENTARY
# =============================================================================

class SemanticRelation(models.Model):
    """
    Semantic and phonological relationships between entries.
    Includes synonyms, antonyms, hyponyms, and minimal pairs.
    Based on WordNet-style relation taxonomy.
    """
    # Relation type choices
    SYNONYM = 'synonym'
    ANTONYM = 'antonym'
    HYPONYM = 'hyponym'
    HYPERNYM = 'hypernym'
    MERONYM = 'meronym'
    HOLONYM = 'holonym'
    TROPONYM = 'troponym'
    ENTAILMENT = 'entailment'
    MINIMAL_PAIR = 'minimal_pair'
    HOMOPHONE = 'homophone'
    HOMONYM = 'homonym'
    DERIVED_FORM = 'derived_form'
    COMPOUND = 'compound'
    SEE_ALSO = 'see_also'

    RELATION_CHOICES = [
        (SYNONYM, 'Synonym'),
        (ANTONYM, 'Antonym'),
        (HYPONYM, 'Hyponym (is a kind of)'),
        (HYPERNYM, 'Hypernym (is a superordinate of)'),
        (MERONYM, 'Meronym (is part of)'),
        (HOLONYM, 'Holonym (has as part)'),
        (TROPONYM, 'Troponym (manner of)'),
        (ENTAILMENT, 'Entailment'),
        (MINIMAL_PAIR, 'Minimal Pair'),
        (HOMOPHONE, 'Homophone'),
        (HOMONYM, 'Homonym'),
        (DERIVED_FORM, 'Derived Form'),
        (COMPOUND, 'Compound'),
        (SEE_ALSO, 'See Also'),
    ]

    # Source (can be sense-specific or entry-wide)
    from_sense = models.ForeignKey(
        Sense, on_delete=models.CASCADE, related_name='outgoing_relations', 
        null=True, blank=True
    )
    from_entry = models.ForeignKey(
        LexicalEntry, on_delete=models.CASCADE, related_name='outgoing_entry_relations'
    )

    # Target
    to_entry = models.ForeignKey(
        LexicalEntry, on_delete=models.CASCADE, related_name='incoming_relations'
    )
    to_sense = models.ForeignKey(
        Sense, on_delete=models.CASCADE, related_name='incoming_sense_relations',
        null=True, blank=True
    )

    relation_type = models.CharField(max_length=20, choices=RELATION_CHOICES)

    # Bidirectional flag (e.g., synonym is mutual, hyponym is not)
    is_bidirectional = models.BooleanField(default=False)

    # Metadata
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_entry', 'to_entry', 'relation_type', 'from_sense', 'to_sense')
        ordering = ['relation_type']
        indexes = [
            models.Index(fields=['from_entry', 'relation_type']),
            models.Index(fields=['to_entry', 'relation_type']),
        ]

    def __str__(self):
        return f"{self.from_entry.lemma} --{self.get_relation_type_display()}--> {self.to_entry.lemma}"


class Illustration(models.Model):
    """Visual illustrations linked to entries or senses."""
    sense = models.ForeignKey(
        Sense, on_delete=models.CASCADE, related_name='illustrations', 
        null=True, blank=True
    )
    entry = models.ForeignKey(
        LexicalEntry, on_delete=models.CASCADE, related_name='illustrations', 
        null=True, blank=True
    )
    image = models.ForeignKey(
        MediaFile, on_delete=models.CASCADE, 
        limit_choices_to={'media_type': 'image'}
    )
    caption = models.CharField(max_length=255, blank=True)
    order = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']
        constraints = [
            CheckConstraint(
                check=Q(sense__isnull=False, entry__isnull=True) | 
                      Q(sense__isnull=True, entry__isnull=False),
                name='illustration_has_one_parent'
            ),
        ]

    def __str__(self):
        return f"Illustration for {self.entry.lemma if self.entry else self.sense.entry.lemma}"


class Etymology(models.Model):
    """Etymological and historical information about a lexical entry."""
    entry = models.OneToOneField(
        LexicalEntry, on_delete=models.CASCADE, related_name='etymology'
    )
    origin_text = models.TextField()
    proto_form = models.CharField(max_length=200, blank=True)
    source_entry = models.ForeignKey(
        LexicalEntry, on_delete=models.SET_NULL, null=True, blank=True, 
        related_name='etymology_source'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Etymologies"

    def __str__(self):
        return f"Etymology of {self.entry.lemma}"


class Source(models.Model):
    """Provenance and citation information for entries and examples."""
    entry = models.ForeignKey(
        LexicalEntry, on_delete=models.CASCADE, related_name='sources', 
        null=True, blank=True
    )
    example = models.ForeignKey(
        Example, on_delete=models.CASCADE, related_name='sources', 
        null=True, blank=True
    )

    # Citation details
    speaker = models.ForeignKey(
        Speaker, on_delete=models.SET_NULL, null=True, blank=True
    )
    recording_date = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=200, blank=True)

    # Bibliographic
    bibliographic_ref = models.CharField(max_length=500, blank=True)
    page_number = models.CharField(max_length=50, blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recording_date']
        constraints = [
            CheckConstraint(
                check=Q(entry__isnull=False, example__isnull=True) | 
                      Q(entry__isnull=True, example__isnull=False),
                name='source_has_one_parent'
            ),
        ]

    def __str__(self):
        return f"Source for {self.entry.lemma if self.entry else 'example'}"


class CommunityNote(models.Model):
    """
    Community-contributed notes on word senses.
    Supports participatory dictionary making and language revitalization.
    """
    sense = models.ForeignKey(
        Sense, on_delete=models.CASCADE, related_name='community_notes'
    )
    user = models.ForeignKey(
        AkitaUser, on_delete=models.CASCADE, related_name='community_notes'
    )

    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Moderation
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        AkitaUser, on_delete=models.SET_NULL, null=True, blank=True, 
        related_name='verified_community_notes'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    is_hidden = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Note by {self.user.username} on {self.sense.entry.lemma}"


class VisitorSuggestion(models.Model):
    """
    Public feedback and suggestions from any site visitor (including anonymous users).
    Limited to 5 per day per IP. Supports "Noted" workflow.
    """
    name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    user = models.ForeignKey(
        AkitaUser, on_delete=models.SET_NULL, null=True, blank=True, 
        related_name='visitor_suggestions'
    )

    subject = models.CharField(max_length=200)
    content = models.TextField()

    # Workflow
    is_noted = models.BooleanField(default=False, verbose_name="Noted")
    noted_by = models.ForeignKey(
        AkitaUser, on_delete=models.SET_NULL, null=True, blank=True, 
        related_name='noted_suggestions'
    )
    noted_at = models.DateTimeField(null=True, blank=True)

    # Rate limiting
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Soft delete
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ip_address', 'created_at']),
            models.Index(fields=['is_noted', 'created_at']),
        ]

    def __str__(self):
        return f"Suggestion: {self.subject[:50]}"

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])