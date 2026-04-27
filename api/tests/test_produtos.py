def test_produtos_require_authentication(client):
    response = client.get("/api/produtos")

    assert response.status_code == 401


def test_create_and_list_produtos(client, admin_headers):
    create_response = client.post(
        "/api/produtos",
        headers=admin_headers,
        json={
            "nome": "Mouse",
            "sku": "MOU-001",
            "categoria": "Perifericos",
            "unidade": "UN",
            "custo": "50.00",
            "preco": "90.00",
            "estoque_atual": 8,
            "estoque_minimo": 2,
            "localizacao": "A1",
        },
    )

    assert create_response.status_code == 201
    produto = create_response.json()
    assert produto["sku"] == "MOU-001"

    list_response = client.get("/api/produtos", headers=admin_headers)

    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_create_produto_rejects_duplicate_sku(client, admin_headers):
    payload = {
        "nome": "Teclado",
        "sku": "TEC-001",
        "categoria": "Perifericos",
        "unidade": "UN",
        "custo": "80.00",
        "preco": "120.00",
        "estoque_atual": 3,
        "estoque_minimo": 1,
        "localizacao": "B1",
    }

    first_response = client.post("/api/produtos", headers=admin_headers, json=payload)
    second_response = client.post("/api/produtos", headers=admin_headers, json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 400
    assert second_response.json()["detail"] == "SKU ja cadastrado."


def test_update_produto(client, admin_headers):
    create_response = client.post(
        "/api/produtos",
        headers=admin_headers,
        json={
            "nome": "Monitor",
            "sku": "MON-001",
            "categoria": "Eletronicos",
            "unidade": "UN",
            "custo": "500.00",
            "preco": "900.00",
            "estoque_atual": 5,
            "estoque_minimo": 2,
            "localizacao": "C1",
        },
    )
    assert create_response.status_code == 201
    produto_id = create_response.json()["id"]

    update_response = client.put(
        f"/api/produtos/{produto_id}",
        headers=admin_headers,
        json={
            "nome": "Monitor Atualizado",
            "sku": "MON-001",
            "categoria": "Eletronicos",
            "unidade": "UN",
            "custo": "550.00",
            "preco": "950.00",
            "estoque_atual": 10,
            "estoque_minimo": 3,
            "localizacao": "C2",
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["nome"] == "Monitor Atualizado"
    assert update_response.json()["preco"] == "950.00"


def test_delete_produto(client, admin_headers):
    create_response = client.post(
        "/api/produtos",
        headers=admin_headers,
        json={
            "nome": "Produto para deletar",
            "sku": "DEL-001",
            "categoria": "Teste",
            "unidade": "UN",
            "custo": "10.00",
            "preco": "20.00",
            "estoque_atual": 1,
            "estoque_minimo": 0,
            "localizacao": "Z1",
        },
    )
    assert create_response.status_code == 201
    produto_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/produtos/{produto_id}", headers=admin_headers)
    assert delete_response.status_code == 204

    get_response = client.get(f"/api/produtos/{produto_id}", headers=admin_headers)
    assert get_response.status_code == 404


def test_get_single_produto(client, admin_headers):
    create_response = client.post(
        "/api/produtos",
        headers=admin_headers,
        json={
            "nome": "Webcam",
            "sku": "WEB-001",
            "categoria": "Perifericos",
            "unidade": "UN",
            "custo": "120.00",
            "preco": "200.00",
            "estoque_atual": 15,
            "estoque_minimo": 5,
            "localizacao": "D1",
        },
    )
    assert create_response.status_code == 201
    produto_id = create_response.json()["id"]

    get_response = client.get(f"/api/produtos/{produto_id}", headers=admin_headers)
    assert get_response.status_code == 200
    assert get_response.json()["sku"] == "WEB-001"


def test_create_produto_with_minimal_fields(client, admin_headers):
    response = client.post(
        "/api/produtos",
        headers=admin_headers,
        json={
            "nome": "Produto Minimo",
            "sku": "MIN-001",
            "unidade": "UN",
            "custo": "10.00",
            "preco": "15.00",
        },
    )
    assert response.status_code == 201
    produto = response.json()
    assert produto["estoque_atual"] == 0
    assert produto["estoque_minimo"] == 0
