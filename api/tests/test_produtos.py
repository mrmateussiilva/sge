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
