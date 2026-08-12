"""Re-push a user's snapshot when their AA group membership changes, so role
mappings on the industrial site stay in sync without waiting for a manual
update.
"""

import logging

from django.contrib.auth.models import User
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from .models import IndustrySiteAccount
from .tasks import push_account

logger = logging.getLogger(__name__)


@receiver(m2m_changed, sender=User.groups.through)
def user_groups_changed(sender, instance, action, **kwargs):
    if action not in ("post_add", "post_remove", "post_clear"):
        return
    # instance is the User when groups are edited via user.groups.
    if isinstance(instance, User) and IndustrySiteAccount.objects.filter(user=instance).exists():
        push_account.delay(instance.pk)
