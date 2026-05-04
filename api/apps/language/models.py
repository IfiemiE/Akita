from django.db import models
from django.utils import timezone
#from django.utils.translation import gettext_lazy as _

# Create your models here.

# ====================== CORE LANGUAGE & SOCIOLINGUISTIC MODELS ======================

class Language(models.Model):
    """
    Represents a language in the system
    Captures the language metadata and distinguishes it from translation languages.
    """
    pass

class Dialect(models.Model):
    """
    Captures dialectal variation within the dialect.
    Establishes the targeted dialect and distinguishes it from others
    """
    pass

class Speaker(models.Model):
    """
    Represents individual speakers of the targeted dialect/language
    Tracks who provided data, age, gender and reliability
    """
    pass

class MediaFile(models.Model):
    """
    Central multimedia storage for audio, video, and images.
    Supports rich documentation with pronunciation, cultural illustrations, and ideophones.
    """
    pass

# ====================== ORTHOGRAPHY FOUNDATION FOR LITERACY ======================

class Grapheme(models.Model):
    """
    Orthography/Writing system support
    Especially useful for a language with new or non-standard writing system.
    """
    pass

class GraphemeFeaturedExample(models.Model):
    """Links graphemes to example words with notes for literacy materials"""
    pass

# ====================== MORPHOLOGICAL & SEMANTIC FOUNDATION ======================

class Root(models.Model):
    """
    Stores morphological roots.
    Enables derivation tracking and etymological understanding.
    """
    pass

class SemanticDomain(models.Model):
    """
    Hierarchical semantic domains classification
    Useful for semantic search, language learning, revitalization and organizing vocabulary by meaning.
    Example: 1.5 -> Living Things -> 1.5.2 -> Plants
    """
    pass

class PartOfSpeech(models.Model):
    """Part of Speech categories (Noun, Verb, Ideophones, etc)"""
    pass

class GrammaticalCategory(models.Model):
    """
    Language-specific grammatical categories (Noun Class, Valency, Tone Pattern, Subject Marker)
    Captures complex morphology typical of many African and low-resource language.
    """
    pass

# ====================== CORE LEXICAL ENTRY ======================

class LexicalEntry(models.Model):
    """
    The central model representing a dictionary headword/entry.
    Combines orthography, morphology, grammar, Pronunciation, and multimedia for comprehensive documentation.
    """
    pass

class VariantForm(models.Model):
    """Alternative spellings, pronunciations, or dialectal variants of a lexical entry"""
    pass

class Pronunciation(models.Model):
    """
    Rich pronunciation data including IPA, speaker variation, and audio.
    Critical for tonal and phonologically complex low-resource languages.    
    """
    pass

class GrammaticalFeature(models.Model):
    """Language-specific grammatical features (e.g Noun Class 3/4, Causative)"""
    pass

class Inflection(models.Model):
    """Inflected forms (paradigms) such as plural, past tense, etc"""
    pass


# ====================== SENSES & USAGE ======================

class Sense(models.Model):
    """
    Individual senses/meanings of a polysemous word.
    Captures definitions, (English) translations, cultural notes, semantic domains, ideophones,
    and revitalization metadata.
    """
    pass

class Example(models.Model):
    """
    Naturalistic example sentences with translations and multimedia.
    """
    pass

class Collocation(models.Model):
    """Common word combinations and phrases"""
    pass

# ====================== RELATIONS & SUPPLEMENTARY ======================

class SemanticRelation(models.Model):
    """
    Semantic and phonological relationships between entries
    Includes synonyms, antonyms, hyponyms, and minimal pairs (useful for phonological training).
    """
    pass

class Illustration(models.Model):
    """Visual illustrations linked to entries or senses"""
    pass

class Etymology(models.Model):
    """Etymological and historical information about a lexical entry."""
    pass

class Source(models.Model):
    """Provenance and citation information for entries and examples."""
    pass

class CommunityNote(models.Model):
    """
    Community-contibuted notes on word senses.
    Supports participatory dictionary making and language revitalization.
    """
    pass

class ChallengeParticipation(models.Model):
    """Track users who joined a challenge (optional)"""
    pass

# ====================== GRAMMAR - RULES & PATTERNS ======================

class GrammarTopic(models.Model):
    """
    For teaching grammar patterns and observed rules.
    Major grammatical topic or construction (e.g. "Serial Verbs", "Noun Class Agreement", "Focus Constructions")
    """
    pass

class SentencePattern(models.Model):
    """Specific syntactic patterns discovered through elicitation"""
    pass

class PatternExample(models.Model):
    """
    Multiple real examples for each sentence pattern - For learning and verifications
    """
    pass

class FixedExpressions(models.Model):
    """
    Captures greetings, idioms, proverbs, fixed phrases, and culturally bound expressions
    that are said in a specific way and often carry non-literal meaning.    
    """
    pass

# ====================== MEDIA WORKFLOW & VISITOR INPUT ======================

class PendingMediaUpload(models.Model):
    """
    Staging area for media uploaded by contibutors.
    Media is reviewed by administrators before being moved to MediaFile and Linked to cultural/dictionary content.
    """
    pass

class VisitorSuggestion(models.Model):
    """
    Public feedback and suggestions from any site visitor (including anonymous users)
    Limited to 5 per day per IP. Auto-deleted after 7 days. Supports "Noted" workflow.
    """