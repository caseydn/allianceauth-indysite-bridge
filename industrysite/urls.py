from django.urls import path

from . import provider, views

app_name = "industrysite"

urlpatterns = [
    # Service-control actions (from the AA Services page).
    path("activate/", views.activate, name="activate"),
    path("deactivate/", views.deactivate, name="deactivate"),
    # Pull API (industrial site -> AA) for ESI-data offload. HMAC-authenticated.
    path(
        "api/characters/<int:character_id>/assets/",
        provider.character_assets,
        name="api_assets",
    ),
    path(
        "api/characters/<int:character_id>/industry-jobs/",
        provider.character_industry_jobs,
        name="api_industry_jobs",
    ),
    path(
        "api/characters/<int:character_id>/skills/",
        provider.character_skills,
        name="api_skills",
    ),
]
