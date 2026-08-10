import pytest

from schwab_readonly_mcp.auth import AuthenticationError, code_from_redirect


def test_code_from_redirect() -> None:
    assert code_from_redirect("https://localhost/callback?code=abc%20123&state=x") == "abc 123"


def test_code_from_redirect_rejects_missing_code() -> None:
    with pytest.raises(AuthenticationError, match="code"):
        code_from_redirect("https://localhost/callback?state=x")
