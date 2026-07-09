from django.db import models
from django.core.exceptions import ValidationError
from model_utils import FieldTracker
from apps.identity.users.models import AkitaUser
from apps.infrastructure.core.models import Language, Dialect
from apps.documentation.orthography.models import Alphabet
from apps.common.storage import set_user_uploaded_file_path


# ============================================================
#   MEDIA
# ============================================================

class MediaFile(models.Model):
    """
    Reusable multimedia files (audio, video, images) across the dictionary.
    Base media store referenced by lexicon, media_annotations, and culture apps.
    """
    AUDIO = 'audio'
    VIDEO = 'video'
    IMAGE = 'image'
    TYPE_CHOICES = [(AUDIO, 'Audio'), (VIDEO, 'Video'), (IMAGE, 'Image')]

    file = models.FileField(upload_to='media/%Y/%m/%d/')
    media_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    description = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        AkitaUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_media'
    )

    def __str__(self):
        return f"{self.media_type} - {self.file.name}"


# ============================================================
#   SPEAKER
# ============================================================

class Speaker(models.Model):
    """
    Speakers whose voices were recorded to produce lexicon entry sounds.
    """
    code = models.CharField(
        max_length=20, 
        unique=True, 
        help_text="Anonymous identifier, e.g., SPK01"
    )
    name = models.CharField(max_length=100, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=20, blank=True)
    dialect = models.ForeignKey(
        Dialect, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        AkitaUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorded_speakers',
        help_text="Contributor who made the recording"
    )

    def __str__(self):
        return self.code


# ============================================================
#   MORPHOLOGY & SEMANTIC FOUNDATIONS
# ============================================================

class Root(models.Model):
    """
    Core morphological root/radical from which multiple words are derived
    Represents the shared 'DNA' or abstract semantic nucleus of a word family.
    """
    root_form = models.CharField(max_length=50, unique=True)
    meaning = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank= True)
    
    def __str__(self):
        return self.root_form
    

class SemanticDomain(models.Model):
    """
    Hierarchical semantic classification following standard domain codes.
    e.g. '1.5.2 Plants', '2.3 Finance', '4.1 Relationships'.
    Parent FK enables nested domain trees of arbitrary depth.
    """
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, related_name='subdomains')
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    

class PartOfSpeech(models.Model):
    """
    Grammatical parts of speech (noun, verb, adjective, ideophone, etc)
    """
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name


class GrammaticalCategory(models.Model):
    """
    Categories for grammatical features (e.g. Countability, Valency , Noun class).
    """
    name = models.CharField(max_length=100, unique=True)
    
    class Meta:
        verbose_name_plural = 'Grammatical Categories'
    
    def __str__(self):
        return self.name
    
# ============================================================
#   REGISTER/PRAGMATICS & USAGE LABELS & SEMANTIC RELATIONS
# ============================================================

class Register(models.Model):
    """
    REGISTER_CHOICES = [
        ('formal', 'Formal'), 
        ('informal', 'Informal / Colloquial'),
        ('neutral', 'Neutral'),
        ('taboo', 'Taboo / Vulgar'),
        ('archaic', 'Archaic'),
        ('dialectal', 'Dialectal / Regional'),
        ('polite', 'Polite / Honorific'),
        ('slang', 'Slang'),
        ('technical', 'Technical / Specialized'),
        ('literal', 'Literal'),
        ('offensive', 'Offensive'),
        ('child', 'Child speech / Baby talk'),
        # Add more as the need arises
    ]
    """
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class UsageLabel(models.Model):
    """
    Frequency/currency labels: common, rare, obsolete, neologism, etc.
    Stored as rows so editors can extend the list without code changes.
    Examples from original inline choices now live as seeded rows:
        common, rare, very_rare, archaic, obsolete, dated, regional,
        dialectal, technical, neologism, borrowed, idiomatic, figurative,
        poetic, euphemism, restricted
    USAGE_LABEL_CHOICES = [
        ('common', 'Common / Everyday'),
        ('rare', 'Rare'),
        ('very_rare', 'Very Rare'),
        ('archaic', 'Archaic'),
        ('obsolete', 'Obsolete'),
        ('dated', 'Dated'),
        ('regional', 'Regional'),
        ('dialectal', 'Dialectal (Akita-specific)'),
        ('technical', 'Technical / Specialized'),
        ('neologism', 'Neologism'),
        ('borrowed', 'Borrowed'),
        ('idiomatic', 'Idiomatic'),
        ('figurative', 'Figurative / Metaphorical'),
        ('poetic', 'Poetic'),
        ('euphemism', 'Euphemism'),
        ('restricted', 'Contextually Restricted'),
        # Add more as the need arises
    ]
    """
    name = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=200, blank=True)
    
    def __str__(self):
        return self.name


