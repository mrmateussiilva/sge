# AGENTS.md

Orientacoes para agentes trabalhando neste repositorio.

## Visao Geral

- Projeto: SGE, um Sistema de Gestao de Estoque em Django.
- Stack principal: Python 3.13, Django 6, SQLite, templates Django, Bootstrap 5, HTMX, Vue global em paginas pontuais, Chart.js e CSS vanilla.
- Apps Django:
  - `estoque`: app principal, com modelos, views, templates, estaticos, logs e testes.
  - `omie`: app legado mantido apenas para migrations de remocao de tabelas antigas. Nao adicione novas regras de negocio nele sem motivo explicito.
- Banco padrao: `data/db.sqlite3`.
- Idioma/timezone da aplicacao: `pt-br` e `America/Sao_Paulo`.

Leia tambem `PROJECT_CONTEXT.md` antes de mudancas relevantes de dominio.

## Comandos

Use `uv` como gerenciador do projeto.

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
uv run python manage.py test
uv run python manage.py collectstatic --noinput
```

Para Docker:

```bash
docker compose up --build
```

O container executa migrations, tenta criar o superusuario com variaveis de ambiente, coleta estaticos e sobe Gunicorn via `entrypoint.sh`.

## Configuracao

- Variaveis esperadas ficam em `.env.example`.
- Nao commite segredos reais de `.env`.
- Em producao, `DJANGO_DEBUG=False`; confira `DJANGO_ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS`.
- WhiteNoise serve estaticos com `CompressedManifestStaticFilesStorage`.

## Arquitetura e Pontos de Entrada

- Configuracao Django: `core/settings.py`.
- URLs globais: `core/urls.py`.
- URLs de estoque: `estoque/urls.py`.
- Modelos principais: `estoque/models.py`.
- Views principais: `estoque/views.py`.
- Templates: `estoque/templates/estoque/` e `templates/registration/`.
- CSS principal: `estoque/static/estoque/css/style.css`.
- Auditoria: `estoque/log_utils.py`.
- Signals: `estoque/signals.py`, carregado por `EstoqueConfig.ready()`.
- Testes existentes: `estoque/tests.py`.

## Regras de Dominio Criticas

- `Produto.quantidade_base` e o saldo real do item. Use sempre a unidade base:
  - tecido/papel: metros;
  - tinta: litros;
  - demais tipos: unidade definida em `unidade_medida`.
- Rolo e vidro sao apenas exibicoes calculadas:
  - `quantidade_rolos_estimada`;
  - `quantidade_vidros_estimada`.
- Nao atualize saldo de estoque diretamente em views ou templates quando a alteracao representa entrada/saida operacional. Use `Movimentacao` ou preserve a mesma semantica transacional.
- `Movimentacao.save()` normaliza quantidade, exige valor positivo, usa `transaction.atomic()` e `select_for_update()`, e impede `SAIDA` sem saldo.
- Ao excluir uma movimentacao, preserve a reversao correta do saldo no produto.
- Ordem de compra:
  - `PENDENTE`: pode ser editada;
  - `APROVADA`: bloqueia edicao;
  - `RECEBIDA`: gera entradas de estoque para os itens;
  - `CANCELADA`: finaliza sem impacto no estoque.
- Fechamento mensal cria snapshot historico. `ItemFechamento` deve copiar descricao, quantidade e precos do momento do fechamento, pois o produto pode mudar ou ser excluido depois.
- Alteracoes significativas feitas por usuario devem registrar auditoria com `log_acao(usuario, acao, descricao, modelo, objeto_id)`.

## Padroes de Codigo

- Mantenha views protegidas com `@login_required`, seguindo o padrao atual.
- Mutacoes feitas via endpoints usados pelo frontend normalmente retornam `JsonResponse` no formato `{'ok': True}` ou `{'ok': False, 'erro': '...'}` com status HTTP adequado.
- Use `Decimal` para quantidades e valores monetarios. Evite `float` em calculos de dominio.
- Use `transaction.atomic()` e, quando houver concorrencia sobre estoque, `select_for_update()`.
- Para novas mudancas de modelo, gere migrations Django e revise se dados existentes precisam de migracao segura.
- Evite refatorar `estoque/views.py` inteiro em tarefas pequenas; ele e grande e central, entao prefira alteracoes localizadas.
- Preserve nomes, mensagens e formatos em portugues nas telas e respostas ao usuario.

## Frontend

- A UI usa templates Django com Bootstrap Icons, Bootstrap 5, HTMX global (`hx-boost`) e scripts inline em templates.
- O conteudo principal e trocado em `#main-content`; ao adicionar scripts por pagina, confira comportamento com navegação HTMX.
- Estilos globais ficam em `estoque/static/estoque/css/style.css`; mantenha consistencia com cards, tabelas, tema claro/escuro e layout responsivo existentes.
- Nao introduza frameworks de frontend ou build steps sem necessidade clara.

## Testes e Verificacao

- Rode `uv run python manage.py test` apos alterar modelos, views, fluxos de estoque, fechamento, importacao/exportacao ou autenticacao.
- Para mudancas em arquivos estaticos ou templates, alem dos testes, verifique manualmente as paginas afetadas com `uv run python manage.py runserver`.
- Ao mexer em exports XLSX/CSV, valide content type, nome de arquivo e estrutura basica do arquivo.
- Ao mexer em migrations, rode `uv run python manage.py migrate` em uma base local.

## Dados e Arquivos Locais

- `data/db.sqlite3`, `.env`, `estoque.xlsx` e arquivos de importacao local podem conter dados de ambiente. Nao os altere ou remova sem pedido explicito.
- `importar_estoque.py` e utilitario de importacao inicial baseado em planilha; trate como script operacional, nao como codigo de runtime web.
- `README.md` esta vazio no momento; nao assuma que ele documenta o projeto.

## Cuidados Antes de Finalizar

- Confira `git status --short` para separar suas mudancas de alteracoes preexistentes do usuario.
- Nao reverta alteracoes que voce nao fez.
- Se mudar regra de estoque, adicione ou ajuste teste cobrindo saldo, validacao e auditoria quando aplicavel.
- Se mudar UI de fluxo operacional, confira desktop e mobile, pois ha sidebar, bottom navigation e modais globais.
