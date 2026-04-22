"""Unit tests for internal token key resolution in service_auth middleware."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.middleware import service_auth


def _generate_rsa_keypair() -> tuple[str, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )
    return private_pem, public_pem


def _build_rs256_token(private_pem: str, *, kid: str | None = None, sub: str = "user-123") -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "aud": "ouroboros.scholarship-discovery",
        "iss": "ouroboros-orchestrator-internal",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
        "sid": "session-123",
        "trace_id": "trace-123",
        "jti": "jti-123",
    }
    headers = {"kid": kid} if kid else None
    return jwt.encode(payload, private_pem, algorithm="RS256", headers=headers)


@pytest.fixture(autouse=True)
def clear_jwks_cache() -> None:
    service_auth._jwks_cache_by_url.clear()  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_decode_internal_service_token_accepts_rs256_with_configured_public_pem(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_pem, public_pem = _generate_rsa_keypair()
    token = _build_rs256_token(private_pem)

    monkeypatch.setattr(service_auth.settings, "INTERNAL_TOKEN_SIGNING_ALGORITHM", "RS256")
    monkeypatch.setattr(service_auth.settings, "INTERNAL_TOKEN_PUBLIC_KEY", public_pem)
    monkeypatch.setattr(service_auth.settings, "INTERNAL_TOKEN_PUBLIC_KEYS", "{}")
    monkeypatch.setattr(service_auth.settings, "INTERNAL_TOKEN_JWKS_URL", "")
    monkeypatch.setattr(service_auth.settings, "INTERNAL_TOKEN_AUDIENCE", "ouroboros.scholarship-discovery")
    monkeypatch.setattr(service_auth.settings, "INTERNAL_TOKEN_ISSUER", "ouroboros-orchestrator-internal")

    claims = await service_auth._decode_internal_service_token(f"Bearer {token}")  # pylint: disable=protected-access

    assert claims is not None
    assert claims["sub"] == "user-123"


@pytest.mark.asyncio
async def test_decode_internal_service_token_uses_kid_public_key_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    valid_private_pem, valid_public_pem = _generate_rsa_keypair()
    wrong_private_pem, wrong_public_pem = _generate_rsa_keypair()
    token = _build_rs256_token(valid_private_pem, kid="internal-kid-1")

    monkeypatch.setattr(service_auth.settings, "INTERNAL_TOKEN_SIGNING_ALGORITHM", "RS256")
    monkeypatch.setattr(service_auth.settings, "INTERNAL_TOKEN_PUBLIC_KEY", wrong_public_pem)
    monkeypatch.setattr(
        service_auth.settings,
        "INTERNAL_TOKEN_PUBLIC_KEYS",
        json.dumps({"internal-kid-1": valid_public_pem}),
    )
    monkeypatch.setattr(service_auth.settings, "INTERNAL_TOKEN_JWKS_URL", "")
    monkeypatch.setattr(service_auth.settings, "INTERNAL_TOKEN_AUDIENCE", "ouroboros.scholarship-discovery")
    monkeypatch.setattr(service_auth.settings, "INTERNAL_TOKEN_ISSUER", "ouroboros-orchestrator-internal")

    claims = await service_auth._decode_internal_service_token(f"Bearer {token}")  # pylint: disable=protected-access

    assert claims is not None
    assert claims["sub"] == "user-123"

    # Ensure we do not accidentally pass because fallback key was used.
    token_with_wrong_key = _build_rs256_token(wrong_private_pem, kid="internal-kid-1")
    wrong_claims = await service_auth._decode_internal_service_token(  # pylint: disable=protected-access
        f"Bearer {token_with_wrong_key}"
    )
    assert wrong_claims is None


@pytest.mark.asyncio
async def test_resolve_jwks_key_fetches_and_caches_until_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}

    async def fake_fetch(_jwks_url: str) -> dict[str, object]:
        calls["count"] += 1
        return {"kid-1": "jwks-key"}

    monkeypatch.setattr(service_auth, "_fetch_jwks_keys", fake_fetch)
    monkeypatch.setattr(service_auth.settings, "INTERNAL_TOKEN_JWKS_REFRESH_SECONDS", 60)

    first = await service_auth._resolve_jwks_key(
        "https://issuer.example/jwks", "kid-1"
    )  # pylint: disable=protected-access
    second = await service_auth._resolve_jwks_key(
        "https://issuer.example/jwks", "kid-1"
    )  # pylint: disable=protected-access

    assert first == "jwks-key"
    assert second == "jwks-key"
    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_resolve_jwks_key_fetch_failure_falls_back_to_cached_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    jwks_url = "https://issuer.example/jwks"
    service_auth._jwks_cache_by_url[jwks_url] = {  # pylint: disable=protected-access
        "keys": {"kid-1": "cached-jwks-key"},
        "expires_at": 0,
    }

    async def failing_fetch(_jwks_url: str) -> dict[str, object]:
        raise RuntimeError("jwks unavailable")

    monkeypatch.setattr(service_auth, "_fetch_jwks_keys", failing_fetch)
    monkeypatch.setattr(service_auth.settings, "INTERNAL_TOKEN_JWKS_REFRESH_SECONDS", 60)

    resolved = await service_auth._resolve_jwks_key(jwks_url, "kid-1")  # pylint: disable=protected-access

    assert resolved == "cached-jwks-key"
