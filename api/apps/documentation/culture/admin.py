from django.contrib import admin
from .models import SpeakerProfile


@admin.register(SpeakerProfile)
class SpeakerProfileAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'community', 'documented_by', 'speaker_user_account']
    list_filter = ['full_name', 'community']
    search_fields = ['full_name', 'community']
    ordering = ['-birth_year', 'full_name', 'community']
