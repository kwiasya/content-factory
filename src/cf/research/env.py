"""Settings and secrets for the research contour, two files, never in git (ADR 0013).

The personal ``<repo>/.env`` (``CF_ENV_FILE`` points elsewhere) holds what differs per person: ``CF_PERSON``
and the roots. The shared ``<shared root>/secrets.env`` (``CF_SECRETS_FILE`` points elsewhere) holds the API
credentials both people use: the YouTube key and the Instagram token, app and user. ``load_env`` and
``load_secrets`` read ``KEY=VALUE`` lines (comments and blank lines skipped, optional quotes stripped) and set
each key in ``os.environ`` unless it is already set, so the shell wins over ``.env``, which wins over
``secrets.env``. The roots read ``.env`` on their first lookup; ``secrets.env`` is read only when a secret is
asked for (it needs the share). ``api_key`` is the one place the YouTube key is looked up; ``value`` looks up
any other variable the same way. ``set_value`` rewrites one ``KEY=VALUE`` line of the file the variable came
from (``secrets.env`` when neither file has it) and nothing else (``ig token-refresh``). Values are never
printed or logged.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from cf.research.store import REPO_ROOT

log = logging.getLogger(__name__)

ENV_PATH = REPO_ROOT / ".env"
PATH_VAR = "CF_ENV_FILE"  # another .env location (tests point it at a missing file)
SECRETS_NAME = "secrets.env"
SECRETS_VAR = "CF_SECRETS_FILE"  # another secrets.env location (tests point it at a missing file)
KEY_VAR = "YOUTUBE_API_KEY"
KEY_HELP = (f"{KEY_VAR} is not set; create an API key for YouTube Data API v3 in Google Cloud Console "
            f"and put `{KEY_VAR}=...` into <shared root>/{SECRETS_NAME} (one file for both people; another file "
            f"via {SECRETS_VAR}) or export it")

# Instagram Graph API (ADR 0010): a long-lived Facebook user token of the Meta app, the Author's
# Instagram business account id (Business Discovery runs as that account) and the app id and secret.
IG_TOKEN_VAR = "INSTAGRAM_ACCESS_TOKEN"
IG_USER_VAR = "INSTAGRAM_USER_ID"
IG_APP_ID_VAR = "INSTAGRAM_APP_ID"
IG_APP_SECRET_VAR = "INSTAGRAM_APP_SECRET"
IG_HELP = (f"{IG_TOKEN_VAR} and {IG_USER_VAR} are not set; put them into <shared root>/{SECRETS_NAME} (another "
           f"file via {SECRETS_VAR}, key names in .env.example) or export them. The token is a long-lived Facebook "
           f"user token with instagram_basic and instagram_manage_insights (ADR 0010)")


def env_path(path: Path | None = None) -> Path:
    """``path``, else ``$CF_ENV_FILE``, else ``<repo>/.env``."""
    return path or Path(os.environ.get(PATH_VAR) or ENV_PATH)


def secrets_path(path: Path | None = None) -> Path:
    """``path``, else ``$CF_SECRETS_FILE``, else ``<shared root>/secrets.env``."""
    if path:
        return path
    if os.environ.get(SECRETS_VAR):
        return Path(os.environ[SECRETS_VAR])
    from cf.research.store import shared_root
    return shared_root() / SECRETS_NAME


def _parse(raw: str) -> tuple[str, str] | None:
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        return None
    if line.startswith("export "):
        line = line[len("export "):]
    key, value = line.split("=", 1)
    key, value = key.strip(), value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return (key, value) if key else None


def _read(p: Path) -> dict[str, str]:
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
    except (FileNotFoundError, NotADirectoryError):
        return {}
    except OSError as exc:
        log.warning("cannot read %s: %s", p, exc.strerror or exc)
        return {}
    return dict(pair for pair in map(_parse, lines) if pair)


def _load(p: Path) -> dict[str, str]:
    found = _read(p)
    for key, val in found.items():
        os.environ.setdefault(key, val)
    return found


def load_env(path: Path | None = None) -> dict[str, str]:
    """Load the personal ``.env`` into ``os.environ`` (existing variables are kept); return what it defined."""
    return _load(env_path(path))


def load_secrets(path: Path | None = None) -> dict[str, str]:
    """Load the shared ``secrets.env`` into ``os.environ`` (existing variables are kept); return what it defined."""
    return _load(secrets_path(path))


def value(var: str, path: Path | None = None) -> str | None:
    """``var`` from the environment, else from ``.env``, else from ``secrets.env``; None when absent or empty.
    With ``path`` only that file is read."""
    got = os.environ.get(var)
    if not got:
        load_env(path)
        got = os.environ.get(var)
    if not got and path is None:
        load_secrets()
        got = os.environ.get(var)
    return got or None


def source(var: str) -> Path:
    """The file ``set_value`` rewrites for ``var``: the personal ``.env`` when it defines it, else ``secrets.env``."""
    personal = env_path()
    return personal if var in _read(personal) else secrets_path()


def api_key(path: Path | None = None) -> str | None:
    """The YouTube Data API key from the environment, else from ``.env``; None when absent."""
    return value(KEY_VAR, path)


def ig_token(path: Path | None = None) -> str | None:
    """The Instagram (Facebook user) access token; None when absent."""
    return value(IG_TOKEN_VAR, path)


def ig_user_id(path: Path | None = None) -> str | None:
    """The Author's Instagram business account id; None when absent."""
    return value(IG_USER_VAR, path)


def _chmod(p: Path) -> None:
    try:
        os.chmod(p, 0o600)
    except OSError as exc:
        log.warning("cannot set mode 600 on %s (%s); the folder's ACLs decide who reads it", p, exc.strerror or exc)


def set_value(var: str, new: str, path: Path | None = None) -> Path:
    """Rewrite the ``var=`` line of ``path`` or of the file the variable came from (``source``; append one when
    missing), keep every other line byte for byte, write atomically with mode 600 (a failing chmod over SMB is
    logged, not fatal) and set ``os.environ[var]``. Returns the file path."""
    p = path or source(var)
    if not p.parent.is_dir():
        from cf.research.store import StoreError, mount_hint
        raise StoreError(f"cannot write {p}: {mount_hint(p.parent)}")
    try:
        lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
    except FileNotFoundError:
        lines = []
    out, done = [], False
    for raw in lines:
        pair = _parse(raw)
        if pair and pair[0] == var and not done:
            out.append(f"{var}={new}\n")
            done = True
        else:
            out.append(raw)
    if not done:
        if out and not out[-1].endswith("\n"):
            out[-1] += "\n"
        out.append(f"{var}={new}\n")
    tmp = p.with_name(p.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("".join(out))
    _chmod(tmp)
    tmp.replace(p)
    _chmod(p)
    os.environ[var] = new
    return p
