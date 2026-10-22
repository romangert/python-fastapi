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
