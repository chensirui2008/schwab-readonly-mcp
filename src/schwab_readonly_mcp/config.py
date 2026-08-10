from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class ConfigurationError(RuntimeError):
    """Raised when a required Schwab configuration value is absent."""


@dataclass(frozen=True)
class Settings:
    client_id: str
    client_secret: str
    redirect_uri: str
    token_path: Path

    @classmethod
    def from_environment(cls) -> "Settings":
        missing = [
            name
            for name in ("SCHWAB_CLIENT_ID", "SCHWAB_CLIENT_SECRET", "SCHWAB_REDIRECT_URI")
            if not os.environ.get(name)
        ]
        if missing:
            raise ConfigurationError(f"Missing required environment variables: {', '.join(missing)}")
        token_path = Path(
            os.environ.get(
                "SCHWAB_TOKEN_PATH",
                Path.home() / ".config" / "schwab-readonly-mcp" / "token.json",
            )
        ).expanduser()
        return cls(
            client_id=os.environ["SCHWAB_CLIENT_ID"],
            client_secret=os.environ["SCHWAB_CLIENT_SECRET"],
            redirect_uri=os.environ["SCHWAB_REDIRECT_URI"],
            token_path=token_path,
        )
