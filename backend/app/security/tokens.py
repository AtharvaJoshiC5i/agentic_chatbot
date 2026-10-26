"""Opaque signed session tokens (stdlib HMAC, not JWT)."""

import base64
import hashlib
import hmac
import json
import time

from app.config import get_settings

_TOKEN_PREFIX = "ss1"


def _sign(body: str) -> str:
    settings = get_settings()
    secret = settings.jwt_secret_key.encode("utf-8")
    return hmac.new(secret, body.encode("utf-8"), hashlib.sha256).hexdigest()


def create_access_token(subject: str, role: str) -> str:
    settings = get_settings()
    exp = int(time.time()) + settings.access_token_expire_minutes * 60
    payload = {"sub": subject, "role": role, "exp": exp}
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    return f"{_TOKEN_PREFIX}.{body}.{_sign(body)}"


def decode_access_token(token: str) -> dict[str, str]:
    if not token.startswith(f"{_TOKEN_PREFIX}."):
        raise ValueError("Invalid token")
    parts = token.split(".", 2)
    if len(parts) != 3:
        raise ValueError("Invalid token")
    _, body, sig = parts
    if not hmac.compare_digest(_sign(body), sig):
        raise ValueError("Invalid token")
    pad = "=" * ((4 - len(body) % 4) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(body + pad))
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError("Invalid token") from exc
    exp = payload.get("exp")
    if exp is not None and int(exp) < int(time.time()):
        raise ValueError("Token expired")
    subject = payload.get("sub")
    role = payload.get("role")
    if not subject or not role:
        raise ValueError("Invalid token payload")
    return {"username": str(subject), "role": str(role)}
