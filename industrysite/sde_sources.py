"""SDE (Static Data Export) readers.

Alliance Auth keeps the full SDE in its own database (django-eveuniverse, used by
Member Audit, and/or CorpTools' SDE), auto-updated on AA's schedule. These readers
serve that already-stored SDE to the industrial site so the site can drop its own
SDE import. Nothing here calls ESI.

Defensive by design (try-imports + getattr): if a package/model/field differs on
your installed versions, that reader degrades to None instead of crashing. Confirm
against your install with:

    python manage.py shell -c "from industrysite.sde_sources import self_test; self_test(34)"
"""

import logging

logger = logging.getLogger(__name__)

# EVE industry activity id for Manufacturing.
ACTIVITY_MANUFACTURING = 1


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------- #
# django-eveuniverse (preferred — richest SDE)
# --------------------------------------------------------------------------- #
def _eu():
    try:
        import eveuniverse.models as models

        return models
    except Exception:
        return None


def _eu_type_info(type_id):
    m = _eu()
    if not m:
        return None
    try:
        t = (
            m.EveType.objects.select_related(
                "eve_group", "eve_group__eve_category", "eve_market_group"
            )
            .filter(id=type_id)
            .first()
        )
    except Exception:
        t = None
    if not t:
        return None
    group = getattr(t, "eve_group", None)
    category = getattr(group, "eve_category", None) if group else None
    return {
        "type_id": t.id,
        "name": t.name,
        "group_id": getattr(group, "id", None),
        "group_name": getattr(group, "name", None),
        "category_id": getattr(category, "id", None),
        "category_name": getattr(category, "name", None),
        "market_group_id": getattr(getattr(t, "eve_market_group", None), "id", None),
        "volume": getattr(t, "volume", None),
        "packaged_volume": getattr(t, "packaged_volume", None),
        "published": bool(getattr(t, "published", False)),
    }


def _eu_type_materials(type_id):
    m = _eu()
    if not m or not hasattr(m, "EveTypeMaterial"):
        return None
    try:
        rows = list(m.EveTypeMaterial.objects.filter(eve_type_id=type_id))
    except Exception:
        return None
    if not rows:
        return None
    return [
        {
            "material_type_id": _int(getattr(r, "material_eve_type_id", None)),
            "quantity": _int(getattr(r, "quantity", 0)) or 0,
        }
        for r in rows
    ]


def _eu_blueprint(type_id):
    m = _eu()
    if not m:
        return None
    Mat = getattr(m, "EveIndustryActivityMaterial", None)
    Prod = getattr(m, "EveIndustryActivityProduct", None)
    if not Mat or not Prod:
        return None

    def _rows(model):
        try:
            return list(model.objects.filter(eve_type_id=type_id, activity_id=ACTIVITY_MANUFACTURING))
        except Exception:
            try:
                return list(model.objects.filter(eve_type_id=type_id))
            except Exception:
                return []

    mats = _rows(Mat)
    prods = _rows(Prod)
    if not mats and not prods:
        return None
    return {
        "blueprint_type_id": type_id,
        "products": [
            {
                "type_id": _int(getattr(p, "product_eve_type_id", None)),
                "quantity": _int(getattr(p, "quantity", 1)) or 1,
            }
            for p in prods
        ],
        "materials": [
            {
                "type_id": _int(getattr(x, "material_eve_type_id", None)),
                "quantity": _int(getattr(x, "quantity", 0)) or 0,
            }
            for x in mats
        ],
    }


# --------------------------------------------------------------------------- #
# CorpTools SDE (fallback — mainly type names)
# --------------------------------------------------------------------------- #
def _ct_type_model():
    try:
        from corptools.models import EveItemType

        return EveItemType
    except Exception:
        return None


def _ct_type_info(type_id):
    model = _ct_type_model()
    if not model:
        return None
    try:
        t = model.objects.filter(type_id=type_id).first()
    except Exception:
        t = None
    if not t:
        return None
    group = getattr(t, "group", None)
    return {
        "type_id": _int(getattr(t, "type_id", type_id)),
        "name": getattr(t, "name", None),
        "group_id": _int(getattr(group, "group_id", None)) if group else None,
        "group_name": getattr(group, "name", None) if group else None,
        "category_id": None,
        "category_name": None,
        "market_group_id": None,
        "volume": getattr(t, "volume", None),
        "packaged_volume": None,
        "published": bool(getattr(t, "published", True)),
    }


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def type_info(type_id):
    return _eu_type_info(type_id) or _ct_type_info(type_id)


def types_bulk(ids):
    """Resolve many type_ids -> name in one go. Returns {type_id: name}."""
    ids = [i for i in (_int(x) for x in ids) if i]
    out = {}
    m = _eu()
    if m:
        try:
            for tid, name in m.EveType.objects.filter(id__in=ids).values_list("id", "name"):
                out[tid] = name
        except Exception:
            logger.debug("eveuniverse bulk type resolve failed", exc_info=True)
    missing = [i for i in ids if i not in out]
    if missing:
        model = _ct_type_model()
        if model:
            try:
                for tid, name in model.objects.filter(type_id__in=missing).values_list("type_id", "name"):
                    out[_int(tid)] = name
            except Exception:
                logger.debug("corptools bulk type resolve failed", exc_info=True)
    return out


def type_materials(type_id):
    """Reprocessing / refine materials for a type. eveuniverse only."""
    return _eu_type_materials(type_id)


def blueprint(type_id):
    """Manufacturing BOM (materials + product) for a blueprint type. eveuniverse only."""
    return _eu_blueprint(type_id)


def status():
    """Which SDE sources are importable — shown on the admin data-preview page."""
    return {
        "eveuniverse": _eu() is not None,
        "corptools_sde": _ct_type_model() is not None,
    }


def self_test(type_id=34):
    """Print what each SDE reader resolves for a type. Run from manage.py shell.

    34 = Tritanium. Try a blueprint type id too (e.g. a ship BPO).
    """
    print("SDE sources importable:", status())
    info = type_info(type_id)
    print("type_info:", info)
    mats = type_materials(type_id)
    print("type_materials rows:", len(mats) if mats else 0)
    bp = blueprint(type_id)
    if bp:
        print(f"blueprint: {len(bp['materials'])} materials, {len(bp['products'])} product(s)")
    else:
        print("blueprint: none (not a blueprint type, or industry SDE not loaded)")
    print("bulk resolve:", types_bulk([34, 35, type_id]))
