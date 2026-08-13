import logging

from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import path

from allianceauth.authentication.models import CharacterOwnership

from . import collector, data_sources
from .models import IndustrySiteAccount

logger = logging.getLogger(__name__)


@admin.register(IndustrySiteAccount)
class IndustrySiteAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "main_character_id", "last_synced_at", "last_result")
    search_fields = ("user__username", "main_character_id")
    readonly_fields = ("activated_at", "last_synced_at", "last_result")
    change_list_template = "industrysite/admin_accounts_changelist.html"

    def get_urls(self):
        custom = [
            path(
                "data-preview/",
                self.admin_site.admin_view(self.data_preview_view),
                name="industrysite_data_preview",
            ),
        ]
        return custom + super().get_urls()

    def data_preview_view(self, request):
        """Show exactly what the plugin would serve the industrial site for a
        given character: which AA source has each dataset + row counts, plus the
        identity/roles push payload. Reads AA's stored data only — no ESI calls.
        """
        character_id = (request.GET.get("character_id") or "").strip()
        context = dict(
            self.admin_site.each_context(request),
            title="Industry Site — data being provided",
            character_id=character_id,
            result=None,
        )

        if character_id.isdigit():
            cid = int(character_id)
            owner = (
                CharacterOwnership.objects.filter(character__character_id=cid)
                .select_related("user")
                .first()
            )
            payload = None
            if owner and owner.user_id:
                try:
                    payload = collector.build_user_payload(owner.user)
                except Exception:
                    logger.exception("industrysite data preview payload failed for %s", cid)

            try:
                described = data_sources.describe(cid)
            except Exception:
                logger.exception("industrysite data preview describe failed for %s", cid)
                described = {}

            context["result"] = {
                "character_id": cid,
                "owner": owner.user.username if owner and owner.user_id else None,
                "data": described,
                "payload": payload,
            }

        return TemplateResponse(request, "industrysite/data_preview.html", context)
