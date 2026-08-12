from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="IndustrySiteAccount",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("main_character_id", models.PositiveBigIntegerField(blank=True, null=True)),
                ("site_user_token", models.CharField(blank=True, default="", max_length=191)),
                ("activated_at", models.DateTimeField(auto_now_add=True)),
                ("last_synced_at", models.DateTimeField(blank=True, null=True)),
                ("last_result", models.CharField(blank=True, default="", max_length=64)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="industrysite_account",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Industry Site account",
                "permissions": (
                    ("access_industrysite", "Can access the Industry Site service"),
                ),
            },
        ),
    ]
