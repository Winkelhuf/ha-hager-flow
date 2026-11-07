"""myHager-Login für die Hager flow Cloud.

Der Ablauf (SAML über login.hager.com, Token am Ende in der Redirect-URL) ist aus
dem Projekt "Hager Local" von hebrru übernommen und leicht gekürzt:
https://github.com/hebrru/Hager-local – MIT License, Copyright (c) 2026 hebrru.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import html as html_module
import json
import re
from urllib.parse import parse_qs, urljoin, urlparse

from aiohttp import ClientError, ClientSession, CookieJar

from .const import FLOW_LOGIN_URL, USER_AGENT
from .errors import HagerCloudAuthError, HagerCloudConnectionError

LOGIN_URL_RE = re.compile(
    r"https://login\.hager\.com/interaction/v2/[^\"' <&]+/login\?client_id=[A-Za-z0-9_-]+"
)
FORM_TAG_RE = re.compile(r"<form\b[^>]*>", re.IGNORECASE)
INPUT_TAG_RE = re.compile(r"<input\b[^>]*>", re.IGNORECASE)
ANCHOR_HREF_RE = re.compile(r"""<a\b[^>]*href=[\"']([^\"']+)[\"']""", re.IGNORECASE)
META_REFRESH_RE = re.compile(
    r"""<meta\b[^>]*http-equiv=[\"']refresh[\"'][^>]*content=[\"'][^\"']*url=([^\"'>]+)""",
    re.IGNORECASE,
)
JS_REDIRECT_RE = re.compile(
    r"""location(?:\.href)?\s*=\s*[\"']([^\"']+)[\"']|location\.(?:replace|assign)\(\s*[\"']([^\"']+)[\"']""",
    re.IGNORECASE,
)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b.*?</\1>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
URL_RE = re.compile(r"https?://[^\s\"'<>]+")
SECRETISH_RE = re.compile(r"[A-Za-z0-9_\-.=+/]{40,}")
_REDIRECTS = (301, 302, 303, 307, 308)


@dataclass(slots=True)
class CloudTokens:
    """Token-Paar aus dem Login bzw. dem Re-Auth."""

    access_token: str
    reauth_token: str


@dataclass(slots=True)
class _RawCookie:
    name: str
    value: str
    domain: str
    path: str


def token_expiry(access_token: str | None) -> float | None:
    """Ablaufzeitpunkt (exp) eines JWT, ohne Signaturprüfung."""
    if not access_token:
        return None
    try:
        payload = access_token.split(".")[1]
        decoded = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
        exp = json.loads(decoded).get("exp")
        return float(exp) if exp is not None else None
    except (IndexError, ValueError, TypeError):
        return None


def _tokens_from_url(url: str) -> CloudTokens | None:
    query = parse_qs(urlparse(url).query)
    access, reauth = query.get("token", [None])[0], query.get("reAuthToken", [None])[0]
    return CloudTokens(access, reauth) if access and reauth else None


def _default_cookie_path(path: str) -> str:
    if not path or not path.startswith("/") or path == "/":
        return "/"
    if path.endswith("/"):
        return path
    return path.rsplit("/", 1)[0] or "/"


def _store_raw_cookies(url: str, headers: list[str], jar: dict[tuple[str, str, str], _RawCookie]) -> None:
    """Cookies roh speichern – aiohttp normalisiert manche Werte von login.hager.com kaputt."""
    parsed = urlparse(url)
    default_domain = (parsed.hostname or "").casefold()
    default_path = _default_cookie_path(parsed.path)
    for header in headers:
        first, _, rest = header.partition(";")
        name, sep, value = first.partition("=")
        if not sep:
            continue
        domain, path = default_domain, default_path
        for attribute in rest.split(";"):
            attribute = attribute.strip()
            lower = attribute.casefold()
            if lower.startswith("domain="):
                domain = attribute[7:].strip().lstrip(".").casefold()
            elif lower.startswith("path="):
                path = attribute[5:].strip() or "/"
        key = (domain, path, name.strip())
        if value == "":
            jar.pop(key, None)
        else:
            jar[key] = _RawCookie(name.strip(), value, domain, path)


