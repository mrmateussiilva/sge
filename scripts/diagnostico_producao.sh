#!/usr/bin/env bash

# Diagnóstico somente leitura do deploy Django/Docker e dos arquivos estáticos.
# Não executa git pull, build, restart nem collectstatic real.

set -u
set -o pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_PATH="${PROJECT_PATH:-$(cd -- "$SCRIPT_DIR/.." && pwd)}"
PUBLIC_URL="${1:-${PUBLIC_URL:-https://sge.finderbit.com.br}}"
SERVICE="${2:-${COMPOSE_SERVICE:-sge}}"
PUBLIC_URL="${PUBLIC_URL%/}"
PUBLIC_HOST="${PUBLIC_HOST:-$(printf '%s\n' "$PUBLIC_URL" | sed -E 's#^[a-zA-Z][a-zA-Z0-9+.-]*://([^/:]+).*#\1#')}"
LOCAL_CURL_HEADERS=(-H "Host: $PUBLIC_HOST" -H 'X-Forwarded-Proto: https')
EXPECTED_FIX_COMMIT="1b9400a"
STATIC_RELATIVE_PATH="estoque/css/layout.css"
TMP_DIR="$(mktemp -d /tmp/sge-diagnostico.XXXXXX)"
ISSUES=0

cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

section() {
    printf '\n=== %s ===\n' "$1"
}

ok() {
    printf '[OK] %s\n' "$1"
}

warn() {
    printf '[ATENÇÃO] %s\n' "$1"
    ISSUES=1
}

info() {
    printf '[INFO] %s\n' "$1"
}

if ! cd "$PROJECT_PATH" 2>/dev/null; then
    printf '[ERRO] Não foi possível acessar PROJECT_PATH=%s\n' "$PROJECT_PATH"
    exit 2
fi

printf 'Diagnóstico do SGE\n'
printf 'Projeto: %s\n' "$PWD"
printf 'Serviço Docker: %s\n' "$SERVICE"
printf 'URL pública: %s\n' "$PUBLIC_URL"

section '1. Git e versão do código'

if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    LOCAL_COMMIT="$(git rev-parse HEAD 2>/dev/null || true)"
    LOCAL_VERSION="$(sed -n "s/^[[:space:]]*APP_VERSION[[:space:]]*=[[:space:]]*['\"]\([^'\"]*\)['\"].*/\1/p" core/settings.py 2>/dev/null | head -n 1)"
    PROJECT_VERSION="$(sed -n 's/^[[:space:]]*version[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' pyproject.toml 2>/dev/null | head -n 1)"

    printf 'HEAD local: %s\n' "${LOCAL_COMMIT:-indisponível}"
    git log -1 --oneline --decorate 2>/dev/null || true
    printf 'APP_VERSION local: %s\n' "${LOCAL_VERSION:-indisponível}"
    printf 'Versão pyproject: %s\n' "${PROJECT_VERSION:-indisponível}"

    if git cat-file -e "$EXPECTED_FIX_COMMIT^{commit}" 2>/dev/null && \
       git merge-base --is-ancestor "$EXPECTED_FIX_COMMIT" HEAD 2>/dev/null; then
        ok "O commit $EXPECTED_FIX_COMMIT está presente no histórico atual."
    else
        warn "O commit $EXPECTED_FIX_COMMIT não está presente como ancestral do HEAD."
    fi

    REMOTE_REF="$(git ls-remote origin refs/heads/main 2>/dev/null || true)"
    REMOTE_COMMIT="$(printf '%s\n' "$REMOTE_REF" | awk '{print $1}')"
    if [ -n "$REMOTE_COMMIT" ]; then
        printf 'origin/main remoto: %s\n' "$REMOTE_COMMIT"
        if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ]; then
            ok 'O checkout local está alinhado com origin/main.'
        else
            warn 'O checkout local está diferente de origin/main.'
        fi
    else
        warn 'Não foi possível consultar origin/main.'
    fi
else
    warn 'Git não está disponível ou o diretório não é um checkout Git.'
fi

section '2. Docker e container'

DOCKER_AVAILABLE=0
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    DOCKER_AVAILABLE=1
    docker compose ps 2>&1 || warn 'Não foi possível listar os serviços Docker Compose.'
    docker compose images 2>&1 || warn 'Não foi possível listar as imagens do Compose.'

    CONTAINER_ID="$(docker compose ps -q "$SERVICE" 2>/dev/null | head -n 1)"
    if [ -n "$CONTAINER_ID" ]; then
        docker inspect "$CONTAINER_ID" \
            --format 'container={{.Id}} image={{.Image}} criado={{.Created}} iniciado={{.State.StartedAt}} status={{.State.Status}}' \
            2>&1 || warn 'Não foi possível inspecionar o container.'
    else
        warn "Não foi encontrado container para o serviço $SERVICE."
    fi
