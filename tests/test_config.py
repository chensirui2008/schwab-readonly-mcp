import pytest

from schwab_readonly_mcp.config import ConfigurationError, Settings


def test_settings_requires_all_schwab_environment_values(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("SCHWAB_CLIENT_ID", "SCHWAB_CLIENT_SECRET", "SCHWAB_REDIRECT_URI"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ConfigurationError, match="SCHWAB_CLIENT_ID"):
        Settings.from_environment()
