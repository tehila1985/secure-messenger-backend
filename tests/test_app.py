"""
test_app.py — Stage 1 test suite.

HOW TO RUN:
  pytest tests/ -v

Each test gets a fresh in-memory database so tests never interfere with each other.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.main import app
from server.models import Base, get_db
from server.crypto import encrypt, decrypt

# ---------------------------------------------------------------------------
# Test-only credential constants — not real secrets; exist only for fixtures.
# ---------------------------------------------------------------------------
TEST_USER_ALICE = "alice"
TEST_PASS_ALICE = "secret123"
TEST_USER_BOB = "bob"
TEST_PASS_BOB = "secret456"
TEST_USER_CHARLIE = "charlie"
TEST_PASS_CHARLIE = "secret789"

# ---------------------------------------------------------------------------
# Test database setup — in-memory SQLite, wiped before each test
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def register_and_login(client, username: str = TEST_USER_ALICE, password: str = TEST_PASS_ALICE) -> str:
    """Register a user and return their JWT token."""
    client.post("/register", json={"username": username, "password": password})
    response = client.post("/login", json={"username": username, "password": password})
    return response.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# 1. Authentication tests
# ===========================================================================

class TestAuthentication:

    def test_register_success(self, client):
        response = client.post("/register", json={"username": TEST_USER_ALICE, "password": TEST_PASS_ALICE})
        assert response.status_code == 201

    def test_register_duplicate_username(self, client):
        client.post("/register", json={"username": TEST_USER_ALICE, "password": TEST_PASS_ALICE})
        response = client.post("/register", json={"username": TEST_USER_ALICE, "password": "other-password"})
        assert response.status_code == 400

    def test_register_password_too_short(self, client):
        response = client.post("/register", json={"username": TEST_USER_ALICE, "password": "abc"})
        assert response.status_code == 422   # Pydantic rejects it before service code runs

    def test_login_success(self, client):
        client.post("/register", json={"username": TEST_USER_ALICE, "password": TEST_PASS_ALICE})
        response = client.post("/login", json={"username": TEST_USER_ALICE, "password": TEST_PASS_ALICE})
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_wrong_password(self, client):
        client.post("/register", json={"username": TEST_USER_ALICE, "password": TEST_PASS_ALICE})
        response = client.post("/login", json={"username": TEST_USER_ALICE, "password": "wrongpassword"})
        assert response.status_code == 401

    def test_login_unknown_user(self, client):
        response = client.post("/login", json={"username": "ghost", "password": TEST_PASS_ALICE})
        assert response.status_code == 401

    def test_messages_require_token(self, client):
        response = client.get("/messages")
        assert response.status_code in (401, 403)

    def test_messages_reject_bad_token(self, client):
        response = client.get("/messages", headers={"Authorization": "Bearer fake-token"})
        assert response.status_code == 401

    def test_messages_accept_valid_token(self, client):
        token = register_and_login(client)
        response = client.get("/messages", headers=auth(token))
        assert response.status_code == 200


# ===========================================================================
# 2. Encryption tests
# ===========================================================================

class TestEncryption:

    def test_encrypt_is_not_plain_text(self):
        assert encrypt("hello world") != "hello world"

    def test_decrypt_round_trip(self):
        original = "this is a secret message"
        assert decrypt(encrypt(original)) == original

    def test_same_message_encrypts_differently_each_time(self):
        assert encrypt("hello") != encrypt("hello")

    def test_tampered_ciphertext_raises(self):
        blob = encrypt("original")
        tampered = blob[:-4] + "XXXX"
        with pytest.raises(Exception):
            decrypt(tampered)

    def test_messages_are_stored_encrypted(self, client):
        from server.models import Message
        token = register_and_login(client)
        original_text = "private secret"

        client.post(
            "/messages",
            json={"content": original_text, "recipient": TEST_USER_BOB},
            headers=auth(token),
        )

        db = TestingSession()
        row = db.query(Message).first()
        db.close()

        assert row.ciphertext != original_text
        assert decrypt(row.ciphertext) == original_text


# ===========================================================================
# 3. Messaging tests
# ===========================================================================

class TestMessaging:

    def test_send_message_success(self, client):
        alice_token = register_and_login(client, TEST_USER_ALICE, TEST_PASS_ALICE)
        register_and_login(client, TEST_USER_BOB, TEST_PASS_BOB)

        response = client.post(
            "/messages",
            json={"content": "hello bob", "recipient": TEST_USER_BOB},
            headers=auth(alice_token),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == "hello bob"
        assert data["sender"] == TEST_USER_ALICE
        assert data["recipient"] == TEST_USER_BOB

    def test_get_messages_returns_decrypted(self, client):
        alice_token = register_and_login(client, TEST_USER_ALICE, TEST_PASS_ALICE)
        register_and_login(client, TEST_USER_BOB, TEST_PASS_BOB)

        client.post("/messages", json={"content": "hi bob", "recipient": TEST_USER_BOB}, headers=auth(alice_token))

        response = client.get("/messages", headers=auth(alice_token))
        assert response.status_code == 200
        messages = response.json()
        assert len(messages) >= 1
        assert messages[0]["content"] == "hi bob"

    def test_user_sees_only_their_messages(self, client):
        alice_token   = register_and_login(client, TEST_USER_ALICE,   TEST_PASS_ALICE)
        bob_token     = register_and_login(client, TEST_USER_BOB,     TEST_PASS_BOB)
        charlie_token = register_and_login(client, TEST_USER_CHARLIE, TEST_PASS_CHARLIE)

        client.post("/messages", json={"content": "hi bob",        "recipient": TEST_USER_BOB}, headers=auth(alice_token))
        client.post("/messages", json={"content": "secret for bob","recipient": TEST_USER_BOB}, headers=auth(charlie_token))

        response = client.get("/messages", headers=auth(alice_token))
        alice_messages = response.json()

        assert len(alice_messages) == 1
        assert alice_messages[0]["content"] == "hi bob"
        for msg in alice_messages:
            assert msg["content"] != "secret for bob"
