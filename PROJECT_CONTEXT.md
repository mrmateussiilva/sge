# SGE — Sistema de Gestão de Estoque | Contexto do Projeto

## Stack

- **Backend:** Django (Python 3.12+) — app única chamada `estoque`
- **Banco de dados:** SQLite (arquivo em `data/db.sqlite3`)
- **Autenticação:** `django.contrib.auth` padrão (User nativo do Django)
- **Frontend:** HTML + CSS vanilla (sem framework JS) com templates Django
- **Arquivos estáticos:** servidos via WhiteNoise
- **Deploy:** Docker + Caddy (proxy reverso HTTPS)
- **Idioma/Timezone:** pt-BR / America/Sao_Paulo

---

## Modelos de dados (`estoque/models.py`)

### `Categoria`
Agrupa produtos por categoria visual.
```
nome (str, unique)
descricao (str)
cor (str, hex — ex: #ff5733)
```

### `Fornecedor`
Representa um fornecedor de produtos.
```
nome (str)
cnpj (str)
email (str)
telefone (str)
observacao (str)
```

### `Produto`
Entidade central do sistema. Representa um item do estoque.
```
tipo_produto: TECIDO | PAPEL | TINTA | AVIAMENTO | OUTRO
unidade_medida: UN | M | KG | L | RL | CX | PC | G | ML | OUTRO
descricao (str)
categoria → FK Categoria
fornecedor → FK Fornecedor

quantidade_base (Decimal)  ← saldo atual, alterado via Movimentacao
metros_por_rolo (Decimal, nullable) ← para tecidos/papéis
tipo_tinta: SUBLIMACAO | SOLVENTE | N/A
cor_tinta: CYAN | MAGENTA | YELLOW | BLACK | LIGHT_CYAN | LIGHT_MAGENTA | BRANCO | INCOLOR
litros_por_vidro (Decimal, nullable) ← para tintas

preco_custo (Decimal)
preco_venda (Decimal)
estoque_minimo (Decimal)
```
**Properties calculadas:**
- `quantidade_rolos_estimada` → `quantidade_base / metros_por_rolo`
- `quantidade_vidros_estimada` → `quantidade_base / litros_por_vidro`

### `Movimentacao`
Registra entradas e saídas de estoque. **Atualiza `quantidade_base` do Produto atomicamente no `save()`.**
```
produto → FK Produto
usuario → FK User
tipo: ENTRADA | SAIDA
quantidade (Decimal)
data (auto_now_add)
observacao (str)
```
> Regra: SAIDA valida se há saldo suficiente; caso contrário lança `ValidationError`.

### `HistoricoPreco`
Gravado automaticamente via **signal** (`post_save` em `Produto`) toda vez que `preco_custo` ou `preco_venda` mudar.
```
produto → FK Produto
preco_custo_antigo / preco_custo_novo (Decimal)
preco_venda_antigo / preco_venda_novo (Decimal)
data (auto_now_add)
usuario → FK User
```

### `OrdemCompra`
Pedido de compra ao fornecedor.
```
fornecedor → FK Fornecedor
data_criacao (auto_now_add)
status: PENDENTE | APROVADA | RECEBIDA | CANCELADA
observacao (str)
```

### `ItemOrdemCompra`
Itens de uma `OrdemCompra` (relação N:1).
```
ordem → FK OrdemCompra (related_name='itens')
produto → FK Produto
quantidade (Decimal)
preco_unitario (Decimal)
```
> Ao **receber** a ordem, cada item gera uma `Movimentacao` de ENTRADA.

### `LogAcao`
Trilha de auditoria de ações do usuário.
```
usuario → FK User
acao: CRIAR | EDITAR | EXCLUIR | ENTRADA | SAIDA | APROVAR | CANCELAR | RECEBER
descricao (str, max 500)
modelo (str) ← nome do model afetado
objeto_id (int) ← PK do objeto afetado
data (auto_now_add)
```

### `FechamentoMensal`
Snapshot mensal do estoque para relatórios/auditoria.
```
data_fechamento (auto_now_add)
usuario → FK User
referencia_mes_ano (str, unique, formato "MM/AAAA")
observacao (str)
```

### `ItemFechamento`
Linha do snapshot — cópia dos dados do produto no momento do fechamento.
```
fechamento → FK FechamentoMensal (related_name='itens')
produto → FK Produto (nullable — produto pode ser excluído depois)
descricao (str) ← cópia da descrição no momento
quantidade (Decimal)
preco_custo (Decimal)
preco_venda (Decimal)
```

---

## Fluxos principais

### Entrada/Saída de estoque
`Movimentacao.save()` → dentro de `transaction.atomic()` faz `select_for_update()` no Produto, atualiza `quantidade_base`, salva o Produto e depois a própria Movimentacao.

### Atualização de preço
`Produto.save()` → signal `post_save` (`signals.py`) compara preços antigos com novos e, se houver mudança, cria `HistoricoPreco`.

### Importação de NF-e
`xml_parser.parse_nfe_xml()` → lê XML SEFAZ (suporta `<nfeProc>` e `<NFe>` direto) → retorna dict com `numero_nf`, `fornecedor` (nome + CNPJ) e `itens[]`. A view exibe uma tela de confirmação antes de criar Produtos/Movimentações.

### Fechamento mensal
View `realizar_fechamento` → itera todos os Produtos ativos → cria `FechamentoMensal` + `ItemFechamento` por produto → exportável em XLSX.

### Ordem de compra
- **PENDENTE** → usuário edita itens
- **APROVADA** → bloqueada para edição
- **RECEBIDA** → gera Movimentacoes de ENTRADA para cada ItemOrdemCompra
- **CANCELADA** → encerrada sem efeito no estoque

---

## Convenções do código

- Toda ação significativa chama `log_utils.registrar_log(usuario, acao, descricao, modelo, objeto_id)` que cria um `LogAcao`.
- Views em `estoque/views.py` (arquivo único, ~1600 linhas) — todas com `@login_required`.
- Contexto global injeta `produtos_estoque_baixo` (via `context_processors.estoque_baixo`) para exibir alerta no header.
- Unidades de medida da NF-e são mapeadas para os códigos internos via `xml_parser._map_unidade_medida()`.
- O campo `quantidade_base` **sempre** representa a unidade base do produto (metros para tecido/papel, litros para tinta, unidades para o restante). Quantidades em rolos/vidros são apenas propriedades calculadas para exibição.
