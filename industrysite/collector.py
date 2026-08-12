"""Collect the data Alliance Auth already holds for a user and shape it into
the payload the industrial site ingests. Uses only AA core models
(CharacterOwnership, EveCharacter, UserProfile) and django-esi Tokens, so it
works on any AA install regardless of which audit apps are present.
"""

import logging

from allianceauth.authentication.models import CharacterOwnership
from esi.models import Token

logger = logging.getLogger(__name__)


def _int_or_none(value):
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def granted_scopes_by_character(user) -> dict:
    """Map character_id -> sorted list of granted ESI scope names for the user."""
    scopes = {}
    for token in Token.objects.filter(user=user).prefetch_related("scopes"):
        cid = _int_or_none(token.character_id)
        if cid is None:
            continue
        bucket = scopes.setdefault(cid, set())
        for scope in token.scopes.all():
            bucket.add(scope.name)
    return {cid: sorted(names) for cid, names in scopes.items()}


def build_user_payload(user) -> dict:
    """Full snapshot of a user's identity/characters/roles for the site."""
    try:
        main = user.profile.main_character
    except Exception:  # pragma: no cover - profile always exists in practice
        main = None
    main_id = _int_or_none(main.character_id) if main else None

    scopes = granted_scopes_by_character(user)

    characters = []
    ownerships = CharacterOwnership.objects.filter(user=user).select_related("character")
    for ownership in ownerships:
        ch = ownership.character
        cid = _int_or_none(ch.character_id)
        if cid is None:
            continue
        characters.append(
            {
                "character_id": cid,
                "name": ch.character_name,
                "corporation_id": _int_or_none(ch.corporation_id),
                "corporation_name": ch.corporation_name or "",
                "corporation_ticker": ch.corporation_ticker or "",
                "alliance_id": _int_or_none(ch.alliance_id),
                "alliance_name": ch.alliance_name or "",
                "alliance_ticker": ch.alliance_ticker or "",
                "is_main": bool(main_id is not None and cid == main_id),
                "granted_scopes": scopes.get(cid, []),
            }
        )

    state = ""
    try:
        state = user.profile.state.name
    except Exception:  # pragma: no cover
        state = ""

    return {
        "aa_user_id": user.id,
        "username": user.username,
        "main_character_id": main_id,
        "state": state,
        "groups": sorted(g.name for g in user.groups.all()),
        "characters": characters,
    }
