"""
Scheduler leve em Python puro para execução periódica do backup_sqlite dentro do container.
Roda em segundo plano sem exigir cron de sistema operacional.
"""

import logging
import os
import subprocess
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [Backup Scheduler] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)


def executar_backup():
    logger.info('Disparando backup do banco SQLite...')
    try:
        cmd = [sys.executable, 'manage.py', 'backup_sqlite']
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if res.stdout:
            for line in res.stdout.strip().splitlines():
                logger.info(line)
    except subprocess.CalledProcessError as exc:
        logger.error('Falha ao executar backup: %s', exc.stderr or exc)
    except Exception as exc:
        logger.exception('Erro inesperado no backup: %s', exc)


def main():
    # Intervalo em segundos (padrão: 86400s = 24 horas, configurável via BACKUP_INTERVAL_SECONDS)
    intervalo = int(os.getenv('BACKUP_INTERVAL_SECONDS', '86400'))
    logger.info('Agendador de backup iniciado. Intervalo configurado: %d segundos (%0.1f horas)', intervalo, intervalo / 3600)

    # Executa um backup logo após iniciar se configurado
    if os.getenv('BACKUP_RUN_ON_STARTUP', 'false').lower() in ('true', '1', 'yes'):
        executar_backup()

    while True:
        try:
            time.sleep(intervalo)
            executar_backup()
        except KeyboardInterrupt:
            logger.info('Agendador de backup interrompido.')
            break
        except Exception as exc:
            logger.exception('Erro no loop do agendador: %s', exc)
            time.sleep(60)


if __name__ == '__main__':
    main()

