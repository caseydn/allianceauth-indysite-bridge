"""HTTP client that pushes user data to the industrial site. Kept free of
Django/AA specifics so it is easy to test and reuse: callers pass in a ready
payload dict and (optionally) the per-user token.
"""

import json
import logging
import time

import requests

from . import app_settings
from .signing import sign

logger = logging.getLogger(__name__)


class IndustrySiteError(Exception):
    pass


class IndustrySiteManager:
    @staticmethod
    def _canonical(payload: dict) -> str:
        # Deterministic body so the signature matches the bytes on the wire.
        return json.dumps(payload, separators=(",", ":"), sort_keys=True)

    @classmethod
    def _post(cls, path: str, payload: dict, user_token: str = "") -> dict:
        if not app_settings.is_configured():
            raise IndustrySiteError(
                "INDUSTRYSITE_URL / INDUSTRYSITE_SHARED_KEY are not configured"
            )
        body = cls._canonical(payload)
        timestamp = str(int(time.time()))
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-AA-Timestamp": timestamp,
            "X-AA-Signature": sign(timestamp, body),
        }
        if user_token:
            headers["X-AA-User-Token"] = user_token

        url = f"{app_settings.INDUSTRYSITE_URL}{path}"
        response = requests.post(
            url, data=body, headers=headers, timeout=app_settings.INDUSTRYSITE_TIMEOUT
        )
        response.raise_for_status()
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError:
            return {}

    @classmethod
    def activate_user(cls, payload: dict) -> dict:
        """First push; the site creates/links the user and returns a token."""
        return cls._post("/api/aa/activate", payload)

    @classmethod
    def update_user(cls, payload: dict, user_token: str = "") -> dict:
        return cls._post("/api/aa/update", payload, user_token=user_token)

    @classmethod
    def deactivate_user(cls, payload: dict, user_token: str = "") -> dict:
        return cls._post("/api/aa/deactivate", payload, user_token=user_token)
