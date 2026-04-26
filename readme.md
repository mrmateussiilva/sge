# SGE

Frontend estatico em `public/` e API FastAPI em `api/`.

## Deploy do frontend no GitHub Pages

1. Edite `public/js/config.js`
2. Troque `https://SEU-BACKEND-NA-VERCEL.vercel.app/api` pela URL real da API
3. Envie para a branch `main`
4. No GitHub, abra `Settings > Pages`
5. Em `Source`, selecione `GitHub Actions`
6. Aguarde o workflow `Deploy Frontend to GitHub Pages`

Arquivos importantes:

- `public/index.html`: app principal
- `public/login.html`: tela de login
- `public/404.html`: redireciona rotas amigaveis no Pages
- `.github/workflows/deploy-pages.yml`: deploy automatico do frontend

## Deploy da API na Vercel

Mantenha a API publicada na Vercel com as variaveis:

- `DATABASE_URL`
- `SECRET_KEY`

O frontend faz requisicoes para a URL definida em `public/js/config.js`.

## Observacoes

- Os assets do frontend usam caminhos relativos para funcionar em subpastas do GitHub Pages.
- O backend ja aceita requisicoes cross-origin com token Bearer.
