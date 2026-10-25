from tests.conftest import login_headers

REG = {"name": "Asha", "email": "asha@example.com", "password": "password123"}


def test_register_success_hides_password(client):
    res = client.post("/auth/register", json=REG)
    assert res.status_code == 201
    assert "password" not in str(res.json()).lower()


def test_duplicate_email_rejected(client):
    client.post("/auth/register", json=REG)
    assert client.post("/auth/register", json=REG).status_code == 409


def test_invalid_input_rejected(client):
    assert client.post("/auth/register", json={**REG, "email": "bad"}).status_code == 422
    assert client.post("/auth/register", json={**REG, "password": "short"}).status_code == 422
    assert client.post("/auth/register", json={"email": "x@y.com"}).status_code == 422


def test_login_wrong_password(client):
    client.post("/auth/register", json=REG)
    res = client.post("/auth/login", data={"username": REG["email"], "password": "wrongpass1"})
    assert res.status_code == 401


def test_protected_routes_need_token(client):
    for path in ("/auth/me", "/jobs", "/resume", "/applications"):
        assert client.get(path).status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_me_returns_current_user(client, headers):
    assert client.get("/auth/me", headers=headers).json()["email"] == "a@example.com"
