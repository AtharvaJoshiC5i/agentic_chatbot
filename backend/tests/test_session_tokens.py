"""Signed session tokens (non-JWT)."""

from app.security.tokens import create_access_token, decode_access_token


def test_session_token_round_trip() -> None:
    token = create_access_token("returns_analyst", "returns_analyst")
    assert token.startswith("ss1.")
    payload = decode_access_token(token)
    assert payload["username"] == "returns_analyst"
    assert payload["role"] == "returns_analyst"
