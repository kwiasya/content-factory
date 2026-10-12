"""python -m cf.desk [--repo PATH] [--host 127.0.0.1] [--port 8765] [--token T]

Starts Desk on localhost. Any other host (the home network) requires --token; every request must then
carry it (Authorization: Bearer T, or open http://host:port/?token=T once and the browser keeps a cookie).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import uvicorn

from cf.desk.app import create_app
from cf.research.store import default_db_path, footage_root

LOCALHOSTS = {"127.0.0.1", "localhost", "::1"}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m cf.desk", description="Desk: the Author's window over the Editor's files.")
    p.add_argument("--repo", type=Path, default=Path.cwd(), help="repo checkout to serve (default: current directory)")
    p.add_argument("--host", default="127.0.0.1", help="bind address (default: 127.0.0.1)")
    p.add_argument("--port", type=int, default=8765, help="port (default: 8765)")
    p.add_argument("--token", help="shared token; required when --host is not localhost")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.host not in LOCALHOSTS and not args.token:
        parser.error(f"--host {args.host} is reachable from the network: pass --token")
    repo = args.repo.expanduser()
    if not repo.is_dir():
        parser.error(f"--repo {repo} is not a directory")
    app = create_app(repo, footage_root=footage_root(), db_path=default_db_path(), token=args.token)
    url = f"http://{args.host}:{args.port}/" + (f"?token={args.token}" if args.token else "")
    print(f"Desk serving {repo.resolve()} at {url}", file=sys.stderr)
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0
