"""Shared HMAC signing helpers used by both directions of traffic:

  * push (AA -> site): AA signs the request body.
  * pull (site -> AA): the site signs the request path; AA verifies here.

Scheme (identical on the Laravel side):

    message   = f"{timestamp}.{payload}"
    signature = hex( HMAC_SHA256(shared_key, message) )

where `payload` is the exact raw request body for POSTs, or the full request
path (path + query string) for GETs. Requests older than the TTL are rejected
to bound replay.
"""

import hashlib
import hmac
import time

from . import app_settings


def sign(timestamp: str, payload: str) -> str:
    key = app_settings.INDUSTRYSITE_SHARED_KEY.encode()
    message = f"{timestamp}.{payload}".encode()
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def verify(timestamp: str, payload: str, signature: str) -> bool:
    if not app_settings.INDUSTRYSITE_SHARED_KEY or not timestamp or not signature:
        return False
    try:
        if abs(time.time() - int(timestamp)) > app_settings.INDUSTRYSITE_AUTH_TTL:
            return False
    except (TypeError, ValueError):
        return False
    return hmac.compare_digest(sign(timestamp, payload), signature)
