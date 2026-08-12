"""Industry Site service module for Alliance Auth.

Registers an Alliance Auth *service* (like the Discord service) named
"Industry Site". A user activates it from their AA Services page; on
activation AA pushes that user's characters, ESI scope status,
corp/alliance affiliation and group memberships to the Ore Build Profit
industrial site. Group changes re-push automatically; deactivating unlinks
the user on the site.

It also exposes a small HMAC-authenticated pull API so the industrial site
can read character assets / industry jobs / skills from Alliance Auth
instead of calling CCP ESI itself (ESI offload).
"""

__version__ = "1.0.3"