class SemanticRelationTypes(models.Model):
    """
    RELATION_CHOICES = [
        ('synonym', 'Synonym'),
        ('antonym', 'Antonym'),
        ('hyponym', 'Hyponym'),
        ('hypernym', 'Hypernym'),
        
    ]
    """
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


# ============================================================
#   CORE LEXICAL MODELS
# ============================================================

class LexicalEntry(models.Model):
    """
    The main headword/lemma (citation form) of a dictionary entry.
 
    `lemma` is the human-entered canonical spelling — the source of truth
    for the word's written form. The grapheme_slots M2M relationship
    (via LexicalEntryGrapheme) is a structured decomposition of this lemma
    into its constituent Alphabet entries (grapheme-phoneme pairs).
 
    `position` encodes the entry's rank in the Akita alphabetical ordering
    as defined by Alphabet.order in the default OrthographicSystem. It is:
      - Computed entirely by services/collation.py — never set directly.
      - NULL for entries whose grapheme sequence is incomplete (no
        LexicalEntryGrapheme row with is_final=True yet). Draft entries.
      - Protected by a DEFERRED UniqueConstraint (PostgreSQL) so bulk
        position updates do not raise IntegrityError mid-transaction.
 
    `constituents` — self-referential M2M for compound words. Asymmetrical:
      entry.constituents → the parts that make up this compound
      entry.compounds    → compounds that contain this entry as a part
 
    `variant_form` — self-referential symmetrical M2M for spelling variants
    within the same orthographic system (not cross-system transliterations).
    """
    lemma = models.CharField(
        max_length=200, 
        db_index=True,
        help_text="The headword as it appears in the dictionary."
    )
    language = models.ForeignKey(
        Language, 
        on_delete=models.CASCADE,
        related_name='lexical_entries',
        limit_choices_to={'is_target': True},
        # language.lexical_entries.all() → all entries in this language
    )
    dialect = models.ForeignKey(
        Dialect, 
        on_delete=models.CASCADE,
        related_name='lexical_entries',
        limit_choices_to={'is_target': True},
        # dialect.lexical_entries.all() → all entries in this dialect
    )
    root = models.ForeignKey(
        Root, 
        on_delete=models.SET_NULL,
        related_name='derived_entries',
        null=True
        # root.derived_entries.all() → all words sharing this root
    )
    is_compound = models.BooleanField(default=False)
    constituents = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='compounds',
        blank=True,
        help_text="Component words that make up this compound entry.",
        # entry.constituents.all() → parts of this compound
        # entry.compounds.all()    → compounds containing this entry
    )
    variant_form = models.ManyToManyField(
        'self',
        symmetrical=True,
        blank=True, 
        help_text='other spellings for this same word in same orthographic system'
    )
    position = models.PositiveIntegerField(
        null=True, blank=True,
        editable=False,
        help_text=(
            "Alphabetical rank in the dictionary. Computed automatically "
            "by the collation service. NULL until the grapheme sequence is complete."
        ),
    )
    note = models.CharField(max_length=255, blank=True, null=True)
    
    # Tracks lemma changes so the collation signal repositions only on
    # actual headword edits, not on saves that touch other fields.
    tracker = FieldTracker(fields=['lemma'])
    
    class Meta:
        unique_together = ('lemma', 'language', 'dialect')
        verbose_name_plural = 'Lexical Entries'
        constraints = [
            models.UniqueConstraint(
                fields=['position'],
                name='lexical_entry_position_unique',
                deferrable=models.Deferrable.DEFERRED, # defer check until commit. note: a feature of postgresql
            )
        ]
    
    def clean(self):
        super().clean()
        if self.pk and self.variant_form.filter(pk=self.pk).exists():
            raise ValidationError('Cannot select same word as a variant of itself')
        if self.is_compound and not self.constituents.exists():
            raise ValidationError(
                "Compound words must specify their constituent entries."
            )
    
    def __str__(self):
        return self.lemma
    
    @property
    def is_complete(self) -> bool:
        """True if the grapheme sequence has been marked final and validated."""
        return self.grapheme_slots.filter(is_final=True).exists()
    
    @property
    def letter_length(self) -> int | None:
        """
        Number of grapheme slots if the sequence is complete, else None. 
        Use with prefetch_related.
        """
        if not self.grapheme_slots.filter(is_final=True).exists():
            return None
        return self.grapheme_slots.count()

    @property
    def letters(self):
        """
        Returns a QuerySet of Alphabet instances (grapheme-phoneme pairs: letters)
        constituting this headword, in slot order.
 
        Returns None if the grapheme sequence is not yet complete (no
        is_final=True slot), so callers can gate on this cleanly.
 
        The Alphabet model carries:
            .grapheme  → GraphemeRegister (the written symbol)
            .phoneme   → PhonemeRegister  (the IPA sound)
            .order     → collation rank in the orthographic system
 
        Used by the transliteration service to access phoneme_ids for
        slot-based, multigraph-safe mapping to other orthographic systems.
        """
        if not self.is_complete:
            return None
        return(
            Alphabet.objects
            .filter(entry_slots__entry=self)
            .select_related(
                'grapheme',   # GraphemeRegister — for .notation (the symbol)
                'phoneme',    # PhonemeRegister  — for .ipa and .pk (phoneme bridge)
                'orthographic_system',
            )
            .order_by('entry_slots__slot')
        )


