def test_create_movimentacao_updates_stock(client, admin_headers):
    produto_response = client.post(
        "/api/produtos",
        headers=admin_headers,
        json={
            "nome": "Monitor",
            "sku": "MON-001",
            "categoria": "Video",
            "unidade": "UN",
            "custo": "500.00",
            "preco": "750.00",
            "estoque_atual": 10,
            "estoque_minimo": 2,
            "localizacao": "C1",
        },
    )
    produto_id = produto_response.json()["id"]

    movimentacao_response = client.post(
        "/api/movimentacoes",
        headers=admin_headers,
        json={
            "produto_id": produto_id,
            "tipo": "saida",
            "quantidade": 4,
            "motivo": "Pedido",
        },
    )

    assert movimentacao_response.status_code == 201
    assert movimentacao_response.json()["produto"]["estoque_atual"] == 6

    produto_atualizado = client.get(f"/api/produtos/{produto_id}", headers=admin_headers)
    assert produto_atualizado.status_code == 200
    assert produto_atualizado.json()["estoque_atual"] == 6


def test_saida_rejects_insufficient_stock(client, admin_headers):
    produto_response = client.post(
        "/api/produtos",
        headers=admin_headers,
        json={
            "nome": "Notebook",
            "sku": "NOT-001",
            "categoria": "Informatica",
            "unidade": "UN",
            "custo": "2500.00",
            "preco": "3200.00",
            "estoque_atual": 1,
            "estoque_minimo": 1,
            "localizacao": "D1",
        },
    )
    produto_id = produto_response.json()["id"]

    response = client.post(
        "/api/movimentacoes",
        headers=admin_headers,
        json={
            "produto_id": produto_id,
            "tipo": "saida",
            "quantidade": 2,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Estoque insuficiente para a saida."