else
    warn 'Docker Compose não está disponível ou não há permissão para acessar o Docker daemon.'
fi

compose_exec() {
    docker compose exec -T "$SERVICE" "$@"
}

CONTAINER_PYTHON_CMD=(uv run python)

if [ "$DOCKER_AVAILABLE" -eq 1 ] && [ -n "${CONTAINER_ID:-}" ]; then
    section '3. Versão e health check do container'

    HEALTH_LOCAL="$(curl -fsS "${LOCAL_CURL_HEADERS[@]}" --max-time 10 http://127.0.0.1:8000/health/ 2>&1 || true)"
    if [ -n "$HEALTH_LOCAL" ]; then
        printf 'Health local: %s\n' "$HEALTH_LOCAL"
        HEALTH_VERSION="$(printf '%s' "$HEALTH_LOCAL" | sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)"
        if [ -n "${LOCAL_VERSION:-}" ] && [ "$HEALTH_VERSION" = "$LOCAL_VERSION" ]; then
            ok 'A versão informada pelo container coincide com APP_VERSION do checkout.'
        else
            warn 'A versão do health check não coincide com a versão do checkout.'
        fi
    else
        warn 'O endpoint local /health/ não respondeu.'
    fi

    CONTAINER_VERSION="$(compose_exec "${CONTAINER_PYTHON_CMD[@]}" -c 'import os; os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings"); import django; django.setup(); from django.conf import settings; print(settings.APP_VERSION)' 2>/dev/null || true)"
    printf 'APP_VERSION no container: %s\n' "${CONTAINER_VERSION:-indisponível}"
    if [ -n "${LOCAL_VERSION:-}" ] && [ "$CONTAINER_VERSION" = "$LOCAL_VERSION" ]; then
        ok 'APP_VERSION do container coincide com o checkout da VPS.'
    else
        warn 'APP_VERSION do container difere do checkout da VPS ou não foi obtida.'
    fi

    section '4. Configuração efetiva de estáticos'

    STATIC_CONFIG_CODE='import os; os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings"); import django; django.setup(); from django.conf import settings; print("STATIC_URL=" + str(settings.STATIC_URL)); print("STATIC_ROOT=" + str(settings.STATIC_ROOT)); print("STATICFILES_STORAGE=" + str(getattr(settings, "STATICFILES_STORAGE", None))); print("STORAGES_STATICFILES_BACKEND=" + str(settings.STORAGES.get("staticfiles", {}).get("BACKEND", "")))'
    compose_exec "${CONTAINER_PYTHON_CMD[@]}" -c "$STATIC_CONFIG_CODE" 2>&1 || warn 'Não foi possível ler a configuração Django dentro do container.'

    section '5. Cópias do layout.css dentro do container'

    compose_exec find /app -type f -name 'layout.css' -print 2>/dev/null || warn 'Não foi possível procurar layout.css no container.'

    SOURCE_CONTAINER_HASH="$(compose_exec sha256sum /app/estoque/static/estoque/css/layout.css 2>/dev/null | awk '{print $1}' || true)"
    COLLECTED_CONTAINER_HASH="$(compose_exec sha256sum /app/staticfiles/estoque/css/layout.css 2>/dev/null | awk '{print $1}' || true)"
    printf 'Código fonte no container: %s\n' "${SOURCE_CONTAINER_HASH:-indisponível}"
    printf 'STATIC_ROOT no container: %s\n' "${COLLECTED_CONTAINER_HASH:-indisponível}"

    if [ -n "$SOURCE_CONTAINER_HASH" ] && [ -n "$COLLECTED_CONTAINER_HASH" ]; then
        if [ "$SOURCE_CONTAINER_HASH" = "$COLLECTED_CONTAINER_HASH" ]; then
            ok 'A cópia coletada coincide com a cópia fonte dentro do container.'
        else
            warn 'A cópia em STATIC_ROOT está diferente da cópia fonte dentro do container.'
        fi
    else
        warn 'Não foi possível comparar as cópias fonte e coletada no container.'
    fi

    compose_exec sh -c "grep -nE 'position: fixed|bottom: 0|left: 0' /app/staticfiles/estoque/css/layout.css" 2>&1 || \
        warn 'O layout.css coletado não possui todas as regras esperadas da correção.'

    section '6. collectstatic em modo dry-run'

    COLLECTSTATIC_OUTPUT="$(compose_exec "${CONTAINER_PYTHON_CMD[@]}" manage.py collectstatic --noinput --dry-run --verbosity 1 2>&1 || true)"
    printf '%s\n' "$COLLECTSTATIC_OUTPUT" | tail -n 30

    section '7. Headers e CSS servido pelo container'

    curl -fsS "${LOCAL_CURL_HEADERS[@]}" -H 'Accept-Encoding: identity' -H 'Cache-Control: no-cache' \
        --max-time 10 \
        -D "$TMP_DIR/container.headers" \
        -o "$TMP_DIR/container.css" \
        http://127.0.0.1:8000/static/"$STATIC_RELATIVE_PATH" 2>&1 || true

    if [ -f "$TMP_DIR/container.css" ]; then
        printf 'Hash CSS servido pelo container: '
        sha256sum "$TMP_DIR/container.css"
        grep -nE 'position: fixed|bottom: 0|left: 0' "$TMP_DIR/container.css" || \
            warn 'O CSS servido diretamente pelo container não contém as regras esperadas.'
        sed -n '/^HTTP\|^cache-control\|^etag\|^last-modified\|^content-encoding/Ip' \
            "$TMP_DIR/container.headers" || true
    else
        warn 'Não foi possível baixar o CSS diretamente do container.'
    fi