class LexicalEntryGrapheme(models.Model):
    """
    Through/intermediary table linking a LexicalEntry to the Alphabet
    entries (grapheme-phoneme pairs) that constitute its headword.
 
    Each row records one grapheme occupying one `slot` (zero-indexed
    position) within a headword's decomposition.
 
    The FK to Alphabet (not raw GraphemeRegister) means each slot carries:
      - The grapheme symbol (.grapheme.notation)
      - Its associated phoneme (.phoneme.ipa, .phoneme_id)
      - Its collation rank in the orthographic system (.order)
      - The system it belongs to (.orthographic_system)
 
    This makes the slot sequence the foundation for:
      1. Concatenation validation (clean())
      2. Collation positioning (via collation service)
      3. Transliteration (phoneme bridge to any other system)
 
    is_final
    --------
    Marks the last grapheme slot. Setting is_final=True on a slot:
      - Triggers clean() which concatenates all slot grapheme notations
        and checks they match entry.lemma exactly.
      - On success, fires the post_save signal which calls
        collation.reassign_after_insert(), assigning entry.position.
      - On failure, raises ValidationError — entry stays as a draft
        (position remains NULL).
 
    Deleting the is_final slot returns the entry to draft state.
    """
    entry = models.ForeignKey(
        LexicalEntry,
        on_delete=models.CASCADE,
        related_name='grapheme_slots',
        # entry.grapheme_slots.order_by('slot') → slot sequence for this word
    )
    letter = models.ForeignKey(
        Alphabet,
        on_delete=models.CASCADE,
        related_name='entry_slots',
        # alphabet_entry.entry_slots.all() → all headwords using this grapheme-phoneme pair (letter)
    )
    slot = models.PositiveSmallIntegerField(
        help_text="Zero-indexed position of this grapheme within the headword.",
    )
    is_final = models.BooleanField(
        default=False,
        help_text=(
            "True on the last grapheme slot only. Triggers concatenation "
            "validation and, on success, collation positioning."
        ),
    )
 
    class Meta:
        unique_together = [('entry', 'slot')]
        ordering = ['entry', 'slot']
 
    def __str__(self):
        return (
            f"{self.entry.lemma}[{self.slot}]"
            f"={self.letter.grapheme.notation}"
            f" ({'final' if self.is_final else 'draft'})"
        )
 
    def clean(self):
        super().clean()
 
        # --- Guard: no further slots once is_final is set, and no duplicate final ---
        # A single query covers both cases:
        #   - Someone adds a non-final slot after is_final=True already exists
        #   - Someone tries to mark a second slot as is_final=True
        final_exists = (
            LexicalEntryGrapheme.objects
            .filter(entry=self.entry, is_final=True)
            .exclude(pk=self.pk)
            .exists()
        )
        if final_exists:
            raise ValidationError(
                "A final slot already exists for this entry. "
                "Cannot add further slots or mark another slot as final. "
                "To correct: set is_final=False on the current final slot first."
            )
 
        # --- Concatenation integrity check (only when marking this slot final) ---
        if self.is_final:
            prior_slots = (
                LexicalEntryGrapheme.objects
                .filter(entry=self.entry)
                .exclude(pk=self.pk)
                .order_by('slot')
                .select_related('letter__grapheme')
            )
            grapheme_list = (
                [s.letter.grapheme.notation for s in prior_slots]
                + [self.letter.grapheme.notation]
            )
            concatenated = ''.join(grapheme_list)
            if concatenated != self.entry.lemma:
                raise ValidationError(
                    f"Grapheme sequence '{concatenated}' does not match "
                    f"headword '{self.entry.lemma}'. "
                    "Correct the sequence before marking as final."
                )
      

