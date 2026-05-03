from django.db import models
from django.utils import timezone
#from django.utils.translation import gettext_lazy as _

# Create your models here.

class Language(models.Model):
    pass

class Dialect(models.Model):
    pass

class Speaker(models.Model):
    pass

class MediaFile(models.Model):
    pass

class Grapheme(models.Model):
    pass

class GraphemeFeaturedExample(models.Model):
    pass

class Root(models.Model):
    pass

class SemanticDomain(models.Model):
    pass

class PartOfSpeech(models.Model):
    pass

class GrammaticalCategory(models.Model):
    pass

class LexicalEntry(models.Model):
    pass

class VariantForm(models.Model):
    pass

class Sense(models.Model):
    pass

class Pronunciation(models.Model):
    pass

class GrammaticalFeature(models.Model):
    pass

class Inflection(models.Model):
    pass

class Etymology(models.Model):
    pass

class Example(models.Model):
    pass

class Collocation(models.Model):
    pass

class SemanticRelation(models.Model):
    pass

class Illustration(models.Model):
    pass

class Source(models.Model):
    pass

class CommunityNote(models.Model):
    pass

class GrammarTopic(models.Model):
    """For teaching grammar patterns and observed rules"""
    pass

class SentencePattern(models.Model):
    """Common sentence structures"""
    pass