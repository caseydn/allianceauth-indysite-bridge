"""Settings for the Industry Site service, read from Alliance Auth's
settings (add these to myauth/settings/local.py):

    INSTALLED_APPS += ["industrysite"]
    INDUSTRYSITE_URL = "https://orebuildprofit.com"   # industrial site base URL
    INDUSTRYSITE_SHARED_KEY = "<same value as the site's AA_SHARED_KEY>"
    INDUSTRYSITE_AUTH_TTL = 120                        # signature replay window (s)
    INDUSTRYSITE_TIMEOUT = 20                          # HTTP timeout (s)
    INDUSTRYSITE_TAG = "Industry Site"                 # label on the Services page
"""

from django.conf import settings


def _get(name, default=None):
    return getattr(settings, name, default)


INDUSTRYSITE_URL = str(_get("INDUSTRYSITE_URL", "")).rstrip("/")
INDUSTRYSITE_SHARED_KEY = str(_get("INDUSTRYSITE_SHARED_KEY", ""))
INDUSTRYSITE_AUTH_TTL = int(_get("INDUSTRYSITE_AUTH_TTL", 120))
INDUSTRYSITE_TIMEOUT = int(_get("INDUSTRYSITE_TIMEOUT", 20))
INDUSTRYSITE_TAG = str(_get("INDUSTRYSITE_TAG", "Industry Site"))
# How long AA may cache a pull-API response before re-fetching from ESI (s).
INDUSTRYSITE_PULL_CACHE = int(_get("INDUSTRYSITE_PULL_CACHE", 300))


def is_configured() -> bool:
    return bool(INDUSTRYSITE_URL and INDUSTRYSITE_SHARED_KEY)
