"""Celery tasks. Pushes run off the request cycle and retry on transient
failures so a brief site/network outage doesn't lose a registration.
"""

import logging

from celery import shared_task
from django.contrib.auth.models import User
from django.utils import timezone

from .collector import build_user_payload
from .manager import IndustrySiteManager
from .models import IndustrySiteAccount

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=5, default_retry_delay=30)
def push_account(self, user_id: int, activate: bool = False):
    """Send (or re-send) a user's full snapshot to the industrial site."""
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.warning("industrysite push: user %s no longer exists", user_id)
        return

    account, _ = IndustrySiteAccount.objects.get_or_create(user=user)
    payload = build_user_payload(user)
    account.main_character_id = payload.get("main_character_id")

    try:
        if activate or not account.site_user_token:
            result = IndustrySiteManager.activate_user(payload)
            token = str(result.get("user_token") or "")
            if token:
                account.site_user_token = token
        else:
            IndustrySiteManager.update_user(payload, user_token=account.site_user_token)
        account.last_result = "ok"
        account.last_synced_at = timezone.now()
        account.save()
        logger.info("industrysite push ok for user %s", user_id)
    except Exception as exc:
        account.last_result = f"error: {exc}"[:64]
        account.save(update_fields=["last_result", "main_character_id"])
        logger.exception("industrysite push failed for user %s", user_id)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=5, default_retry_delay=30)
def deactivate_account(self, user_id: int):
    """Tell the site to unlink the user, then drop the local account row."""
    try:
        account = IndustrySiteAccount.objects.get(user_id=user_id)
    except IndustrySiteAccount.DoesNotExist:
        return

    payload = {"aa_user_id": user_id, "main_character_id": account.main_character_id}
    try:
        IndustrySiteManager.deactivate_user(payload, user_token=account.site_user_token)
    except Exception as exc:
        logger.exception("industrysite deactivate failed for user %s", user_id)
        raise self.retry(exc=exc)

    account.delete()
    logger.info("industrysite deactivated user %s", user_id)
