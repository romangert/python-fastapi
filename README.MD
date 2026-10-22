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
