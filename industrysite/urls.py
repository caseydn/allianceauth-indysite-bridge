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
    path(
        "api/characters/<int:character_id>/planets/",
        provider.character_planets,
        name="api_planets",
    ),
    # Bulk location id -> name resolution from Member Audit (stations + structures).
    path("api/locations/", provider.location_names, name="api_locations"),
    # SDE (Static Data Export) read from AA's eveuniverse / CorpTools SDE.
    path("api/sde/types/", provider.sde_types, name="api_sde_types"),
    path("api/sde/types/<int:type_id>/", provider.sde_type, name="api_sde_type"),
    path(
        "api/sde/types/<int:type_id>/materials/",
        provider.sde_type_materials,
        name="api_sde_type_materials",
    ),
    path("api/sde/blueprints/<int:type_id>/", provider.sde_blueprint, name="api_sde_blueprint"),
    # Bulk SDE export (paginated) for the site's full sde:import --aa refresh.
    path("api/sde/export/counts/", provider.sde_export_counts, name="api_sde_export_counts"),
    path("api/sde/export/types/", provider.sde_export_types, name="api_sde_export_types"),
    path("api/sde/export/groups/", provider.sde_export_groups, name="api_sde_export_groups"),
    path("api/sde/export/categories/", provider.sde_export_categories, name="api_sde_export_categories"),
    path("api/sde/export/blueprints/", provider.sde_export_blueprints, name="api_sde_export_blueprints"),
    path(
        "api/sde/export/blueprint-materials/",
        provider.sde_export_blueprint_materials,
        name="api_sde_export_blueprint_materials",
    ),
    path(
        "api/sde/export/type-materials/",
        provider.sde_export_type_materials,
        name="api_sde_export_type_materials",
    ),
]