class Sense(models.Model):
    
    """
    These will be relocated as rows to the Register and UsageLabel tables/models.
    """
    entry = models.ForeignKey(LexicalEntry, on_delete=models.CASCADE, related_name='senses')
    order = models.PositiveIntegerField(unique=True)
    translation = models.TextField(
        blank=True,
        help_text='a direct substitute'
    )
    definition = models.TextField(
        blank=True, null=True, 
        help_text='an elaborate explanation of meaning'
    )
    
    gloss_language = models.ForeignKey(Language, on_delete=models.CASCADE, related_name='glosses')
    domains = models.ManyToManyField(SemanticDomain, blank=True) 
    register = models.ManyToManyField(
        Register,
        blank=True,
        help_text='Register or style of usage - pragmatics'
    )
    is_ideophone = models.BooleanField(default=False)
    usage_label = models.ForeignKey(
        UsageLabel,
        on_delete=models.CASCADE,
        blank=True, null=True,
        help_text='Register or style of usage - pragmatics'
    )
    cultural_note = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        unique_together = ('entry', 'order')
        ordering = ['entry', 'order']
    
    def __str__(self):
        return f"{self.entry.lemma} | Sense {self.order}"

    
class Pronunciation(models.Model):
    """ 
    Entry Pronunciation variants with audio, supporting speaker variations.
    """
    
    entry = models.ForeignKey(LexicalEntry, on_delete=models.CASCADE, related_name='pronunciations')
    ipa = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text='IPA transcription of the word'
    )
    transcription_type = models.CharField(
        max_length=20,
        choices=[
            ('phonemic', 'Phonemic (Broad)'),
            ('phonetic', 'Phonetic (Narrow)'),
            ('both', 'Both (combined notation)'),
        ],
        default='phonemic'
    )
    dialect = models.ForeignKey(Dialect, on_delete=models.SET_NULL, null=True, blank=True)
    speaker = models.ForeignKey(Speaker, on_delete=models.SET_NULL, null=True, blank=True)
    audio = models.ManyToManyField(
        MediaFile,
        limit_choices_to={'media_type': 'audio'},
        blank=True, 
        related_name='pronunciation_audio'
    )
    note = models.CharField(max_length=255, blank=True)
    
    def __str__(self):
        if self.transcription_type == 'phonemic':
            return f"{self.entry.lemma} /{self.ipa}/"
        elif self.transcription_type == 'phonetic':
            return f"{self.entry.lemma} [{self.ipa}]"
        else:
            return f"{self.entry.lemma} {self.ipa}"
    


# =============================================================================
# 4. GRAMMATICAL & USAGE MODELS
# =============================================================================

class GrammaticalFeature(models.Model):
    """
    Subcategorization features (valency, countability, noun class, etc.).
    """
    entry = models.ForeignKey(LexicalEntry, on_delete=models.CASCADE, related_name='grammatical_features', null=True, blank=True)
    category = models.ForeignKey(GrammaticalCategory, on_delete=models.CASCADE, null=True, blank=True)
    value = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"{self.category.name}: {self.value}"
    

class Inflection(models.Model):
    """
    Inflectional and derivational forms. Linked to Sense to support sense-dependent morphology.
    """
    sense = models.ForeignKey(
        Sense, 
        on_delete=models.CASCADE, 
        related_name='inflections',
        null=True, blank=True,
        help_text='The inflection is associated with this sense of the entry'
    )
    entry = models.ForeignKey(
        LexicalEntry, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        help_text='If inflection is entry-based, specify, else null for sense-based inflection'
    )  # fallback

    label = models.CharField(max_length=100, null=True, blank=True, help_text="e.g., past tense, plural, gerund")
    form = models.CharField(max_length=200, blank=True, null=True, help_text="The inflected form of the word")
    dialect = models.ForeignKey(Dialect, on_delete=models.SET_NULL, null=True, blank=True)
    note = models.TextField(blank=True)
    
    def clean(self):
        super().clean()
        if not self.sense and not self.entry:
            raise ValidationError("Inflection must be linked to either a sense or an entry.")
        if self.entry and self.sense:
            raise ValidationError(
                "Inflection cannot be linked to both a sense and an entry."
                "If the inflection is sense-specific, link it to the sense; otherwise, link it to the entry."
            )
        
    
    def __str__(self):
        return f"{self.label}: {self.form}"


