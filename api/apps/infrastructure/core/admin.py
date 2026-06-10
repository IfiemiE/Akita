from django.contrib import admin
from .models import Community, AkitaCommunity, MediaTag, Category, SiteSetting
# Register your models here.

@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ['name']
    
@admin.register(AkitaCommunity)
class AkitaCommunityAdmin(admin.ModelAdmin):
    list_display = ['name']

@admin.register(MediaTag)
class MediaTagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']

@admin.register(Category)
class CategoryAmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'parent']
    list_filter = ['name', 'parent']
    search_fields = ['name', 'parent']
    ordering = ['parent', 'name']

@admin.register(SiteSetting)
class SiteSettingAmin(admin.ModelAdmin):
    list_display = ['key', 'value']
    list_filter = ['key']
    search_fields = ['key']
    readonly_fields = ['key', 'value']

