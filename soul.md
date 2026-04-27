# Resolucao do erro `FUNCTION_INVOCATION_FAILED` na Vercel

## Problema

O backend FastAPI publicado na Vercel caiu com erro `500: INTERNAL_SERVER_ERROR` e `FUNCTION_INVOCATION_FAILED`.

## Causa raiz

O arquivo `api/routers/importacao_xml.py` importava `httpx` no carregamento do modulo.

Na configuracao atual, a Vercel publica a API com `Root Directory = api`, entao ela instala apenas as dependencias de runtime declaradas em `api/pyproject.toml`.

`httpx` estava declarado apenas no grupo `dev`, mas era usado por codigo de producao. Isso faz a funcao falhar antes mesmo do FastAPI subir, porque o import acontece no startup da aplicacao.

## Correcao aplicada

Foram feitas duas mudancas:

1. `httpx` foi movido para `dependencies` em `api/pyproject.toml`.
2. O import de `httpx` em `api/routers/importacao_xml.py` passou a ser lazy, dentro da rota `/importacao/xml/download`.

Com isso:

- a dependencia passa a ser instalada no deploy da Vercel;
- uma ausencia futura dessa lib nao derruba toda a API no startup;
- o erro fica isolado na funcionalidade afetada.

## Regra para qualquer alteracao futura no backend

Sempre que uma nova biblioteca for usada por qualquer rota, servico, router, middleware ou codigo executado no startup da API:

1. adicione essa biblioteca em `api/pyproject.toml` dentro de `dependencies`;
2. nao deixe bibliotecas de producao apenas em `[dependency-groups].dev`;
3. trate imports opcionais de forma lazy quando a funcionalidade nao precisa impedir o boot da API;
4. evite codigo pesado ou fragil em import de modulo;
5. considere que a Vercel precisa conseguir iniciar a app mesmo se uma funcionalidade secundaria falhar.

## Checklist obrigatorio antes de subir alteracoes no backend

1. Verificar se toda dependencia usada em producao esta em `api/pyproject.toml`.
2. Rodar os testes do backend, preferencialmente com:

```bash
cd api
uv sync --group dev
uv run pytest
```

3. Confirmar que o backend continua iniciando sem depender de imports opcionais no carregamento global.
4. Se houver mudanca de dependencia, atualizar tambem o lockfile local com `uv lock`.
5. Depois do deploy, validar pelo menos:

```text
/api
/api/health
```

## Observacao sobre deploy

Este projeto assume:

- `Root Directory` da API na Vercel apontando para `api`;
- variaveis `DATABASE_URL` e `SECRET_KEY` configuradas;
- instalacao baseada no `api/pyproject.toml`.

Se esse modelo mudar, a documentacao e o processo de deploy precisam ser revistos junto com o backend.
