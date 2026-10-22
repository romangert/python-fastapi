"""ADFS JWT bearer-token verification for FastAPI routes.

This module only *verifies* tokens; it never issues them and never sees user
passwords. ADFS signs the JWT with its private key, and we check the signature
with the matching public key that ADFS publishes.

Usage on a route:

    @app.get("/something")
    def something(claims: dict = Depends(verify_adfs_token)):
        ...

Configuration (environment variables):
    ADFS_ISSUER    required. Expected "iss" claim, e.g. https://adfs.example.com/adfs
    ADFS_AUDIENCE  required. Expected "aud" claim (the relying party identifier).
    ADFS_JWKS_URL  optional. Where to download the public keys from.
                   Defaults to "<ADFS_ISSUER>/discovery/keys".

Request flow handled here:
    1. HTTPBearer extracts the token from "Authorization: Bearer <jwt>".
    2. PyJWKClient finds the ADFS public key whose "kid" matches the token header.
    3. jwt.decode verifies signature, expiry, issuer and audience.
    4. The decoded claims are returned to the route, or a 401 is raised.
"""

import os

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

# Reads the "Authorization: Bearer <token>" header. If the header is missing or
# uses another scheme, FastAPI rejects the request (401/403) before our code runs.
# It also makes the "Authorize" button appear in the /docs page.
bearer_scheme = HTTPBearer()

# Module-level cache: one client for the whole process, so the ADFS signing keys
# are downloaded once and reused instead of being fetched on every request.
_jwks_client: PyJWKClient | None = None


def _settings() -> tuple[str, str]:
    """Return (issuer, audience) from the environment.

    Read on every call (not at import time) so the app can start, and tests can
    set the variables, without them being present up front. A missing value is a
    server misconfiguration, so it returns 500 rather than 401.
    """
    try:
        # rstrip("/") so "https://host/adfs/" and "https://host/adfs" both work;
        # the "iss" claim comparison is an exact string match.
        return os.environ["ADFS_ISSUER"].rstrip("/"), os.environ["ADFS_AUDIENCE"]
    except KeyError as e:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, f"{e.args[0]} is not configured"
        )


def get_jwks_client() -> PyJWKClient:
    """Return the shared client that downloads and caches ADFS's public keys.

    Created lazily on first use. This is a FastAPI dependency, which lets tests
    replace it with a fake (app.dependency_overrides) so no network is needed.
    """
    global _jwks_client
    if _jwks_client is None:
        issuer, _ = _settings()
        # ADFS publishes its token-signing public keys (a JWKS document) here.
        keys_url = os.environ.get("ADFS_JWKS_URL", issuer + "/discovery/keys")
        # cache_keys=True keeps the downloaded keys in memory. If a token arrives
        # with an unknown "kid" (e.g. ADFS rotated its key), the client re-fetches.
        _jwks_client = PyJWKClient(keys_url, cache_keys=True)
    return _jwks_client


def verify_adfs_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    jwks_client: PyJWKClient = Depends(get_jwks_client),
) -> dict:
    """Validate an ADFS-issued JWT and return its claims.

    Raises HTTP 401 (with "WWW-Authenticate: Bearer") for any invalid token:
    bad signature, expired, wrong issuer, wrong audience, missing required
    claims, unknown signing key, or a malformed token.
    """
    issuer, audience = _settings()
    token = credentials.credentials
    try:
        # Look at the token's (unverified) header for its "kid", then return the
        # matching public key from the ADFS key set. Raises if there is no match
        # or the keys endpoint can't be reached.
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        # decode() does the real verification; it raises if any check fails.
        return jwt.decode(
            token,
            signing_key.key,
            # Allow only RS256. Never trust the algorithm named in the token
            # itself; that is how "alg: none" / HS256-with-public-key attacks work.
            algorithms=["RS256"],
            issuer=issuer,  # "iss" must equal ADFS_ISSUER: rejects other identity providers
            audience=audience,  # "aud" must equal ADFS_AUDIENCE: rejects tokens meant for other APIs
            # Signature and "exp" (expiry) are always checked. This additionally
            # makes the token invalid if these claims are absent altogether.
            options={"require": ["exp", "iss", "aud"]},
        )
    except jwt.PyJWTError as e:
        # PyJWTError is the base class for every verification failure above,
        # including PyJWKClientError from the key lookup. All map to 401.
        # The message is included to ease debugging; it names the failed check
        # (e.g. "Signature has expired") but contains no secrets.
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )
