import os

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

bearer_scheme = HTTPBearer()

_jwks_client: PyJWKClient | None = None


def _settings() -> tuple[str, str]:
    """ADFS settings come from env vars, e.g.
    ADFS_ISSUER=https://adfs.example.com/adfs
    ADFS_AUDIENCE=<relying party identifier / client id>
    """
    try:
        return os.environ["ADFS_ISSUER"].rstrip("/"), os.environ["ADFS_AUDIENCE"]
    except KeyError as e:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, f"{e.args[0]} is not configured"
        )


def get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        issuer, _ = _settings()
        # ADFS publishes its token-signing public keys here.
        keys_url = os.environ.get("ADFS_JWKS_URL", issuer + "/discovery/keys")
        _jwks_client = PyJWKClient(keys_url, cache_keys=True)
    return _jwks_client


def verify_adfs_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    jwks_client: PyJWKClient = Depends(get_jwks_client),
) -> dict:
    """Validate signature, expiry, issuer and audience of an ADFS-issued JWT."""
    issuer, audience = _settings()
    token = credentials.credentials
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=issuer,
            audience=audience,
            options={"require": ["exp", "iss", "aud"]},
        )
    except jwt.PyJWTError as e:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )
