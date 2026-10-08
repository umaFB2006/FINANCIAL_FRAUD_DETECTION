from auth.authentication import create_user
from tests.conftest import signup_and_login


def test_unauthorized_admin_access_blocked(client):
    signup_and_login(client, "plain@example.com")
    resp = client.get("/admin", follow_redirects=True)
    assert resp.status_code == 200
    assert b"not authorized" in resp.data.lower() or b"Admin dashboard" not in resp.data


def test_investigator_cannot_see_admin_unless_admin(client):
    create_user("invonly@example.com", "Password@123", "Inv Only", "INVESTIGATOR")
    client.post(
        "/login",
        data={"email": "invonly@example.com", "password": "Password@123"},
        follow_redirects=True,
    )
    resp = client.get("/admin", follow_redirects=True)
    assert b"Total Users" not in resp.data
    inv = client.get("/investigator")
    assert inv.status_code == 200


def test_user_cannot_open_investigations_list(client):
    signup_and_login(client, "norole@example.com")
    resp = client.get("/investigations", follow_redirects=True)
    assert b"not authorized" in resp.data.lower() or resp.request.path != "/investigations"
