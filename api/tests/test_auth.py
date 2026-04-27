def test_register_first_user_becomes_admin(client):
    response = client.post(
        "/api/auth/register",
        json={
            "nome": "Primeiro Usuario",
            "email": "primeiro@example.com",
            "senha": "secret123",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["perfil"] == "admin"
    assert body["email"] == "primeiro@example.com"


def test_login_and_get_current_user(client, admin_user):
    login_response = client.post(
        "/api/auth/login",
        json={"email": admin_user.email, "senha": "secret123"},
    )

    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["email"] == admin_user.email


def test_login_rejects_invalid_password(client, admin_user):
    response = client.post(
        "/api/auth/login",
        json={"email": admin_user.email, "senha": "senha-errada"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Email ou senha invalidos."
