"""Pull API (industrial site -> Alliance Auth) for ESI-data offload.

The industrial site calls these HMAC-signed endpoints instead of hitting CCP
itself. Each endpoint resolves a valid token AA already holds for the
character and fetches the data via django-esi, caching the result briefly so
repeated site requests don't re-hit ESI. Because the call is made from AA's
process (AA's IP / error budget), the industrial site's own ESI budget is
never touched.

Only AA core + django-esi are required. If you run Member Audit or CorpTools
and would rather read their already-cached tables (zero ESI calls), implement
the three `_fetch_*` functions against those models — the HTTP contract stays
identical.
"""

import logging
from functools import wraps

from django.core.cache import cache
from django.http import HttpResponseForbidden, JsonResponse

from esi.clients import EsiClientProvider
from esi.models import Token

from . import app_settings, data_sources
from .signing import verify

logger = logging.getLogger(__name__)

esi = EsiClientProvider(app_info_text="industrysite")

# Scope required to read each dataset.
SCOPE_ASSETS = "esi-assets.read_assets.v1"
SCOPE_JOBS = "esi-industry.read_character_jobs.v1"
SCOPE_SKILLS = "esi-skills.read_skills.v1"


def require_signature(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        timestamp = request.headers.get("X-AA-Timestamp", "")
        signature = request.headers.get("X-AA-Signature", "")
        if not verify(timestamp, request.get_full_path(), signature):
            return HttpResponseForbidden("invalid signature")
        return view(request, *args, **kwargs)

    return wrapper


def _valid_token(character_id: int, scope: str):
    return (
        Token.objects.filter(character_id=character_id, scopes__name=scope)
        .require_valid()
        .first()
    )


def _cache_key(character_id: int, kind: str) -> str:
    return f"industrysite:pull:{kind}:{character_id}"


def _respond(character_id: int, kind: str, scope: str, cached_source, esi_fetch):
    key = _cache_key(character_id, kind)
    data = cache.get(key)

    if data is None:
        # 1) Member Audit / CorpTools cached tables (zero ESI calls).
        try:
            data = cached_source(character_id)
        except Exception:  # pragma: no cover - defensive
            logger.exception("industrysite cached %s failed for %s", kind, character_id)
            data = None

        # 2) Fall back to a live ESI call using the token AA holds.
        if data is None:
            token = _valid_token(character_id, scope)
            if token is None:
                return JsonResponse(
                    {"character_id": character_id, "error": "no_valid_token", "scope": scope},
                    status=404,
                )
            try:
                data = esi_fetch(character_id, token)
            except Exception as exc:  # pragma: no cover - upstream/ESI failure
                logger.exception("industrysite pull %s failed for %s", kind, character_id)
                return JsonResponse(
                    {"character_id": character_id, "error": "esi_error", "detail": str(exc)},
                    status=502,
                )

        cache.set(key, data, app_settings.INDUSTRYSITE_PULL_CACHE)

    return JsonResponse({"character_id": character_id, kind: data})


def _fetch_assets(character_id, token):
    return esi.client.Assets.get_characters_character_id_assets(
        character_id=character_id, token=token.valid_access_token()
    ).results()


def _fetch_industry_jobs(character_id, token):
    return esi.client.Industry.get_characters_character_id_industry_jobs(
        character_id=character_id,
        include_completed=True,
        token=token.valid_access_token(),
    ).results()


def _fetch_skills(character_id, token):
    return esi.client.Skills.get_characters_character_id_skills(
        character_id=character_id, token=token.valid_access_token()
    ).result()


@require_signature
def character_assets(request, character_id):
    return _respond(character_id, "assets", SCOPE_ASSETS, data_sources.assets, _fetch_assets)


@require_signature
def character_industry_jobs(request, character_id):
    return _respond(
        character_id, "industry_jobs", SCOPE_JOBS, data_sources.industry_jobs, _fetch_industry_jobs
    )


@require_signature
def character_skills(request, character_id):
    return _respond(character_id, "skills", SCOPE_SKILLS, data_sources.skills, _fetch_skills)
