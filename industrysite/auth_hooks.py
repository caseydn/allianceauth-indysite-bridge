from allianceauth import hooks
from allianceauth.services.hooks import UrlHook

from . import urls
from .services import IndustrySiteService


@hooks.register("services_hook")
def register_service():
    return IndustrySiteService()


@hooks.register("url_hook")
def register_urls():
    # Mounts urls.py under /industrysite/ with the "industrysite" namespace.
    return UrlHook(urls, "industrysite", r"^industrysite/")