fi

section '8. Cópias locais e artefatos gerados'

find . -type f \( -name 'layout.css' -o -name 'layout*.css' \) \
    -not -path './.git/*' \
    -not -path './node_modules/*' \
    -not -path './.venv/*' \
    -print 2>/dev/null || true

if [ -f "estoque/static/$STATIC_RELATIVE_PATH" ]; then
    printf 'Hash fonte local: '
    sha256sum "estoque/static/$STATIC_RELATIVE_PATH"
fi
if [ -f "staticfiles/$STATIC_RELATIVE_PATH" ]; then
    printf 'Hash STATIC_ROOT local: '
    sha256sum "staticfiles/$STATIC_RELATIVE_PATH"
    if cmp -s "estoque/static/$STATIC_RELATIVE_PATH" "staticfiles/$STATIC_RELATIVE_PATH"; then
        ok 'A cópia local coletada coincide com a fonte local.'
    else
        warn 'A cópia local em staticfiles está desatualizada em relação à fonte.'
    fi
fi

section '9. Service worker, manifest e cache frontend'

PWA_FILES="$(find . \
    -path './.git' -prune -o \
    -path './node_modules' -prune -o \
    -path './.venv' -prune -o \
    -type f \( -iname '*service*worker*' -o -iname 'sw.js' -o -iname 'manifest.json' -o -iname '*.webmanifest' -o -iname '*workbox*' \) \
    -print 2>/dev/null || true)"
if [ -n "$PWA_FILES" ]; then
    printf '%s\n' "$PWA_FILES"
    warn 'Foram encontrados possíveis mecanismos de cache/PWA.'
else
    ok 'Nenhum service worker, manifest PWA ou Workbox encontrado no projeto.'
fi

section '10. CSS público'

PUBLIC_CSS_URL="$PUBLIC_URL/static/$STATIC_RELATIVE_PATH?diagnostico=$(date +%s)"
if curl -fsS -H 'Accept-Encoding: identity' -H 'Cache-Control: no-cache' \
    --max-time 15 \
    -D "$TMP_DIR/public.headers" \
    -o "$TMP_DIR/public.css" \
    "$PUBLIC_CSS_URL" 2>&1; then
    printf 'URL consultada: %s\n' "$PUBLIC_CSS_URL"
    printf 'Hash CSS público: '
    sha256sum "$TMP_DIR/public.css"
    grep -nE 'position: fixed|bottom: 0|left: 0' "$TMP_DIR/public.css" || \
        warn 'O CSS público não contém as regras esperadas da correção.'
    sed -n '/^HTTP\|^cache-control\|^etag\|^last-modified\|^age\|^via\|^x-cache/Ip' \
        "$TMP_DIR/public.headers" || true

    if [ -f "$TMP_DIR/container.css" ] && cmp -s "$TMP_DIR/container.css" "$TMP_DIR/public.css"; then
        ok 'O CSS público coincide byte a byte com o CSS servido pelo container.'
    elif [ -f "$TMP_DIR/container.css" ]; then
        warn 'O CSS público difere do CSS servido diretamente pelo container.'
    fi
else
    warn 'Não foi possível baixar o CSS pela URL pública.'
fi

section 'Resultado'
if [ "$ISSUES" -eq 0 ]; then
    ok 'Nenhuma divergência foi detectada pelos testes executados.'
    exit 0
else
    warn 'Foram encontradas divergências ou verificações indisponíveis. Veja os itens [ATENÇÃO].'
    exit 1
fi
