"""
Teste rápido do webhook n8n — sem precisar subir o Django.

Preencha as variáveis abaixo e rode:
    uv run python scripts/testar_webhook.py
ou
    python scripts/testar_webhook.py
"""

import json
import socket
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone

# ─── CONFIG — preencha aqui ──────────────────────────────────────────────────
WEBHOOK_URL = "https://n8n.corrigeja.com.br/webhook/notifications/v3"
TOKEN       = "mateus3010"   # cole o token que o n8n espera
# ─────────────────────────────────────────────────────────────────────────────

TIMEOUT = 10  # segundos


def enviar(event: str, audience: str, data: dict, severity: str = "info") -> bool:
    payload = {
        "event_id":    str(uuid.uuid4()),
        "event":       event,
        "source":      "sge",
        "audience":    audience,
        "severity":    severity,
        "occurred_at": datetime.now(tz=timezone.utc).isoformat(),
        "data":        data,
    }

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req  = urllib.request.Request(
        WEBHOOK_URL,
        data=body,
        method="POST",
        headers={
            "Content-Type":  "application/json",
            "X-Notify-Token": TOKEN,
        },
    )

    print(f"\n  evento: {event}")
    print(f"  payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            resposta = resp.read().decode("utf-8", errors="replace")
            print(f"\n  OK HTTP {resp.status}")
            print(f"  resposta n8n: {resposta}")
            return True

    except urllib.error.HTTPError as exc:
        corpo = ""
        try:
            corpo = exc.read(500).decode("utf-8", errors="replace")
        except Exception:
            pass
        print(f"\n  ERRO HTTP {exc.code} {exc.reason}")
        print(f"  corpo: {corpo}")

    except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as exc:
        print(f"\n  FALHA de conexao: {exc}")

    return False


def main():
    if TOKEN == "SEU_TOKEN_AQUI":
        print("⚠️  Preencha TOKEN no início do script antes de rodar!")
        return

    print("=" * 60)
    print("SGE — Teste de Webhook n8n")
    print(f"URL: {WEBHOOK_URL}")
    print("=" * 60)

    # ── Evento 1: teste genérico ──────────────────────────────────
    print("\n[1/3] Enviando evento: teste_sistema")
    enviar(
        event="teste_sistema",
        audience="admin",
        severity="info",
        data={
            "mensagem": "Ola do SGE! Webhook funcionando!",
            "usuario":  "script_teste",
        },
    )

    # ── Evento 2: estoque baixo ───────────────────────────────────
    print("\n[2/3] Enviando evento: stock.low")
    enviar(
        event="stock.low",
        audience="purchasing",
        severity="warning",
        data={
            "product_id":    99,
            "product":       "Tinta Azul Royal (teste)",
            "current_stock": 8.5,
            "minimum_stock": 20.0,
            "unit":          "L",
        },
    )

    # ── Evento 3: estoque zerado ──────────────────────────────────
    print("\n[3/3] Enviando evento: stock.zero")
    enviar(
        event="stock.zero",
        audience="purchasing",
        severity="critical",
        data={
            "product_id":    100,
            "product":       "Papel A4 (teste)",
            "current_stock": 0.0,
            "unit":          "m",
        },
    )

    print("\n" + "=" * 60)
    print("Pronto. Confira os logs do n8n para ver os eventos recebidos.")
    print("=" * 60)


if __name__ == "__main__":
    main()
