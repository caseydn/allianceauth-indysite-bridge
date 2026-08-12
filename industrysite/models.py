from django.contrib.auth.models import User
from django.db import models


class IndustrySiteAccount(models.Model):
    """One row per AA user who has activated the Industry Site service.

    Stores the per-user token the industrial site issues on activation; AA
    presents it on every later update/deactivate call so the site can
    authenticate the specific user behind the service-level shared key.
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="industrysite_account"
    )
    main_character_id = models.PositiveBigIntegerField(null=True, blank=True)
    site_user_token = models.CharField(max_length=191, blank=True, default="")
    activated_at = models.DateTimeField(auto_now_add=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_result = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        verbose_name = "Industry Site account"
        permissions = (
            ("access_industrysite", "Can access the Industry Site service"),
        )

    def __str__(self):
        return f"{self.user.username} - Industry Site account"
