from __future__ import annotations

import argparse
import sys
import webbrowser

from .auth import SchwabAuthenticator, authorization_url, code_from_redirect
from .config import ConfigurationError, Settings
from .server import create_server


def main() -> None:
    parser = argparse.ArgumentParser(prog="schwab-readonly-mcp")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("auth", help="Authorize this local client and securely save its OAuth token.")
    commands.add_parser("server", help="Run the read-only MCP server over stdio.")
    args = parser.parse_args()
    try:
        settings = Settings.from_environment()
        if args.command == "auth":
            url = authorization_url(settings)
            print("Opening Schwab authorization in your browser. After approval, paste the complete redirect URL.")
            print("If the redirect page does not load, copy its address-bar URL and paste it here.")
            webbrowser.open(url)
            redirect_url = input("Redirect URL: ").strip()
            SchwabAuthenticator(settings).exchange_code(code_from_redirect(redirect_url))
            print(f"Token saved with owner-only permissions at {settings.token_path}")
            return
        create_server().run()
    except (ConfigurationError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
