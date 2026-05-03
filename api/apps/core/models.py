from django.db import models
from django.utils.translation import gettext_lazy as _

# Create your models here.

class MediaTag(models.Model):
    """Reusable tags/labels for all media across the site (culture, language, etc)"""
    pass

class Category(models.Model):
    """Generate hierarchical category system across the entire platform"""
    pass

class SiteSetting(models.Model):
    """Key-Value Site Settings for the entire platform"""
    pass

class Page(models.Model):
    """Reusable static-like pages (About, Contact, Privacy, etc)"""
    pass