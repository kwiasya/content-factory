"""Thin Instagram Graph API adapter (v25.0, graph.facebook.com): token from ``.env``, urllib, no logic.

Mirrors ``youtube``: every public function takes the ``Store``, charges the
hourly ``instagram`` bucket through ``quota.charge`` *before* the call and
returns the raw JSON payload, which ``ingest`` turns into rows. ``transport``
replaces the HTTP call: a function ``(path, params) -> payload``, where
``path`` is the Graph path after the version (``17841404024670796``,
``17841404024670796/media``) and ``params`` the query without the token.
Tests pass recorded payloads through it.

The token travels in the ``Authorization`` header, never in a URL, a message
or a log. The HTTP transport reads Meta's usage headers
(``X-Business-Use-Case-Usage``, ``X-App-Usage``) into ``_usage`` on the payload;
``_call`` stores the share with ``quota.record_pressure`` so the bucket pauses
near Meta's limit, and a rate-limit error (codes 4, 17, 32, 613, 80002) pauses
it at once (``QuotaExceeded``). ADR 0010 has the why and the limits.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Callable

from cf.research import env, quota
from cf.research.store import Store

VERSION = "v25.0"
BASE_URL = f"https://graph.facebook.com/{VERSION}/"
TIMEOUT_S = 30
MEDIA_PAGE = 50  # media per page (Business Discovery and own media)
MEDIA_FIELDS = "id,media_product_type,media_type,like_count,comments_count,view_count,timestamp,permalink,caption"
OWN_MEDIA_FIELDS = "id,media_product_type,media_type,like_count,comments_count,timestamp,permalink,caption"
ACCOUNT_FIELDS = "id,username,name,biography,website,followers_count,media_count"
# reel insights: the core set works for every reel; the watch-time pair only for reels, and not always
INSIGHT_METRICS = ("reach", "views", "saved", "shares", "total_interactions")
REEL_METRICS = ("ig_reels_avg_watch_time", "ig_reels_video_view_total_time")
RATE_LIMIT_CODES = {4, 17, 32, 613, 80002}
NOT_FOUND_SUBCODES = {2207013}  # Business Discovery: no such business/creator account

Transport = Callable[[str, dict], dict]


class InstagramError(Exception):
    """The Graph API answered with an error, or could not be reached. ``code``: Meta's error code."""

    def __init__(self, message: str, code: int | None = None, subcode: int | None = None):
        super().__init__(message)
        self.code, self.subcode = code, subcode
        self.usage: dict | None = None  # Meta's usage headers of the failed call, when it had them


# --- usage headers ------------------------------------------------------------

def usage_from_headers(headers: dict) -> dict:
    """``{"pct", "regain_minutes"}``: the highest share (0-100) of any counter in Meta's usage headers
    and the longest ``estimated_time_to_regain_access`` (minutes). Missing or broken headers count as 0."""
    pct, regain = 0, 0
    lower = {k.lower(): v for k, v in headers.items()}
    try:
        app = json.loads(lower.get("x-app-usage") or "{}")
        pct = max([pct] + [int(v) for k, v in app.items() if k in ("call_count", "total_cputime", "total_time")])
    except (ValueError, TypeError, AttributeError):
        pass
    try:
        buc = json.loads(lower.get("x-business-use-case-usage") or "{}")
        for entries in buc.values():
            for e in entries:
                pct = max([pct] + [int(e.get(k) or 0) for k in ("call_count", "total_cputime", "total_time")])
                regain = max(regain, int(e.get("estimated_time_to_regain_access") or 0))
    except (ValueError, TypeError, AttributeError):
        pass
    return {"pct": pct, "regain_minutes": regain}


def _error(path: str, body: dict | None, status: int | None = None) -> InstagramError:
    err = (body or {}).get("error") or {}
    code, sub = err.get("code"), err.get("error_subcode")
    msg = err.get("error_user_msg") or err.get("message") or "unknown error"
    head = f"Graph API {path.split('/')[-1] if '/' in path else 'node'}"
    where = f"HTTP {status}: " if status else ""
    if code == 190:
        msg += " (the access token is invalid or expired; issue a new one and run `ig token-refresh`)"
    return InstagramError(f"{head}: {where}{msg} (code {code}{f', subcode {sub}' if sub else ''})", code, sub)


