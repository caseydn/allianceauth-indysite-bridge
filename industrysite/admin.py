from django.contrib import admin

from .models import IndustrySiteAccount


@admin.register(IndustrySiteAccount)
class IndustrySiteAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "main_character_id", "last_synced_at", "last_result")
    search_fields = ("user__username", "main_character_id")
    readonly_fields = ("activated_at", "last_synced_at", "last_result")
