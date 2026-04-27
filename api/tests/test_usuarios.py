import auth
import schemas


def test_admin_can_list_usuarios(client, admin_headers, admin_user):
    response = client.get("/api/usuarios", headers=admin_headers)

    assert response.status_code == 200
    usuarios = response.json()
    assert len(usuarios) == 1
    assert usuarios[0]["email"] == admin_user.email


def test_non_admin_cannot_list_usuarios(client, db_session):
    usuario = auth.create_usuario(
        db_session,
        schemas.UsuarioCreate(
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


def test_usuarios_require_authentication(client):
    response = client.get("/api/usuarios")
    assert response.status_code == 401


def test_register_new_user(client, db_session):
    response = client.post(
        "/api/auth/register",
        json={
            "nome": "Novo Usuario",
            "email": "novo@example.com",
            "senha": "senha123",
        },
    )

    assert response.status_code == 201
    assert response.json()["email"] == "novo@example.com"
    assert response.json()["perfil"] in ["operador", "admin"]


def test_register_first_user_becomes_admin(client, db_session):
    response = client.post(
        "/api/auth/register",
        json={
            "nome": "Primeiro Admin",
            "email": "primeiro@example.com",
            "senha": "senha123",
        },
    )

    assert response.status_code == 201
    assert response.json()["perfil"] == "admin"


def test_register_rejects_duplicate_email(client, admin_user):
    response = client.post(
        "/api/auth/register",
        json={
            "nome": "Outro Usuario",
            "email": admin_user.email,
            "senha": "senha123",
        },
    )

    assert response.status_code == 400
    assert "ja cadastrado" in response.json()["detail"].lower()


def test_admin_can_update_usuario(client, admin_headers, db_session):
    usuario = auth.create_usuario(
        db_session,
        schemas.UsuarioCreate(
            nome="Usuario Original",
            email="original@example.com",
            senha="senha123",
            perfil="operador",
        ),
    )

    response = client.put(
        f"/api/usuarios/{usuario.id}",
        headers=admin_headers,
        json={
            "nome": "Usuario Atualizado",
            "email": "original@example.com",
            "perfil": "operador",
            "ativo": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["nome"] == "Usuario Atualizado"
    assert response.json()["ativo"] is False
