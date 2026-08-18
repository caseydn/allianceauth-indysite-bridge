"""Cached data sources for the pull API.

Reads a character's assets / skills / industry jobs from **Member Audit** first,
then **CorpTools**, so the industrial site gets data with zero ESI calls when
either app already has it. Anything not found here returns None and the provider
falls back to a live django-esi call.

Everything is normalized to the same shape CCP ESI returns, so the industrial
site parses one format regardless of source.

Field access is defensive (getattr / try-except imports): if an app isn't
installed, or a field name differs on your installed version, that source is
skipped rather than crashing. Confirm the mappings on your versions with:

    python manage.py shell -c "from industrysite.data_sources import self_test; self_test(CHARACTER_ID)"
"""

import logging

logger = logging.getLogger(__name__)


def _num(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------------------- #
# Member Audit
# --------------------------------------------------------------------------- #
def _ma_character(character_id):
    try:
        from memberaudit.models import Character as MaCharacter
    except Exception:
        return None
    qs = MaCharacter.objects.all()
    # Support both the current (eve_character) and older
    # (character_ownership.character) schemas.
    for lookup in ("eve_character__character_id", "character_ownership__character__character_id"):
        try:
            obj = qs.filter(**{lookup: character_id}).first()
        except Exception:
            obj = None
        if obj is not None:
            return obj
    return None


def _ma_assets(character_id):
    char = _ma_character(character_id)
    if char is None:
        return None
    try:
        from memberaudit.models import CharacterAsset
    except Exception:
        return None
    rows = list(CharacterAsset.objects.filter(character=char))
    if not rows:
        return None
    out = []
    for a in rows:
        out.append(
            {
                "item_id": _num(getattr(a, "item_id", None), None),
                "type_id": _num(getattr(a, "eve_type_id", None), None),
                "location_id": _num(getattr(a, "location_id", None), None),
                "location_flag": getattr(a, "location_flag", "") or "",
                "location_type": getattr(a, "location_type", "") or "",
                "quantity": _num(getattr(a, "quantity", 1), 1),
                "is_singleton": bool(getattr(a, "is_singleton", False)),
                "is_blueprint_copy": bool(getattr(a, "is_blueprint_copy", False)),
            }
        )
    return out


def _ma_skills(character_id):
    char = _ma_character(character_id)
    if char is None:
        return None
    try:
        from memberaudit.models import CharacterSkill
    except Exception:
        return None
    rows = list(CharacterSkill.objects.filter(character=char))
    if not rows:
        return None
    skills = [
        {
            "skill_id": _num(getattr(s, "eve_type_id", None), None),
            "active_skill_level": _num(getattr(s, "active_skill_level", 0)),
            "trained_skill_level": _num(getattr(s, "trained_skill_level", 0)),
            "skillpoints_in_skill": _num(getattr(s, "skillpoints_in_skill", 0)),
        }
        for s in rows
    ]
    return {
        "skills": skills,
        "total_sp": sum(x["skillpoints_in_skill"] for x in skills),
    }


def _ma_industry_jobs(character_id):
    char = _ma_character(character_id)
    if char is None:
        return None
    try:
        from memberaudit.models import CharacterIndustryJob
    except Exception:
        return None
    rows = list(CharacterIndustryJob.objects.filter(character=char))
    if not rows:
        return None
    return [_industry_job_row(j) for j in rows]


def _ir_planets(character_id):
    """Planetary Interaction colonies from the industry_reforged plugin
    (CharacterPlanet + PlanetPin). Returns each colony with its FULL pin layout:
    extractors (install/expiry/cycle/yield), factories (schematic/product) and
    storage (contents/capacity). No ESI — reads industry_reforged's stored data.
    """
    try:
        from industry_reforged.models import CharacterPlanet
    except Exception:
        return None
    try:
        rows = list(
            CharacterPlanet.objects.filter(character__character_id=character_id)
            .select_related("eve_planet", "eve_system", "planet_type")
            .prefetch_related("pins", "pins__type", "pins__product_type")
        )
    except Exception:
        logger.exception("industry_reforged CharacterPlanet query failed")
        return None
    if not rows:
        return None

    out = []
    for p in rows:
        planet = getattr(p, "eve_planet", None)
        system = getattr(p, "eve_system", None)
        ptype = getattr(p, "planet_type", None)

        pins = []
        try:
            pin_rows = list(p.pins.all())
        except Exception:
            pin_rows = []
        for pin in pin_rows:
            pins.append(
                {
                    "pin_id": _num(getattr(pin, "pin_id", None), None),
                    "type_id": _num(getattr(pin, "type_id", None), None),
                    "type_name": getattr(getattr(pin, "type", None), "name", None),
                    "product_type_id": _num(getattr(pin, "product_type_id", None), None),
                    "product_type_name": getattr(getattr(pin, "product_type", None), "name", None),
                    "schematic_id": _num(getattr(pin, "schematic_id", None), None),
                    "install_time": _iso(getattr(pin, "install_time", None)),
                    "expiry_time": _iso(getattr(pin, "expiry_time", None)),
                    "last_cycle_start": _iso(getattr(pin, "last_cycle_start", None)),
                    "cycle_time": _num(getattr(pin, "cycle_time", None), None),
                    "extraction_yield": _float(getattr(pin, "extraction_yield", None)),
                    "capacity": _float(getattr(pin, "capacity", None)),
                    "contents_volume": _float(getattr(pin, "contents_volume", None)),
                    "contents": getattr(pin, "contents", None),
                }
            )

        out.append(
            {
                "planet_id": _num(getattr(p, "planet_id", None), None),
                "planet_name": getattr(planet, "name", None),
                "planet_type_id": _num(getattr(p, "planet_type_id", None), None)
                or _num(getattr(ptype, "id", None), None),
                "planet_type_name": getattr(ptype, "name", None),
                "system_id": _num(getattr(p, "system_id", None), None)
                or _num(getattr(system, "id", None), None),
                "system_name": getattr(system, "name", None),
                "upgrade_level": _num(getattr(p, "upgrade_level", None), None),
                "num_pins": _num(getattr(p, "num_pins", None), None),
                "last_update": _iso(getattr(p, "last_update", None)),
                "pins": pins,
            }
        )
    return out


# --------------------------------------------------------------------------- #
# CorpTools
# --------------------------------------------------------------------------- #
def _ct_character(character_id):
    try:
        from corptools.models import CharacterAudit
    except Exception:
        return None
    try:
        return CharacterAudit.objects.filter(character__character_id=character_id).first()
    except Exception:
        return None


def _ct_assets(character_id):
    audit = _ct_character(character_id)
    if audit is None:
        return None
    try:
        from corptools.models import CharacterAsset
    except Exception:
        return None
    rows = list(CharacterAsset.objects.filter(character=audit))
    if not rows:
        return None
    out = []
    for a in rows:
        # CorpTools stores the type via a `type_name` FK (id == type_id).
        type_id = getattr(a, "type_name_id", None)
        out.append(
            {
                "item_id": _num(getattr(a, "item_id", None), None),
                "type_id": _num(type_id, None),
                "location_id": _num(getattr(a, "location_id", None), None),
                "location_flag": getattr(a, "location_flag", "") or "",
                "location_type": getattr(a, "location_type", "") or "",
                "quantity": _num(getattr(a, "quantity", 1), 1),
                "is_singleton": bool(getattr(a, "is_singleton", False)),
                "is_blueprint_copy": bool(getattr(a, "is_blueprint_copy", False)),
            }
        )
    return out


def _ct_skills(character_id):
    audit = _ct_character(character_id)
    if audit is None:
        return None
    try:
        from corptools.models import Skill
    except Exception:
        return None
    rows = list(Skill.objects.filter(character=audit))
    if not rows:
        return None
    skills = [
        {
            "skill_id": _num(getattr(s, "skill_id", None) or getattr(s, "skill_name_id", None), None),
            "active_skill_level": _num(getattr(s, "active_skill_level", 0)),
            "trained_skill_level": _num(getattr(s, "trained_skill_level", 0)),
            "skillpoints_in_skill": _num(getattr(s, "skillpoints_in_skill", 0)),
        }
        for s in rows
    ]
    return {
        "skills": skills,
        "total_sp": sum(x["skillpoints_in_skill"] for x in skills),
    }


def _ct_industry_jobs(character_id):
    audit = _ct_character(character_id)
    if audit is None:
        return None
    try:
        from corptools.models import CharacterIndustryJob
    except Exception:
        return None
    try:
        rows = list(CharacterIndustryJob.objects.filter(character=audit))
    except Exception:
        return None
    if not rows:
        return None
    return [_industry_job_row(j) for j in rows]


def _industry_job_row(j):
    def _fk(obj, name):
        return getattr(obj, name + "_id", None)

    return {
        "job_id": _num(getattr(j, "job_id", None), None),
        "activity_id": _num(getattr(j, "activity_id", None), None),
        "blueprint_type_id": _num(_fk(j, "blueprint_type") or getattr(j, "blueprint_type_id", None), None),
        "product_type_id": _num(_fk(j, "product_type") or getattr(j, "product_type_id", None), None),
        "status": getattr(j, "status", "") or "",
        "runs": _num(getattr(j, "runs", 0)),
        "start_date": _iso(getattr(j, "start_date", None)),
        "end_date": _iso(getattr(j, "end_date", None)),
        "facility_id": _num(getattr(j, "facility_id", None), None),
    }


def _iso(value):
    try:
        return value.isoformat() if value else None
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# Public API: try Member Audit, then CorpTools
# --------------------------------------------------------------------------- #
def assets(character_id):
    return _first(character_id, _ma_assets, _ct_assets)


def skills(character_id):
    return _first(character_id, _ma_skills, _ct_skills)


def industry_jobs(character_id):
    return _first(character_id, _ma_industry_jobs, _ct_industry_jobs)


def planets(character_id):
    return _safe(_ir_planets, character_id)


def _first(character_id, *sources):
    for source in sources:
        try:
            data = source(character_id)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("industrysite data source %s failed: %s", source.__name__, exc)
            data = None
        if data:
            return data
    return None


def _count(data):
    if data is None:
        return 0
    if isinstance(data, dict):
        return len(data.get("skills", []))
    return len(data)


def _safe(fn, character_id):
    try:
        return fn(character_id)
    except Exception:  # pragma: no cover - defensive
        return None


def describe(character_id):
    """Report, per dataset, which AA source holds the data and how many rows.

    Used by the admin "Data preview" page so you can see exactly what the plugin
    would serve the industrial site for a character. Never calls ESI.
    """

    def probe(ma_fn, ct_fn):
        data = _safe(ma_fn, character_id)
        if data:
            return {"source": "Member Audit", "count": _count(data)}
        data = _safe(ct_fn, character_id)
        if data:
            return {"source": "CorpTools", "count": _count(data)}
        return {"source": None, "count": 0}

    return {
        "assets": probe(_ma_assets, _ct_assets),
        "skills": probe(_ma_skills, _ct_skills),
        "industry_jobs": probe(_ma_industry_jobs, _ct_industry_jobs),
        "planets": probe(_ir_planets, lambda _cid: None),
    }


def locations(ids):
    """Resolve station/structure location ids -> names from Member Audit's Location
    table (Member Audit already resolves NPC stations AND player structures). Bulk.
    Returns a list of {location_id, name, system_id, system_name, type_id}, or None
    if Member Audit isn't installed.
    """
    ids = [i for i in (_num(x) for x in ids) if i]
    if not ids:
        return []
    try:
        from memberaudit.models import Location
    except Exception:
        return None
    try:
        qs = Location.objects.filter(id__in=ids).select_related("eve_solar_system", "eve_type")
    except Exception:
        logger.exception("memberaudit Location query failed")
        return None

    out = []
    for loc in qs:
        system = getattr(loc, "eve_solar_system", None)
        out.append(
            {
                "location_id": _num(getattr(loc, "id", None)),
                "name": getattr(loc, "name", None),
                "system_id": _num(getattr(system, "id", None)),
                "system_name": getattr(system, "name", None),
                "type_id": _num(getattr(loc, "eve_type_id", None)),
            }
        )
    return out


def self_test(character_id):
    """Print what each source resolves for a character. Run from manage.py shell."""
    for name, fn in (("assets", assets), ("skills", skills), ("industry_jobs", industry_jobs)):
        try:
            data = fn(character_id)
        except Exception as exc:
            print(f"{name}: ERROR {exc}")
            continue
        if data is None:
            print(f"{name}: no cached source (will use live ESI fallback)")
        elif isinstance(data, dict):
            print(f"{name}: {len(data.get('skills', []))} rows from cache")
        else:
            print(f"{name}: {len(data)} rows from cache")