def _cookie_matches(cookie: _RawCookie, url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").casefold()
    domain_ok = host == cookie.domain or host.endswith(f".{cookie.domain}")
    return domain_ok and (parsed.path or "/").startswith(cookie.path)


def _cookie_header(session: ClientSession, url: str, jar: dict[tuple[str, str, str], _RawCookie]) -> dict[str, str]:
    values: dict[str, str] = {}
    for morsel in session.cookie_jar:
        cookie = _RawCookie(
            morsel.key, morsel.value, (morsel["domain"] or "").lstrip(".").casefold(), morsel["path"] or "/"
        )
        if _cookie_matches(cookie, url):
            values[morsel.key] = morsel.value
    for cookie in jar.values():
        if _cookie_matches(cookie, url):
            values[cookie.name] = cookie.value
    return {"Cookie": "; ".join(f"{k}={v}" for k, v in values.items())} if values else {}


def _html_attribute(tag: str, attribute: str) -> str | None:
    match = re.search(rf"""\b{re.escape(attribute)}\s*=\s*[\"']([^\"']*)[\"']""", tag, re.IGNORECASE)
    return html_module.unescape(match.group(1)) if match else None


def _auto_post_form(body: str) -> tuple[str, dict[str, str]] | None:
    decoded = html_module.unescape(body)
    form = FORM_TAG_RE.search(decoded)
    if not form:
        return None
    method = (_html_attribute(form.group(0), "method") or "get").casefold()
    action = _html_attribute(form.group(0), "action")
    if not action or (method != "post" and "samlresponse" not in decoded.casefold()):
        return None
    fields: dict[str, str] = {}
    for tag in INPUT_TAG_RE.finditer(decoded):
        name = _html_attribute(tag.group(0), "name")
        kind = (_html_attribute(tag.group(0), "type") or "text").casefold()
        if name and kind not in {"submit", "button", "image", "reset"}:
            fields[name] = _html_attribute(tag.group(0), "value") or ""
    return action, fields


def _html_redirect(body: str) -> str | None:
    decoded = html_module.unescape(body)
    for pattern in (META_REFRESH_RE, JS_REDIRECT_RE, ANCHOR_HREF_RE):
        if match := pattern.search(decoded):
            return html_module.unescape(next(g for g in match.groups() if g))
    return None



# SAML-Antwort, die erst per JavaScript als Formular abgeschickt wird
# (Keycloak-Seite auth.hagerenergy.com/.../after-post-broker-login)
def _js_value(body: str, *names: str) -> str | None:
    """Wert eines Feldes aus einem Skript (JSON oder JS-Objekt), JS-Escapes aufgelöst."""
    for name in names:
        pattern = re.compile(
            rf"""["']?{re.escape(name)}["']?\s*[:=]\s*(["'])((?:(?!\1)[^\\]|\\.)*)\1""", re.DOTALL
        )
        if match := pattern.search(body):
            quote, raw = match.group(1), match.group(2)
            if quote == "'":
                # einfache Anführungszeichen -> JSON-String daraus machen
                raw = re.sub(r'(?<!\\)"', '\\"', raw.replace("\\'", "'"))
            try:
                return json.loads(f'"{raw}"')
            except ValueError:
                return raw
    return None


ASSERT_URL_RE = re.compile(r"""https://[^\s"'<>\\]+/auth-saml/service-providers/hager/assert[^\s"'<>\\]*""")


def _saml_post_from_script(body: str) -> tuple[str, dict[str, str]] | None:
    """Ziel-URL und Formularfelder einer per JS abgeschickten SAML-Antwort."""
    response = _js_value(body, "SAMLResponse", "samlResponse")
    if not response:
        return None
    response = response.strip()
    if response.startswith("<"):
        # Roh-XML -> wie im Formular Base64-kodiert senden
        response = base64.b64encode(response.encode("utf-8")).decode("ascii")

    url = _js_value(body, "url", "action", "postUrl")
    if not url or "/assert" not in url:
        candidates = ASSERT_URL_RE.findall(html_module.unescape(body))
        # Produktiv-Host bevorzugen (die Seite nennt auch eine Lab-Umgebung)
        prod = [u for u in candidates if urlparse(u).hostname == "e3dc.e3dc.com"]
        url = (prod or candidates or [None])[0]
    if not url:
        return None

    fields = {"SAMLResponse": response}
    if relay := _js_value(body, "RelayState", "relayState"):
        fields["RelayState"] = relay
    return url, fields


def _script_keys(body: str) -> list[str]:
    """Feldnamen in den Skripten (ohne Werte) – für die Fehlersuche."""
    keys = re.findall(r"""["']([A-Za-z_][A-Za-z0-9_]{2,30})["']\s*:""", body)
    return sorted(set(keys))[:60]


def describe_page(url: str, body: str) -> str:
    """Kurzbeschreibung einer unerwarteten Seite fürs Protokoll – ohne Query-Strings und Tokens."""

    def strip(u: str) -> str:
        parsed = urlparse(u)
        return f"{parsed.netloc}{parsed.path}"

    decoded = html_module.unescape(body or "")
    title = TITLE_RE.search(decoded)
    text = TAG_RE.sub(" ", SCRIPT_STYLE_RE.sub(" ", decoded))
    text = SECRETISH_RE.sub("…", " ".join(text.split()))[:400]
    forms = [
        f"{(_html_attribute(f.group(0), 'method') or 'get').upper()} {strip(urljoin(url, _html_attribute(f.group(0), 'action') or ''))}"
        for f in FORM_TAG_RE.finditer(decoded)
    ][:3]
    inputs = sorted({n for t in INPUT_TAG_RE.finditer(decoded) if (n := _html_attribute(t.group(0), "name"))})[:10]
    urls = sorted({strip(u) for u in URL_RE.findall(decoded)})[:8]
    scripts = len(SCRIPT_STYLE_RE.findall(decoded))
    return (
        f"Seite {strip(url)} ({len(body or '')} Zeichen) | Titel: {title.group(1).strip()[:80] if title else '-'}"
        f" | Text: {text or '-'} | Formulare: {forms or '-'} | Felder: {inputs or '-'}"
        f" | Skripte: {scripts} | Adressen: {urls or '-'} | Schlüssel: {_script_keys(decoded) or '-'}"
    )


async def async_login(email: str, password: str) -> CloudTokens:
    """Meldet sich mit E-Mail/Passwort am myHager-Konto an und liefert die Bearer-Tokens."""
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
        "User-Agent": USER_AGENT,
    }
    try:
        async with ClientSession(headers=headers, cookie_jar=CookieJar(unsafe=True, quote_cookie=False)) as session:
            jar: dict[tuple[str, str, str], _RawCookie] = {}
            trail: list[str] = []

            def note(method: str, url: str, status: int) -> None:
                parsed = urlparse(url)
                trail.append(f"{method} {parsed.netloc}{parsed.path} -> {status}")

            def fail(reason: str) -> HagerCloudAuthError:
                return HagerCloudAuthError(f"{reason} | Ablauf: " + " ; ".join(trail[-8:]))

            async def get(url: str):
                async with session.get(url, headers=_cookie_header(session, url, jar), allow_redirects=False) as resp:
                    _store_raw_cookies(str(resp.url), resp.headers.getall("Set-Cookie", []), jar)
                    note("GET", str(resp.url), resp.status)
                    return resp.status, resp.headers.get("Location"), str(resp.url), await resp.text()

            async def post(url: str, data: dict[str, str], extra: dict[str, str] | None = None):
                hdrs = {**(extra or {}), **_cookie_header(session, url, jar)}
                async with session.post(url, data=data, headers=hdrs, allow_redirects=False) as resp:
                    _store_raw_cookies(str(resp.url), resp.headers.getall("Set-Cookie", []), jar)
                    note("POST", str(resp.url), resp.status)
                    return resp.status, resp.headers.get("Location"), str(resp.url), await resp.text()

            # 1. Bis zur Login-Maske von login.hager.com folgen
            url, body = FLOW_LOGIN_URL, ""
            for _ in range(10):
                status, location, url, body = await get(url)
                if status in _REDIRECTS and location:
                    url = urljoin(url, location)
                    continue
                break
            path = urlparse(url).path
            if "/interaction/" in path and "/login" in path:
                login_url = url
            elif match := LOGIN_URL_RE.search(html_module.unescape(body)):
                login_url = match.group(0)
            else:
                raise fail("Login-Maske von login.hager.com nicht gefunden")

            # 2. Zugangsdaten absenden
            status, location, url, _ = await post(
                login_url,
                {"email": email.strip(), "password": password},
                {"Origin": "https://login.hager.com", "Referer": login_url},
            )
            if status not in (302, 303) or not location:
                raise fail("Unerwartete Antwort der Login-Maske")
            if "/interaction/" in location and "/login" in location:
                raise fail("E-Mail oder Passwort falsch")
            url = urljoin(url, location)

            # 3. SAML-Weiterleitungen bis zum Token folgen
            pending: tuple[str, str] | None = None
            for _ in range(20):
                if tokens := _tokens_from_url(url):
                    return tokens
                if pending is None:
                    path = urlparse(url).path
                    if "/interaction/" in path and ("/consent" in path or "/mfa/" in path):
                        raise fail("Das myHager-Konto verlangt eine Bestätigung im Browser (Einwilligung/MFA)")
                    status, location, current, body = await get(url)
                    if status in _REDIRECTS and location:
                        url = urljoin(current, location)
                        continue
                else:
                    current, body = pending
                    pending = None

                if form := _auto_post_form(body):
                    action, fields = form
                    status, location, posted, text = await post(urljoin(current, action), fields)
                    if tokens := _tokens_from_url(posted):
                        return tokens
                    if status in _REDIRECTS and location:
                        url = urljoin(posted, location)
                        continue
                    pending = (posted, text)
                    continue
                if saml := _saml_post_from_script(body):
                    action, fields = saml
                    status, location, posted, text = await post(urljoin(current, action), fields)
                    if tokens := _tokens_from_url(posted):
                        return tokens
                    if status in _REDIRECTS and location:
                        url = urljoin(posted, location)
                        continue
                    pending = (posted, text)
                    continue
                if redirect := _html_redirect(body):
                    url = urljoin(current, redirect)
                    continue
                raise fail(f"Unerwartete Antwort im Login-Ablauf – {describe_page(current, body)}")
    except ClientError as err:
        raise HagerCloudConnectionError("myHager-Login nicht erreichbar") from err

    raise HagerCloudAuthError("Der Login-Ablauf hat keine Tokens geliefert")
