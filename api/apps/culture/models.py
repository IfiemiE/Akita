from django.db import models
from django.utils import timezone
# from core.models import MediaTag
# from users.models import akitaUser

# Create your models here.

class CulturalDomain(models.Model):
    """Broad cultural categories: Food, Festival, Ritual, Craft, Rites"""
    pass

class CulturalItem(models.Model):
    """Main model for cultural content for each cultural domain"""
    pass

# Continue with a model for each section/category to capture its peculiarities (e.g Food - Recipe, Music - instrument)
# This implies that more sections can be added as they are discovered or realized.
