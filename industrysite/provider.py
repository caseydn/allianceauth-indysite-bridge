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


def _cache_key(character_id: int, kind: str) -> str:
    return f"industrysite:pull:{kind}:{character_id}"


def _respond(character_id: int, kind: str, source):
    """Read `kind` for a character from AA's stored data (Member Audit / CorpTools).

    `source` is a data_sources reader that returns already-stored data or None.
    Never triggers an ESI call.
    """
    key = _cache_key(character_id, kind)
    data = cache.get(key)

    if data is None:
        try:
            data = source(character_id)
        except Exception:  # pragma: no cover - defensive
            logger.exception("industrysite read %s failed for %s", kind, character_id)
            data = None

        if data is None:
            # Not audited / not synced in AA yet — no ESI fallback here by design.
            return JsonResponse(
                {"character_id": character_id, "error": "no_data", "kind": kind},
                status=404,
            )

        cache.set(key, data, app_settings.INDUSTRYSITE_PULL_CACHE)

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
