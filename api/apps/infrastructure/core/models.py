from django.db import models
from django.core.exceptions import ValidationError
from apps.common.constants import AKITA_COMMUNITIES


class Language(models.Model):
    """The Language as a family of variant dialects"""  
    name = models.CharField(max_length=100, unique=True, null=False)
    # set ISO 693-3 Language Standard Codes
    iso_code = models.CharField(max_length=10, blank=True, null=True)
    is_target = models.BooleanField(default=True)
    
    def clean(self):
        if self.is_target:
            existing = Language.objects.filter(is_target=True).exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError(
                    'Another language has been set as the target/application language'
                )
    def save(self, *args, **kwargs):
        if not Language.objects.exists(): # for first record
            if not self.is_target: # for record not set as target
                raise ValidationError('Ensure the target language is entered first')
        return super().save(*args, **kwargs)
                
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['is_target'],
                condition=models.Q(is_target=True),
                name='unique_target_language',
            )
        ]           
        
    def __str__(self):
        return self.name


class Dialect(models.Model):
    """The Dialect variant of the Language."""
    language = models.ForeignKey(Language, on_delete=models.CASCADE, related_name='dialects', null=False, blank=False)
    name = models.CharField(max_length=100, default='Akita')
    # set ISO 693-3 Language Standard Codes (for Ijaw, it is dialect-based)
    iso_code = models.CharField(max_length=10, blank=True, null=True, default='okd')
    is_target = models.BooleanField(default=True)
    
    def clean(self):
        # check if iso-code is set for language already
        if self.language and self.language.iso_code and self.iso_code:
            if str(self.language.iso_code).strip() != str(self.iso_code).strip():
                raise ValidationError(
                    'if iso-code is set for language and for dialect, then they must be the same'
                )
    
    def save(self, *args, **kwargs):
        if not Dialect.objects.exists(): # for first record
            if not self.is_target: # for record not set as target
                raise ValidationError('Ensure the target dialect is entered first')
        return super().save(*args, **kwargs)
               
    class Meta:
        unique_together = ('language', 'name')
        constraints = [
            models.UniqueConstraint(
                fields=['is_target'],
                condition=models.Q(is_target=True),
                name='unique_target_dialect',
            )
        ]           
    
    def __str__(self):
        return f'{self.name}-{self.language.name}'
         

 
class Community(models.Model):
    """A general community class: A Speaker's community background""" 
    
    name = models.CharField(max_length=100, unique=True)
    alternate_names = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    
    class Meta:
        ordering = ['name']
        verbose_name_plural = 'communities'

    def __str__(self):
        return self.name
    

class AkitaCommunity(Community):
    """A class for Communities in Okordia - To be used for registered users"""
    
    VALID_COMMUNITIES = [c.capitalize() for c in AKITA_COMMUNITIES]

    is_active = models.BooleanField(default=True)
    
    def clean(self):
        super().clean()
        if self.name.capitalize() not in self.VALID_COMMUNITIES:
            raise ValidationError(
                {'name': f'"{self.name}" is not a recognised Akita community.'}
            ) 
            
    class Meta:
        ordering = ['name']
        verbose_name_plural = 'akita communities'


class MediaTag(models.Model):
    """Taxonomic tags for content classification."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Category(models.Model):
    """Hierarchical categories for organizing content."""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class SiteSetting(models.Model):
    """Key-value store for site configuration."""
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['key']

    def __str__(self):
        return self.key