class Etymology(models.Model):
    """
    Etymological and historical information for a lexical entry
    """
    entry = models.OneToOneField(LexicalEntry, on_delete=models.CASCADE, related_name='etymology', null=True, blank=True)
    origin_text = models.TextField(blank=True)
    proto_form = models.CharField(max_length=200, blank=True)
    source_entry = models.ForeignKey(LexicalEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name='etymology_sources')
    

class Example(models.Model):
    """
    Example sentences/phrases with audio, interlinear gloss and speaker metadata
    """
    sense = models.ForeignKey(Sense, on_delete=models.CASCADE, related_name='examples', blank=True, null=True)
    text = models.TextField(blank=True)
    translation = models.TextField(blank=True)
    interlinear_gloss = models.TextField(blank=True)
    audio = models.ManyToManyField(
        MediaFile,
        blank=True,
        limit_choices_to={'media_type':'audio'},
    )
    speaker = models.ForeignKey(Speaker, on_delete=models.SET_NULL, null=True, blank=True)
    dialect = models.ForeignKey(Dialect, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.sense.entry.lemma} example(s)"


class Collocation(models.Model):
    """
    Word cluster:
    Group of 2-3 words spoken together (sometimes, for a specific meaning)
    """
    basic_entry = models.ForeignKey(LexicalEntry, on_delete=models.CASCADE, related_name='collocations')
    other_entries = models.ManyToManyField(LexicalEntry, related_name='collocation_with')
    audio = models.ManyToManyField(
        MediaFile,
        blank=True,
        limit_choices_to={'media_type':'audio'},
    )
    expression = models.TextField()
    translation = models.TextField(blank=True)
    speaker = models.ForeignKey(Speaker, on_delete=models.SET_NULL, null=True, blank=True)
    expression = models.TextField(blank=True)

    def clean(self):
        super().clean()
        if self.basic_entry and self.other_entries:
            if self.pk:
                if self.other_entries.filter(pk=self.basic_entry_id).exists():
                    raise ValidationError(
                        "An entry cannot be connected to itself"
                    )
    
    def __str__(self):
        return f"Collocations for {self.basic_entry.lemma}"


class SemanticRelation(models.Model):
    """
    Semantic and Phonological relationships between lexial entries
    """
    source_entry = models.ForeignKey(
        LexicalEntry,
        on_delete=models.CASCADE,
        related_name='related_targets',
    )
    target_entry = models.ForeignKey(
        LexicalEntry,
        on_delete=models.CASCADE,
        related_name='related_sources',
    )
    relation_type = models.ForeignKey(SemanticRelationTypes, on_delete=models.CASCADE, related_name='related_pair')
    note = models.TextField(blank=True)

    class Meta:
        unique_together = ('source_entry', 'target_entry', 'relation_type')    

class Illustration(models.Model):
    """
    Visual aids (images, diagrams) for concrete or cultural concepts
    """
    sense = models.ForeignKey(
        Sense,
        on_delete=models.CASCADE,
        related_name='illustrations',
        blank=True, null=True,
    )
    image = models.ForeignKey(MediaFile, on_delete=models.CASCADE, blank=True, null=True)
    caption = models.CharField(max_length=255, blank=True, null=True)


class Source(models.Model):
    """
    Provenance and word documentation metadata
    """
    entry = models.ForeignKey(
        LexicalEntry,
        on_delete = models.CASCADE,
        related_name='sources',
        blank=True, null=True,
    )
    example = models.ForeignKey(
        Example,
        on_delete=models.CASCADE,
        related_name='sources',
        blank=True, null=True,
    )
    speaker = models.ForeignKey(Speaker, on_delete=models.SET_NULL, null=True)
    recording_date = models.DateField(blank=True, null=True)
    location = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)


class CommunityNote(models.Model):
    """
    Community-contributed notes, corrections or cultural insights.
    Supports collaborative language revitalization.
    """
    sense = models.ForeignKey(Sense, on_delete=models.CASCADE, related_name='community_notes')
    user = models.ForeignKey(AkitaUser, on_delete=models.CASCADE, related_name='entry_notes', null=True, blank=True)
    content = models.TextField()
    image = models.ImageField(upload_to=set_user_uploaded_file_path, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']    
