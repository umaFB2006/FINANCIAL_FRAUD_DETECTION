from tests.conftest import signup_and_login


def test_signup_works(client):
    resp = client.post(
        "/signup",
        data={
            "full_name": "New User",
            "email": "newuser@example.com",
            "password": "Password@123",
            "confirm_password": "Password@123",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Dashboard" in resp.data or b"Operations" in resp.data or b"New Transaction" in resp.data


def test_duplicate_signup_rejected(client):
    payload = {
        "full_name": "Dup",
        "email": "dup@example.com",
        "password": "Password@123",
        "confirm_password": "Password@123",
    }
    client.post("/signup", data=payload, follow_redirects=True)
    client.get("/logout")
    resp = client.post("/signup", data=payload, follow_redirects=True)
    assert b"already exists" in resp.data


def test_weak_password_rejected(client):
    resp = client.post(
        "/signup",
        data={
            "full_name": "Weak",
            "email": "weak@example.com",
            "password": "password",
            "confirm_password": "password",
        },
        follow_redirects=True,
    )
    assert b"Password must" in resp.data or resp.status_code == 200
    from database.db import fetch_one

    assert fetch_one("SELECT id FROM users WHERE email = ?", ("weak@example.com",)) is None


def test_login_works(client):
    signup_and_login(client, "loginok@example.com")
    client.get("/logout")
    resp = client.post(
        "/login",
        data={"email": "loginok@example.com", "password": "Password@123"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Logged in" in resp.data or b"Dashboard" in resp.data or b"New Transaction" in resp.data


def test_invalid_login_rejected(client):
    resp = client.post(
        "/login",
        data={"email": "nobody@example.com", "password": "WrongPass@1"},
        follow_redirects=True,
    )
    assert b"Invalid email or password" in resp.data


def test_logout_works(client):
    signup_and_login(client, "logout@example.com")
    resp = client.get("/logout", follow_redirects=True)
    assert b"logged out" in resp.data.lower() or b"Login" in resp.data


def test_protected_route_blocked(client):
    resp = client.get("/dashboard", follow_redirects=True)
    assert b"log in" in resp.data.lower() or b"Login" in resp.data


def test_profile_works(client):
    signup_and_login(client, "profile@example.com")
    resp = client.get("/profile")
    assert resp.status_code == 200
    assert b"profile@example.com" in resp.data
