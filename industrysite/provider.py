"""Pull API (industrial site -> Alliance Auth) — reads data ALREADY in AA's DB.

Alliance Auth is NOT used as an ESI gateway here. A character's assets / industry
jobs / skills are already stored in Alliance Auth by Member Audit / CorpTools and
kept fresh by AA's own schedules. These HMAC-signed endpoints simply read that
in-place data and hand it to the industrial site. **No ESI calls are ever made
from this module** — if the data isn't in AA's database yet, we return 404 and the
site handles it on its side.
"""

import logging
from functools import wraps

from django.core.cache import cache
from django.http import HttpResponseForbidden, JsonResponse

from . import app_settings, data_sources, sde_sources
from .signing import verify

logger = logging.getLogger(__name__)

# SDE is effectively static — cache pull responses for a day.
SDE_CACHE = 86400


def require_signature(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        timestamp = request.headers.get("X-AA-Timestamp", "")
        signature = request.headers.get("X-AA-Signature", "")
        if not verify(timestamp, request.get_full_path(), signature):
            return HttpResponseForbidden("invalid signature")
        return view(request, *args, **kwargs)

    return wrapper


def _respond(character_id: int, kind: str, source):
    """Read `kind` for a character straight from AA's stored data (Member Audit /
    CorpTools). NOT cached — Member Audit is already the cache; a cache layer here
    previously served stale-empty (`200 · 0 rows`) responses. Always reads fresh.
    Never triggers an ESI call.
    """
    try:
        data = source(character_id)
    except Exception:  # pragma: no cover - defensive
        logger.exception("industrysite read %s failed for %s", kind, character_id)
        data = None

    if data is None:
        # Character not audited / not synced in AA. No ESI fallback by design.
        return JsonResponse(
            {"character_id": character_id, "error": "no_data", "kind": kind},
            status=404,
        )

    count = len(data.get("skills", [])) if isinstance(data, dict) else len(data)
    logger.info("industrysite served %s %s rows for char %s", count, kind, character_id)

    return JsonResponse({"character_id": character_id, kind: data})


@require_signature
def character_assets(request, character_id):
    return _respond(character_id, "assets", data_sources.assets)


@require_signature
def character_industry_jobs(request, character_id):
    return _respond(character_id, "industry_jobs", data_sources.industry_jobs)


@require_signature
def character_skills(request, character_id):
    return _respond(character_id, "skills", data_sources.skills)


@require_signature
def character_planets(request, character_id):
    return _respond(character_id, "planets", data_sources.planets)


@require_signature
def location_names(request):
    """Resolve location ids -> names from Member Audit: /locations/?ids=60003760,... """
    raw = request.GET.get("ids", "")
    ids = [int(x) for x in raw.split(",") if x.strip().isdigit()]
    if not ids:
        return JsonResponse({"locations": []})
    data = data_sources.locations(ids)
    return JsonResponse({"locations": data if data is not None else []})


# --------------------------------------------------------------------------- #
# SDE endpoints (read from AA's eveuniverse / CorpTools SDE — no ESI)
# --------------------------------------------------------------------------- #
@require_signature
def sde_type(request, type_id):
    key = f"industrysite:sde:type:{type_id}"
    data = cache.get(key)
    if data is None:
        data = sde_sources.type_info(type_id)
        if data is None:
            return JsonResponse({"type_id": type_id, "error": "not_found"}, status=404)
        cache.set(key, data, SDE_CACHE)
    return JsonResponse(data)


@require_signature
def sde_types(request):
    """Bulk name resolution: /sde/types/?ids=34,35,36 -> {types:{id:name}}."""
    raw = request.GET.get("ids", "")
    ids = [int(x) for x in raw.split(",") if x.strip().isdigit()]
    if not ids:
        return JsonResponse({"types": {}})
    return JsonResponse({"types": sde_sources.types_bulk(ids)})


@require_signature
def sde_type_materials(request, type_id):
    key = f"industrysite:sde:mats:{type_id}"
    data = cache.get(key)
    if data is None:
        data = sde_sources.type_materials(type_id) or []
        cache.set(key, data, SDE_CACHE)
    return JsonResponse({"type_id": type_id, "materials": data})


@require_signature
def sde_blueprint(request, type_id):
    key = f"industrysite:sde:bp:{type_id}"
    data = cache.get(key)
    if data is None:
        data = sde_sources.blueprint(type_id)
        if data is None:
            return JsonResponse({"blueprint_type_id": type_id, "error": "not_found"}, status=404)
        cache.set(key, data, SDE_CACHE)
    return JsonResponse(data)


# --------------------------------------------------------------------------- #
# Bulk SDE export — for the site's `sde:import --aa` full refresh. Paginated.
# --------------------------------------------------------------------------- #
def _page(request, default_limit, max_limit):
    try:
        offset = max(0, int(request.GET.get("offset", 0)))
    except (TypeError, ValueError):
        offset = 0
    try:
        limit = int(request.GET.get("limit", default_limit))
    except (TypeError, ValueError):
        limit = default_limit
    return offset, max(1, min(limit, max_limit))


@require_signature
def sde_export_counts(request):
    return JsonResponse(sde_sources.export_counts())


@require_signature
def sde_export_types(request):
    offset, limit = _page(request, 1000, 5000)
    rows = sde_sources.export_types(offset, limit)
    return JsonResponse({"offset": offset, "limit": limit, "count": len(rows), "rows": rows})


@require_signature
def sde_export_groups(request):
    offset, limit = _page(request, 2000, 10000)
    rows = sde_sources.export_groups(offset, limit)
    return JsonResponse({"offset": offset, "limit": limit, "count": len(rows), "rows": rows})


@require_signature
def sde_export_categories(request):
    offset, limit = _page(request, 2000, 10000)
    rows = sde_sources.export_categories(offset, limit)
    return JsonResponse({"offset": offset, "limit": limit, "count": len(rows), "rows": rows})


@require_signature
def sde_export_blueprints(request):
    offset, limit = _page(request, 1000, 5000)
    rows = sde_sources.export_blueprints(offset, limit)
    return JsonResponse({"offset": offset, "limit": limit, "count": len(rows), "rows": rows})


@require_signature
def sde_export_blueprint_materials(request):
    offset, limit = _page(request, 2000, 10000)
    rows = sde_sources.export_blueprint_materials(offset, limit)
    return JsonResponse({"offset": offset, "limit": limit, "count": len(rows), "rows": rows})


@require_signature
def sde_export_type_materials(request):
    offset, limit = _page(request, 2000, 10000)
    rows = sde_sources.export_type_materials(offset, limit)
    return JsonResponse({"offset": offset, "limit": limit, "count": len(rows), "rows": rows})
