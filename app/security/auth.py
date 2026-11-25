import base64
import hashlib
import hmac
import json
import time
from typing import Optional

from fastapi import Header, HTTPException

from app.config.settings import get_settings


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_access_token(student_id: str, expires_in_seconds: int = 3600) -> str:
    """Create a signed HS256 JWT token scoped to a student_id."""
    secret = get_settings().JWT_SECRET.encode("utf-8")
    header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode("utf-8"))
    payload = _b64url_encode(
        json.dumps({"sub": student_id, "exp": int(time.time()) + expires_in_seconds}).encode("utf-8")
    )
    signing_input = f"{header}.{payload}".encode("ascii")
    sig = _b64url_encode(hmac.new(secret, signing_input, hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"


def verify_access_token(token: str) -> str:
    """Verify an HS256 JWT token and return the subject student_id."""
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
        secret = get_settings().JWT_SECRET.encode("utf-8")
        expected_sig = _b64url_encode(
            hmac.new(secret, f"{header_b64}.{payload_b64}".encode("ascii"), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(sig_b64, expected_sig):
            raise ValueError("Invalid signature")
        payload = json.loads(_b64url_decode(payload_b64))
        if int(payload.get("exp", 0)) < int(time.time()):
            raise ValueError("Token expired")
        sub = payload.get("sub")
        if not sub:
            raise ValueError("Missing subject")
        return sub
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {exc}")


def verify_student_access(student_id: str, authorization: Optional[str] = Header(default=None)) -> None:
    """Enforce student-level isolation when AUTH_REQUIRED is True or a Bearer token is sent."""
    auth_required = get_settings().AUTH_REQUIRED
    if not authorization:
        if auth_required:
            raise HTTPException(status_code=401, detail="Missing Authorization Bearer token.")
        return

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header must use Bearer scheme.")

    token_student_id = verify_access_token(authorization[len("Bearer "):].strip())
    if token_student_id != student_id:
        raise HTTPException(status_code=403, detail="Token does not match requested student_id.")
