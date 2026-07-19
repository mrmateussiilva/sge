# SGE - Sistema de Gestao de Estoque

Sistema web para controle de estoque, movimentacoes, fornecedores, categorias, ordens de compra, fechamentos mensais e relatorios.

## Stack

- Python 3.13
- Django 6
- SQLite
- Bootstrap 5, Bootstrap Icons, HTMX, Vue global em paginas pontuais e Chart.js
- WhiteNoise para arquivos estaticos
- Docker, Gunicorn e Caddy para deploy

## Estrutura Principal

- `core/`: configuracao principal do Django.
- `estoque/`: app principal do sistema.
- `omie/`: app legado mantido apenas para migrations de remocao de tabelas antigas.
- `estoque/templates/estoque/`: templates das telas do sistema.
- `estoque/static/estoque/css/style.css`: CSS global.
- `data/db.sqlite3`: banco SQLite local.
- `PROJECT_CONTEXT.md`: contexto de dominio e regras principais.
- `AGENTS.md`: orientacoes para agentes de codigo trabalhando no repositorio.

## Requisitos

- Python 3.13+
- `uv`
- Docker e Docker Compose, caso use container

Instalacao do `uv`, se necessario:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Configuracao Local

Copie o arquivo de exemplo:

```bash
cp .env.example .env
```

Para desenvolvimento local, ajuste pelo menos:

```env
PORT=8000
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
```

Defina tambem `DJANGO_SECRET_KEY` e as variaveis de superusuario se for usar Docker.

## Rodando Localmente

Instale as dependencias:

```bash
uv sync
```

Aplique as migrations:

```bash
uv run python manage.py migrate
```

Crie um superusuario, se ainda nao existir:

```bash
uv run python manage.py createsuperuser
```

Inicie o servidor:

```bash
uv run python manage.py runserver
```

Acesse:

```text
http://127.0.0.1:8000/
```

## Rodando com Docker

Configure o `.env` e execute:

```bash
docker compose up --build
```

O servico sobe em:

```text
http://127.0.0.1:8000/
```

No boot do container, `entrypoint.sh` executa:

- `manage.py migrate --noinput`
- criacao de superusuario via variaveis de ambiente, se possivel
- `collectstatic --noinput`
- Gunicorn em `0.0.0.0:$PORT`

O banco SQLite do container fica persistido no volume `sqlite_data`.

## Comandos Uteis

Rodar testes:

```bash
uv run python manage.py test
```

Coletar arquivos estaticos:

```bash
uv run python manage.py collectstatic --noinput
```

Criar migrations apos alterar modelos:

```bash
uv run python manage.py makemigrations
```

Aplicar migrations:

```bash
uv run python manage.py migrate
```

Abrir shell Django:

```bash
uv run python manage.py shell
```

## Regras Importantes de Estoque

- `Produto.quantidade_base` e o saldo real.
- Tecidos e papeis usam metros como base.
- Tintas usam litros como base.
- Rolos e vidros sao estimativas calculadas para exibicao.
- Entradas e saidas operacionais devem passar por `Movimentacao`.
- `Movimentacao.save()` valida quantidade positiva, usa transacao e impede saida sem saldo.
- Fechamentos mensais geram snapshot historico do estoque.
- Acoes significativas devem ser registradas em `LogAcao`.

Para detalhes completos de dominio, consulte `PROJECT_CONTEXT.md`.

## Testes

A suite atual cobre fluxos de movimentacao, paginas operacionais, cadastro minimo de produto, fechamento mensal e exportacoes XLSX.

Execute antes de concluir mudancas em modelos, views, estoque, fechamento, importacao/exportacao ou autenticacao:

```bash
uv run python manage.py test
```

## Deploy

O deploy previsto usa Docker com Gunicorn atras de proxy reverso Caddy.

Arquivos relacionados:

- `Dockerfile`
- `docker-compose.yml`
- `entrypoint.sh`
- `Caddyfile.example`
- `.env.example`

Em producao:

- use `DJANGO_DEBUG=False`;
- configure `DJANGO_SECRET_KEY` com valor seguro;
- configure `DJANGO_ALLOWED_HOSTS`;
- configure `CSRF_TRUSTED_ORIGINS` com o dominio HTTPS;
- mantenha o volume SQLite persistente.

## Observacoes para Manutencao

- Nao commite `.env` nem dados sensiveis.
- Evite alterar diretamente `data/db.sqlite3` sem backup.
- Antes de mudancas de dominio, leia `PROJECT_CONTEXT.md` e `AGENTS.md`.
- Ao alterar UI, valide desktop e mobile, pois o sistema usa sidebar, bottom navigation, modais globais e navegacao HTMX.
