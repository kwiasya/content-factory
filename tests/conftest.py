"""Keep the suite offline: never read the real .env or the shared secrets.env (a YouTube key there would
turn "no key" tests into live API calls). Tests that need a key set YOUTUBE_API_KEY themselves."""

import os

os.environ.setdefault("CF_ENV_FILE", "/nonexistent/content-factory.env")
os.environ.setdefault("CF_SECRETS_FILE", "/nonexistent/content-factory-secrets.env")
