import os
from pathlib import Path

import pytest

from database.db import init_db
from ml.fraud_detector import reset_detector


@pytest.fixture(autouse=True)
def app(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    reset_detector()
    init_db(str(db_path))
    from app import create_app

    application = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "DATABASE_PATH": str(db_path),
            "SECRET_KEY": "test-secret-key",
        }
    )
    yield application
    reset_detector()


@pytest.fixture()
def client(app):
    return app.test_client()


def signup_and_login(client, email="person@example.com", password="Password@123", name="Person"):
    client.post(
        "/signup",
        data={
            "full_name": name,
            "email": email,
            "password": password,
            "confirm_password": password,
        },
        follow_redirects=True,
    )
    return email
