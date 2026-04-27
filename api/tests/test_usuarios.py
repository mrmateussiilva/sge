import auth


def test_admin_can_list_usuarios(client, admin_headers, admin_user):
    response = client.get("/api/usuarios", headers=admin_headers)

    assert response.status_code == 200
    usuarios = response.json()
    assert len(usuarios) == 1
    assert usuarios[0]["email"] == admin_user.email


def test_non_admin_cannot_list_usuarios(client, db_session):
    usuario = auth.create_usuario(
        db_session,
        auth.schemas.UsuarioCreate(
            nome="Operador",
            email="operador@example.com",
            senha="secret123",
            perfil="operador",
        ),
    )

    login_response = client.post(
        "/api/auth/login",
        json={"email": usuario.email, "senha": "secret123"},
    )
    token = login_response.json()["access_token"]

    response = client.get(
        "/api/usuarios",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Acesso restrito a administradores."
