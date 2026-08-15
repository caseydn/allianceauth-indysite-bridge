"""The Alliance Auth ServicesHook for the Industry Site service. Mirrors the
shape of the built-in Discord service: it renders an Activate/Deactivate row
on the user's Services page and reacts to group changes / eligibility loss.
"""

import logging

from django.template.loader import render_to_string

from allianceauth.services.hooks import ServicesHook

from . import app_settings
from .models import IndustrySiteAccount
from .tasks import notify_site_deactivate, push_account

logger = logging.getLogger(__name__)


class IndustrySiteService(ServicesHook):
    def __init__(self):
        ServicesHook.__init__(self)
        self.name = "industrysite"
        self.service_ctrl_template = "industrysite/services_ctrl.html"
        self.access_perm = "industrysite.access_industrysite"

    @property
    def title(self):
        return app_settings.INDUSTRYSITE_TAG

    def service_active_for_user(self, user):
        return user.has_perm(self.access_perm)

    def delete_user(self, user, notify_user=False):
        account = IndustrySiteAccount.objects.filter(user=user).first()
        if not account:
            return False
        # Unlink locally immediately, notify the site best-effort in the background.
        user_id = user.pk
        main_id = account.main_character_id
        token = account.site_user_token
        account.delete()
        notify_site_deactivate.delay(user_id, main_id, token)
        if notify_user:
            try:
                from allianceauth.notifications import notify

                notify(
                    user,
                    "Industry Site account disabled",
                    "Your access was revoked, so your Industry Site link was removed.",
                    level="warning",
                )
            except Exception:  # pragma: no cover - notifications optional
                logger.debug("industrysite: could not notify user %s", user.pk)
        return True

    def validate_user(self, user):
        """Remove the link if the user is no longer eligible for the service."""
        if IndustrySiteAccount.objects.filter(user=user).exists() and not self.service_active_for_user(user):
            logger.info("industrysite: validating out ineligible user %s", user.pk)
            self.delete_user(user, notify_user=True)

    def update_groups(self, user):
        """AA calls this when the user's group membership changes."""
        if IndustrySiteAccount.objects.filter(user=user).exists():
            push_account.delay(user.pk)

    def update_all_groups(self):
        for account in IndustrySiteAccount.objects.all().only("user_id"):
            push_account.delay(account.user_id)

    def render_services_ctrl(self, request):
        urls = self.Urls()
        urls.auth_activate = "industrysite:activate"
        urls.auth_deactivate = "industrysite:deactivate"
        connected = IndustrySiteAccount.objects.filter(user=request.user).exists()
        return render_to_string(
            self.service_ctrl_template,
            {
                "service_name": self.title,
                "urls": urls,
                "service_url": app_settings.INDUSTRYSITE_URL,
                "connected": connected,
                "username": request.user.username,
            },
            request=request,
        )
