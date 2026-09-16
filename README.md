# SGE - Sistema de Gestão de Estoque

Sistema moderno e completo para controle de estoque físico, movimentações, ordens de compra, fornecedores, categorias, fechamentos contábeis mensais e relatórios gerenciais.

---

## 🏗️ Arquitetura e Stack Tecnológica

O sistema adota uma arquitetura híbrida de alto desempenho: **Frontend SPA desacoplado + Backend Django REST proprietário das regras de negócio**.

### Backend (Regras de Negócio & Persistência)
- **Python 3.13** & **Django 6**
- **SQLite** com integridade transacional (`transaction.atomic` + `select_for_update`)
- **API RESTful JSON** (`/api/v1/`) protegida por sessão e CSRF tokens
- **WhiteNoise** com `CompressedManifestStaticFilesStorage`
- **uv** como gerenciador rápido de pacotes e ambientes virtuais

### Frontend (SPA & Experiência do Usuário)
- **React 19** & **TypeScript**
- **Vite** para compilação ultrarrápida e HMR
- **Tailwind CSS** para design system coeso e responsivo
- **TanStack Query (React Query v5)** para cache, auto-refresh e sincronização de estado servidor
- **React Router v7** com roteamento SPA e persistência de estado na URL
- **Sonner** para toasts e notificações acessíveis
- **Lucide React** para iconografia consistente

### Infraestrutura & Deploy
- **Docker Multi-Stage Build**: Estágio 1 compila o frontend Node.js; Estágio 2 prepara o runtime Python otimizado
- **Gunicorn** como WSGI server em produção
- **Caddy** como reverse proxy com HTTPS automático

---

## ⚡ Recursos de Destaque & UX (v1.6.0)

- 🔍 **Command Palette Global (`Ctrl + K`)**: Busca instantânea de insumos por nome/fornecedor, atalhos para todas as páginas e ações rápidas sem sair da tela atual.
- ⚡ **Busca com Debounce (`useDebounce`)**: O usuário digita de forma fluida e instantânea; o backend só é consultado quando a digitação pausa (350ms), eliminando requisições redundantes.
- 🎯 **Navegação Sem "Piscadas" (`keepPreviousData`)**: Transição suave entre abas, filtros e páginas mantendo os dados anteriores visíveis durante o carregamento com barra de progresso discreta.
- 🔗 **Filtros e Paginação na URL (`useSearchParams`)**: Compartilhe links ou dê F5 sem perder os filtros ou a página selecionada.
- 🔄 **Dashboard em Tempo Real**: Métricas atualizadas automaticamente a cada 60s em segundo plano, com botão manual de atualização.
- 🛡️ **Exclusão Segura**: Operações destrutivas exigem confirmação explícita digitando `EXCLUIR`.
- ✨ **Feedback Visual de Alterações**: Destaque suave em verde (`emerald ring`) na linha da tabela do item recém-movimentado ou alterado.

---

## 📐 Regras de Negócio & Diretrizes de Código

### 1. Saldo e Unidade Base
- `Produto.quantidade_base` é a **fonte única da verdade** do saldo físico:
  - Tecidos e papéis: **metros**.
  - Tintas: **litros**.
  - Outros materiais: unidade cadastrada em `unidade_medida`.
- Rolos e vidros são **sempre projeções calculadas** para visualização (`embalagens_estimadas`), nunca saldo fixo.

### 2. Mutação de Estoque
- **Nunca** altere saldo de produtos diretamente em views ou páginas. Toda entrada ou saída física deve gerar um registro em `Movimentacao`.
- `Movimentacao.save()` valida quantidades estritamente positivas, roda sob `transaction.atomic()` com bloqueio pessimista (`select_for_update()`) e impede saídas sem saldo suficiente.
- Ações críticas de usuários geram auditoria automática em `LogAcao`.

### 3. Padrões do Frontend React
- Ao criar novos campos de busca em tabelas, sempre use o hook `useDebounce(busca, 350)`.
- Ao utilizar `useQuery` para listagens paginadas ou com filtros, sempre configure `placeholderData: keepPreviousData` e desestruture `isFetching` para indicar carregamento secundário sem apagar a tela.
- Mantenha valores e textos em **Português (pt-BR)** e use `Intl.NumberFormat` para valores monetários e quantidades formatadas.

---

## 🚀 Como Executar Localmente

### Pré-requisitos
- Python 3.13+ e [`uv`](https://docs.astral.sh/uv/)
- Node.js 20+ e `npm`

### 1. Configurar Backend (Django)
```bash
# Clone o repositório
git clone https://github.com/mrmateussiilva/sge.git
cd sge

# Sincronize o ambiente Python
uv sync

# Configure as variáveis de ambiente
cp .env.example .env

# Execute as migrations
uv run python manage.py migrate

# Inicie o servidor Django
uv run python manage.py runserver
```

### 2. Configurar Frontend (React SPA)
Em outro terminal:
```bash
cd frontend

# Instale as dependências
npm install

# Inicie o servidor Vite em modo desenvolvimento
npm run dev
```
O frontend estará acessível em `http://localhost:5173` conectando ao backend Django em `http://localhost:8000`.

---

## 🐳 Executando com Docker

O Dockerfile utiliza build multi-estágio automático:

```bash
docker compose up --build
```
O build compila o frontend React, executa `collectstatic`, aplica migrations no banco SQLite e inicia o Gunicorn em `http://localhost:8000`.

---

## 🧪 Testes Automatizados

Para rodar os testes unitários e de integração do backend:
```bash
uv run python manage.py test
```

Para validar a tipagem e compilação do frontend:
```bash
cd frontend
npm run build
```
