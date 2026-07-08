from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from model_utils import FieldTracker



class ToneRegister(models.Model):
    """
    Master list of tones in the language.
    Each tone has a name, a phonological value, and a diacritic mark.
    """
    NAME_CHOICES = [
        ('low', 'Low'),
        ('mid', 'Mid'),
        ('rising', 'Rising'),
        ('high', 'High'),
        ('falling', 'Falling'),    
    ]
    MARK_CHOICES = [
        ('diacritic', 'Diacritic'),
        ('line under', 'Line Under'),
        ('line over', 'Line Over'),
        
    ]
    name = models.CharField(
        max_length=50,
        unique=True,
        choices=NAME_CHOICES,
        default='mid',
        help_text='The name of the tone (e.g., low, mid, rising, high, falling)',
    )

    def __str__(self):
        return f"{self.name}"


class PhonemeRegister(models.Model):
    """IPA sound characters detected in the dialect, collated as a reference register."""
    ipa = models.CharField(
        max_length=10, 
        unique=True,
        help_text='The IPA character representing the sound'
    )
    sound = models.FileField(
        upload_to='records/%Y/%m', 
        blank=True, null=True, 
        validators=[FileExtensionValidator(allowed_extensions=['mp3', 'wav', 'ogg']),
                    ]
    )
    tone = models.ForeignKey(
        ToneRegister,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        help_text="The distinction on sound level of phoneme type"
    )
    is_vowel = models.BooleanField(default=False)
    description = models.CharField(max_length=100)
    
    class Meta:
        ordering = ['ipa']
        
    def __str__(self):
        return self.ipa
    

class GraphemeRegister(models.Model):
    """
    Global inventory of all potential grapheme symbols, independent of
    any orthographic system. A symbol enters here once; systems select
    from this register when building their alphabet.
    """
    notation = models.CharField(max_length=10, unique=True)
    character_count = models.PositiveSmallIntegerField(
        default=1, 
        help_text=(
            "Number of Unicode characters that compose this grapheme."
            "1 for monographs, 2 for digraphs, 3 for trigraphs, etc."
        ),
    )
    description = models.CharField(max_length=100)


class OrthographicSystemRegister(models.Model):
    """This opens the window for more than one system of orthography
       It is a choice collection of character-sound pairs.
    """
    name = models.CharField(
        max_length=100, 
        unique=True,
        help_text='A name used to identify this particular collection of graphemes-phonemes pairs')
    
    is_default = models.BooleanField(
        default=False,
        help_text=(
            "The default/fixed system for the server side."
            "Only one True must exist at a time."
            " It is transliterated to client's choice per toggle request."
        ),
    )
    
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        constraints = [
                models.UniqueConstraint(
                    fields=['is_default'],
                    condition=models.Q(is_default=True),
                    name='unique_default_system',
                )
        ]      
    
    def __str__(self):
        return f"{self.name}{' (default)' if self.is_default else ''}"
    

class Alphabet(models.Model):
    """
    The graphemes and phonemes are selected and paired from their pre-populated registers.
    Each pair is ranked, and the grapheme in a system is allotted a pronunciation  for convenience
    (with IPA phoneme sound present).
    """
    orthographic_system = models.ForeignKey(OrthographicSystemRegister, on_delete=models.CASCADE, related_name='alphabet_entries')
    grapheme = models.ForeignKey(GraphemeRegister, on_delete=models.CASCADE, related_name='alphabet_placements')
    phoneme = models.ForeignKey(PhonemeRegister, on_delete=models.CASCADE, related_name='alphabet_placements')
    pronunciation = models.FileField(
        upload_to='records/%Y/%m', 
        blank=True, null=True, 
        validators=[FileExtensionValidator(allowed_extensions=['mp3', 'wav', 'ogg']),],
    )
    order = models.PositiveSmallIntegerField()   
    featured_examples = models.ManyToManyField(
        'documentation_lexicon.LexicalEntry',
        through='GraphemeFeaturedExample',
        related_name='featured_in_alphabet_entries', 
        blank=True,
    )
    note = models.TextField(blank=True, null=True)
    
    # Tracks 'order' and 'grapheme' changes so signals fire only when needed.
    tracker = FieldTracker(fields=['order', 'grapheme', 'phoneme'])
    
    class Meta:
        unique_together = [
            ('orthographic_system', 'order'),            # rank unique per system
            ('orthographic_system', 'grapheme'), # no duplicate grapheme per system
        ]
        ordering = ['orthographic_system', 'order']
            
    def __str__(self):
        return f"{self.orthographic_system.name} | {self.grapheme.notation} | {self.order}"
    

class GraphemeFeaturedExample(models.Model):
    """Selected word entry examples for each grapheme and phoneme pair"""
    letter = models.ForeignKey(
        Alphabet,
        on_delete=models.CASCADE,
        related_name='example_entries',
    )
    entry = models.ForeignKey('documentation_lexicon.LexicalEntry', on_delete=models.CASCADE, related_name='grapheme_feature_appearances')
    priority = models.PositiveIntegerField(default=1)
    note = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = [('letter', 'entry'), ('letter', 'priority')]
        ordering = ['priority']
    
    def __str__(self):
        return f'{self.priority}. {self.letter.grapheme.notation}: {self.entry.lemma}'
