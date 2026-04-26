# SGE

Frontend estatico em `public/` e API FastAPI em `api/`.

## Deploy do frontend na Vercel

Configure o projeto da Vercel com:

- `Root Directory`: `public`
- `Framework Preset`: `Other`

Defina a variavel:

- `SGE_API_BASE_URL`

Exemplo:

- `SGE_API_BASE_URL=https://seu-backend-na-vercel.vercel.app/api`

Durante o build, o arquivo `js/config.js` e gerado automaticamente com esse valor.

Arquivos importantes:

- `public/index.html`: app principal
- `public/login.html`: tela de login
- `public/js/config.js`: configuracao consumida pelo navegador
- `public/scripts/build-frontend-config.mjs`: gera `js/config.js` no deploy
- `vercel.json`: configuracao de build para projeto com root em `public`

## Deploy da API na Vercel

Mantenha a API publicada na Vercel com as variaveis:

- `DATABASE_URL`
- `SECRET_KEY`

## Desenvolvimento local

Localmente, `public/js/config.js` aponta por padrao para:

- `http://127.0.0.1:8000/api`

Se quiser testar o frontend contra outra API, altere esse arquivo localmente ou gere-o manualmente:

```bash
cd public
SGE_API_BASE_URL=https://seu-backend.vercel.app/api node scripts/build-frontend-config.mjs
```

## Observacoes

- O frontend usa hash routing, entao nao precisa de rewrites de SPA na Vercel.
- O backend ja aceita requisicoes cross-origin com token Bearer.
