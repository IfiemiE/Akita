from django.contrib import admin
from .models import AkitaUser

@admin.register(AkitaUser)
class AkitaUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'full_name', 'role', 'community', 'registered_by', 'is_active']
    list_filter = ['username', 'role', 'community']
    search_fields = ['username', 'role', 'community']
    ordering = ['-registration_date', 'username']
    