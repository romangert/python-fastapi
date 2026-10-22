# fastapi-app

A minimal FastAPI project with two endpoints:

- `GET /` returns `{"message": "Hello, FastAPI!"}`
- `GET /health` returns `{"status": "ok"}`

## Setup

From the `fastapi-app` folder (PowerShell):

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

The `Set-ExecutionPolicy` line only affects the current terminal session and is needed so PowerShell allows the activation script.

## ADFS authentication

`GET /testAdfs` requires an `Authorization: Bearer <jwt>` header. The token's RS256 signature is checked against the ADFS signing keys, along with expiry, issuer and audience. Configure it with environment variables:

```powershell
$env:ADFS_ISSUER = "https://adfs.example.com/adfs"   # token "iss" claim
$env:ADFS_AUDIENCE = "<relying party identifier>"    # token "aud" claim
# optional, defaults to <ADFS_ISSUER>/discovery/keys
$env:ADFS_JWKS_URL = "https://adfs.example.com/adfs/discovery/keys"
```

Invalid or missing tokens get `401`/`403`.

## How the authentication works

The logic lives in `auth.py` and is attached to the route in `main.py` as a FastAPI dependency (`Depends(verify_adfs_token)`). The app never sees user passwords and never issues tokens. ADFS does that, and this app only verifies them.

### Request flow

1. **Client gets a token from ADFS.** The client signs in with ADFS (for example OAuth2/OpenID Connect) and receives a signed JWT access token. This happens outside this app.
2. **Client calls the API** with the header `Authorization: Bearer <jwt>`.
3. **Header extraction.** FastAPI's `HTTPBearer` reads the header and passes the token string to `verify_adfs_token`. If the header is missing or not a `Bearer` scheme, the request is rejected before any verification (`401`/`403`).
4. **Find the signing key.** The JWT header contains a `kid` (key id). `PyJWKClient` downloads ADFS's public keys from the JWKS URL (`<ADFS_ISSUER>/discovery/keys`, or `ADFS_JWKS_URL` if set), caches them, and picks the key whose `kid` matches.
5. **Verify the token.** `jwt.decode` checks:
   - **Signature:** valid RS256 signature using the ADFS public key, which proves ADFS issued the token and it was not modified.
   - **Expiry (`exp`):** the token has not expired.
   - **Issuer (`iss`):** equals `ADFS_ISSUER`, so tokens from another identity provider are rejected.
   - **Audience (`aud`):** equals `ADFS_AUDIENCE`, so tokens meant for a different API are rejected.
   - **Required claims:** `exp`, `iss` and `aud` must be present.
   - **Algorithm:** only `RS256` is accepted, which blocks algorithm-confusion attacks such as `alg: none`.
6. **Result.** On success the decoded claims are passed to the route handler, and `/testAdfs` returns the `sub` (subject) claim. On any verification error the app responds `401` with `WWW-Authenticate: Bearer` and the reason.

```
Client ──(sign in)──▶ ADFS ──(JWT)──▶ Client
Client ──(Authorization: Bearer JWT)──▶ FastAPI /testAdfs
FastAPI ──(fetch + cache public keys, matched by kid)──▶ ADFS /discovery/keys
FastAPI: verify signature, exp, iss, aud ──▶ 200 with claims, or 401
```

### Error responses

| Situation | Status |
|---|---|
| No `Authorization` header or wrong scheme | `401`/`403` (FastAPI `HTTPBearer`) |
| Bad signature, expired, wrong issuer or audience, malformed token | `401` |
| `ADFS_ISSUER` or `ADFS_AUDIENCE` not set | `500` |

### Notes

- The JWKS client is created once and keeps the keys in memory, so ADFS is not called on every request. If ADFS rotates its signing key, an unknown `kid` makes the client re-fetch the keys.
- The first request after startup needs network access to the ADFS keys endpoint.
- To protect another route, add `claims: dict = Depends(verify_adfs_token)` to its parameters. You can also check claims such as roles or groups inside the handler.
- Tests (`test_adfs.py`) replace the JWKS client with a fake that uses a locally generated RSA key, so they run without ADFS.

## Run

```powershell
uvicorn main:app --reload
```

- API: http://127.0.0.1:8000/
- Interactive docs (Swagger UI): http://127.0.0.1:8000/docs
- Alternative docs (ReDoc): http://127.0.0.1:8000/redoc

`--reload` restarts the server automatically when you change the code. Stop it with `Ctrl+C`.

## Test

```powershell
pytest
```

Tests live in `test_main.py` and use FastAPI's `TestClient`, so the server does not need to be running.

## Files

| File | Purpose |
|---|---|
| `main.py` | The FastAPI app and its routes |
| `test_main.py` | pytest tests for the routes |
| `requirements.txt` | Python dependencies |
