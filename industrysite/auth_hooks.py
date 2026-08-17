from allianceauth import hooks
from allianceauth.services.hooks import UrlHook

from . import urls
from .services import IndustrySiteService


@hooks.register("services_hook")
def register_service():
    return IndustrySiteService()


# The pull/SDE API endpoints authenticate with the HMAC shared-key signature, not an
# AA session login. AA auto-decorates every custom-app view with
# `main_character_required`, which would 302 these signed server-to-server requests to
# the login page. Marking them as PUBLIC VIEWS excludes them from that decorator.
# NOTE: the AA admin must ALSO add "industrysite" to APPS_WITH_PUBLIC_VIEWS in
# local.py for these to actually be served publicly. The user-facing activate/
# deactivate views are intentionally left protected (login required).
PUBLIC_API_VIEWS = [
    "industrysite.provider.character_assets",
    "industrysite.provider.character_industry_jobs",
    "industrysite.provider.character_skills",
    "industrysite.provider.location_names",
    "industrysite.provider.sde_type",
    "industrysite.provider.sde_types",
    "industrysite.provider.sde_type_materials",
    "industrysite.provider.sde_blueprint",
    "industrysite.provider.sde_export_counts",
    "industrysite.provider.sde_export_types",
    "industrysite.provider.sde_export_groups",
    "industrysite.provider.sde_export_categories",
    "industrysite.provider.sde_export_blueprints",
    "industrysite.provider.sde_export_blueprint_materials",
    "industrysite.provider.sde_export_type_materials",
]


@hooks.register("url_hook")
def register_urls():
    # Mounts urls.py under /industrysite/ with the "industrysite" namespace; the API
    # views are excluded from the default main_character_required (public views).
    return UrlHook(urls, "industrysite", r"^industrysite/", excluded_views=PUBLIC_API_VIEWS)
