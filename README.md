# allianceauth-industrysite

An **Alliance Auth service module**. A member clicks **Activate** on their AA
**Services** page (just like the Discord service) and Alliance Auth pushes their
characters, ESI scope status, corp/alliance affiliation and group memberships to
the **Ore Build Profit** industrial site. Group changes re-push automatically;
**Deactivate** unlinks them on the site.

It also serves an HMAC-authenticated **pull API** so the industrial site can read
character **assets / industry jobs / skills** from Alliance Auth (using Member
Audit / CorpTools cached data when available, else live ESI) instead of calling
CCP itself — moving the ESI load off the industrial site.

---

## Install (commands only)

On the Alliance Auth server, as the `allianceserver` user, inside the AA venv:

```bash
sudo su - allianceserver
source /home/allianceserver/venv/auth/bin/activate      # adjust to your venv path

# Install straight from GitHub (replace CHANGEME with your GitHub user/org):
pip install git+https://github.com/caseydn/allianceauth-indysite-bridge.git

# ...or, once published to PyPI:
# pip install allianceauth-industrysite
```

Add the app + settings to `myauth/settings/local.py`:

```python
INSTALLED_APPS += [
    "industrysite",
]

# --- Industry Site service ---
INDUSTRYSITE_URL = "https://orebuildprofit.com"          # industrial site base URL
INDUSTRYSITE_SHARED_KEY = "PUT-A-LONG-RANDOM-SECRET-HERE" # must equal the site's AA_SHARED_KEY
INDUSTRYSITE_AUTH_TTL = 120
INDUSTRYSITE_TIMEOUT = 20
INDUSTRYSITE_TAG = "Industry Site"
INDUSTRYSITE_PULL_CACHE = 300
```

Generate the shared key once (use the SAME value on both systems):

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Migrate, collect static, restart:

```bash
cd /home/allianceserver/myauth
python manage.py migrate industrysite
python manage.py collectstatic --noinput
python manage.py check
exit
sudo supervisorctl restart myauth:
```

Upgrade later with:

```bash
sudo su - allianceserver
source /home/allianceserver/venv/auth/bin/activate
pip install --upgrade git+https://github.com/caseydn/allianceauth-indysite-bridge.git
cd /home/allianceserver/myauth && python manage.py migrate && python manage.py collectstatic --noinput
exit
sudo supervisorctl restart myauth:
```

## Grant access

Users only see *Industry Site* if they hold
`industrysite | Industry Site account | Can access the Industry Site service`.
Grant it to a **State** (e.g. Member) or a **Group** in the AA admin
(Authentication → States/Groups → Permissions).

## Publishing to PyPI (optional, from your dev machine)

```bash
pip install build twine
python -m build
twine upload dist/*
```

## Pull API data source

AA is **not** an ESI gateway. `provider.py` serves assets / industry jobs / skills
by reading data Alliance Auth **already stores** — **Member Audit** first, then
**CorpTools** — kept fresh by AA's own schedules. It **never calls CCP ESI**. If a
character isn't audited/synced in AA yet, the endpoint returns 404 and the
industrial site handles it on its side. Field mappings live in `data_sources.py`;
verify them against your installed versions with:

```bash
python manage.py shell -c "from industrysite.data_sources import self_test; self_test(CHARACTER_ID)"
```

## Uninstall

```bash
python manage.py migrate industrysite zero
pip uninstall allianceauth-industrysite
# remove "industrysite" from INSTALLED_APPS, then restart supervisor
```