def http_transport(path: str, params: dict, *, token: str | None = None) -> dict:
    """GET ``BASE_URL/<path>`` with the token in the ``Authorization`` header; the JSON body with ``_usage``."""
    tok = token or env.ig_token()
    if not tok:
        raise InstagramError(env.IG_HELP)
    query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(f"{BASE_URL}{path}?{query}", headers={"Authorization": f"Bearer {tok}"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            body["_usage"] = usage_from_headers(dict(resp.headers.items()))
            return body
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8"))
        except (ValueError, AttributeError):
            body = None
        err = _error(path, body, exc.code)
        err.usage = usage_from_headers(dict(exc.headers.items()) if exc.headers else {})
        raise err from None
    except urllib.error.URLError as exc:
        raise InstagramError(f"Graph API: cannot reach graph.facebook.com: {exc.reason}") from None


def _call(store: Store, method: str, path: str, params: dict, transport: Transport | None) -> dict:
    if transport is None:  # fail on a missing token before charging a call
        if not env.ig_token():
            raise InstagramError(env.IG_HELP)
        transport = http_transport
    quota.charge(store, method)
    bucket = quota.cost(method)[0]
    try:
        out = transport(path, params)
    except InstagramError as exc:
        usage = getattr(exc, "usage", None)
        if exc.code in RATE_LIMIT_CODES:
            quota.record_pressure(store, bucket, 100, max((usage or {}).get("regain_minutes", 0), 60))
            raise quota.QuotaExceeded(f"quota: Meta refused {method} for its rate limit ({exc}); the instagram "
                                      f"bucket pauses for an hour") from None
        if usage:
            quota.record_pressure(store, bucket, usage["pct"], usage["regain_minutes"])
        raise
    usage = out.pop("_usage", None) if isinstance(out, dict) else None
    if usage is not None:
        quota.record_pressure(store, bucket, usage["pct"], usage["regain_minutes"])
    if isinstance(out, dict) and "error" in out:
        raise _error(path, out)
    return out


def _media_edge(limit: int, after: str | None, fields: str) -> str:
    edge = "media" + (f".after({after})" if after else "") + f".limit({limit})"
    return f"{edge}{{{fields}}}"


def business_discovery(store: Store, user_id: str, username: str, *, media_limit: int = MEDIA_PAGE,
                       after: str | None = None, transport: Transport | None = None) -> dict:
    """Business Discovery of ``username`` as the account ``user_id``: the account and, unless
    ``media_limit`` is 0, one page of its media (newest first; ``after`` is the cursor of the last page).
    Only public business and creator accounts are visible."""
    fields = "username,name,biography,website,followers_count,media_count"
    if media_limit:
        fields += "," + _media_edge(media_limit, after, MEDIA_FIELDS)
    params = {"fields": f"business_discovery.username({username.lstrip('@')}){{id,{fields}}}"}
    return _call(store, "ig.business_discovery", user_id, params, transport)


def account(store: Store, user_id: str, *, transport: Transport | None = None) -> dict:
    """The account ``user_id`` itself (the Author's): username, followers, media count."""
    return _call(store, "ig.account", user_id, {"fields": ACCOUNT_FIELDS}, transport)


def own_media(store: Store, user_id: str, *, after: str | None = None, limit: int = MEDIA_PAGE,
              metrics: tuple[str, ...] | None = INSIGHT_METRICS + REEL_METRICS,
              transport: Transport | None = None) -> dict:
    """One page of the account's own media, newest first, with lifetime insights nested per media
    (``metrics``; None: without insights). A reel-only metric is simply absent on feed posts."""
    fields = OWN_MEDIA_FIELDS
    if metrics:
        fields += f",insights.metric({','.join(metrics)})"
    return _call(store, "ig.media", f"{user_id}/media",
                 {"fields": fields, "limit": limit, "after": after}, transport)


def media_insights(store: Store, media_id: str, metrics: tuple[str, ...] = INSIGHT_METRICS + REEL_METRICS, *,
                   transport: Transport | None = None) -> dict:
    """Lifetime insights of one own media."""
    return _call(store, "ig.insights", f"{media_id}/insights", {"metric": ",".join(metrics)}, transport)


# --- the token ------------------------------------------------------------------

@dataclass(frozen=True)
class TokenStatus:
    """What ``debug_token`` says of the access token (never the token itself)."""
    valid: bool
    type: str | None
    expires_at: str | None       # ISO UTC; None: never expires
    days_left: int | None
    data_access_expires_at: str | None
    scopes: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def _iso(ts) -> str | None:
    return datetime.fromtimestamp(int(ts), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if ts else None


def token_status_from(payload: dict, *, now: datetime | None = None) -> TokenStatus:
    """Parse a ``debug_token`` payload. ``days_left`` is rounded down; 0 on the last day."""
    d = payload.get("data") or {}
    exp = int(d.get("expires_at") or 0)  # 0: a token that never expires
    left = exp - (now or datetime.now(timezone.utc)).timestamp() if exp else None
    days = None if left is None else max(int(left // 86400), 0)
    return TokenStatus(bool(d.get("is_valid")) and (left is None or left > 0), d.get("type"), _iso(exp), days,
                       _iso(d.get("data_access_expires_at")), list(d.get("scopes") or []))


def _app_token() -> str:
    app, secret = env.value(env.IG_APP_ID_VAR), env.value(env.IG_APP_SECRET_VAR)
    if not app or not secret:
        raise InstagramError(f"{env.IG_APP_ID_VAR} and {env.IG_APP_SECRET_VAR} are not set (see .env.example)")
    return f"{app}|{secret}"


def token_status(*, transport: Transport | None = None, now: datetime | None = None) -> TokenStatus:
    """``debug_token`` of the access token, asked as the app (no call of the user's hourly bucket)."""
    tok = env.ig_token()
    if not tok:
        raise InstagramError(env.IG_HELP)
    if transport is None:
        app_token = _app_token()
        transport = lambda path, params: http_transport(path, params, token=app_token)  # noqa: E731
    out = transport("debug_token", {"input_token": tok})
    if "error" in out:
        raise _error("debug_token", out)
    return token_status_from(out, now=now)


def exchange_token(*, transport: Transport | None = None) -> dict:
    """``fb_exchange_token``: a fresh long-lived token for the current one (``access_token``, ``expires_in``)."""
    tok = env.ig_token()
    if not tok:
        raise InstagramError(env.IG_HELP)
    app, secret = env.value(env.IG_APP_ID_VAR), env.value(env.IG_APP_SECRET_VAR)
    if not app or not secret:
        raise InstagramError(f"{env.IG_APP_ID_VAR} and {env.IG_APP_SECRET_VAR} are not set (see .env.example)")
    params = {"grant_type": "fb_exchange_token", "client_id": app, "client_secret": secret, "fb_exchange_token": tok}
    out = (transport or (lambda path, p: http_transport(path, p, token=tok)))("oauth/access_token", params)
    if "error" in out:
        raise _error("oauth/access_token", out)
    if not out.get("access_token"):
        raise InstagramError("oauth/access_token answered without a token")
    return out
