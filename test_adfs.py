import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

import auth
from main import app

ISSUER = "https://adfs.example.com/adfs"
AUDIENCE = "my-api"

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class FakeSigningKey:
    key = private_key.public_key()


class FakeJwksClient:
    def get_signing_key_from_jwt(self, token):
        return FakeSigningKey()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ADFS_ISSUER", ISSUER)
    monkeypatch.setenv("ADFS_AUDIENCE", AUDIENCE)
    app.dependency_overrides[auth.get_jwks_client] = lambda: FakeJwksClient()
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_token(key=private_key, **overrides):
    claims = {
        "sub": "user1",
        "iss": ISSUER,
        "aud": AUDIENCE,
        "exp": int(time.time()) + 300,
        **overrides,
    }
    return jwt.encode(claims, key, algorithm="RS256")


def call(client, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return client.get("/testAdfs", headers=headers)


def test_valid_token(client):
    response = call(client, make_token())
    assert response.status_code == 200
    assert response.json()["subject"] == "user1"


def test_missing_token(client):
    assert call(client).status_code in (401, 403)


def test_expired_token(client):
    assert call(client, make_token(exp=int(time.time()) - 10)).status_code == 401


def test_wrong_audience(client):
    assert call(client, make_token(aud="other")).status_code == 401


def test_wrong_issuer(client):
    assert call(client, make_token(iss="https://evil.example.com/adfs")).status_code == 401


def test_bad_signature(client):
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    assert call(client, make_token(key=other_key)).status_code == 401
