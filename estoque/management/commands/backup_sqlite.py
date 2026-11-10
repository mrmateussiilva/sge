import os
import shutil
import sqlite3
import tarfile
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        'Gera um backup consistente e comprimido do banco SQLite do SGE usando a SQLite Online Backup API. '
        'Suporta rotação automática dos backups mais antigos.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            default=os.getenv('BACKUP_DIR', str(settings.BASE_DIR / 'data' / 'backups')),
            help='Diretório onde os arquivos de backup (.tar.gz) serão salvos.',
        )
        parser.add_argument(
            '--keep',
            type=int,
            default=int(os.getenv('BACKUP_KEEP_COPIES', '14')),
            help='Quantidade de backups recentes a manter (os mais antigos serão excluídos). Default: 14.',
        )

    def handle(self, *args, **options):
        db_path = Path(settings.DATABASES['default']['NAME']).resolve()
        if not db_path.exists():
            raise CommandError(f'Arquivo de banco de dados não encontrado: {db_path}')

        out_dir = Path(options['output_dir']).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        now_utc = datetime.now(timezone.utc)
        timestamp = now_utc.strftime('%Y%m%d_%H%M%S')
        temp_sqlite = out_dir / f'db_temp_{timestamp}.sqlite3'
        final_tar_gz = out_dir / f'sge_backup_{timestamp}.tar.gz'

        self.stdout.write(f'Iniciando backup a quente de: {db_path}')

        try:
            # 1. Utiliza a Online Backup API do SQLite para garantir cópia consistente mesmo durante escritas (WAL)
            orig_conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
            dest_conn = sqlite3.connect(temp_sqlite)
            try:
                orig_conn.backup(dest_conn)
            finally:
                dest_conn.close()
                orig_conn.close()

            # 2. Compacta a cópia em tar.gz
            with tarfile.open(final_tar_gz, 'w:gz') as tar:
                tar.add(temp_sqlite, arcname='db.sqlite3')

            size_mb = final_tar_gz.stat().st_size / (1024 * 1024)
            self.stdout.write(
                self.style.SUCCESS(f'Backup concluído com sucesso: {final_tar_gz.name} ({size_mb:.2f} MB)')
            )
        finally:
            if temp_sqlite.exists():
                temp_sqlite.unlink()

        # 3. Rotação de backups antigos
        keep = options['keep']
        if keep > 0:
            existing_backups = sorted(
                out_dir.glob('sge_backup_*.tar.gz'),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            for old_backup in existing_backups[keep:]:
                try:
                    old_backup.unlink()
                    self.stdout.write(f'Removido backup antigo: {old_backup.name}')
                except OSError as exc:
                    self.stderr.write(f'Erro ao remover backup {old_backup.name}: {exc}')

