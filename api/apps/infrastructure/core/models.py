from django.db import models

class Community(models.Model):
    """The five 'original' communities/villages of the Akita clan."""
    ORIGINAL_COMMUNITIES = [
        ('agbobiri', 'Agbobiri'),
        ('akumoni', 'Akumoni'),
        ('ayamabele', 'Ayamabele'),
        ('kalaba', 'Kalaba'),
        ('ikarama', 'Ikarama')
    ]
    
    
    name = models.CharField(max_length=100, unique=True, choices=ORIGINAL_COMMUNITIES, default='agbobiri')
    alternate_names = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'communities'

    def __str__(self):
        return self.name


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
