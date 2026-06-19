from django.contrib import admin
from .models import AkitaUser, SpeakerProfile

@admin.register(AkitaUser)
class AkitaUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'full_name', 'role', 'community', 'registered_by', 'is_active']
    list_filter = ['username', 'role', 'community']
    search_fields = ['username', 'role', 'community']
    ordering = ['-registration_date', 'username']

@admin.register(SpeakerProfile)
class SpeakerProfileAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'community', 'documented_by', 'speaker_user_account']
    list_filter = ['full_name', 'community']
    search_fields = ['full_name', 'community']
    ordering = ['-birth_year', 'full_name', 'community']