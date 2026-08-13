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

from . import app_settings, data_sources
from .signing import verify

logger = logging.getLogger(__name__)


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
