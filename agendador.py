"""Executa ETL ou backup do SQLite uma vez ou por agendamento local.

Sem bibliotecas externas, e sem executar comandos enviados por usuários.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import sys
import time

ROOT = Path(__file__).resolve().parent
ETL_REPO = ROOT.parent / 'etl-python-bancos'
DATA_BASE = ETL_REPO / 'dados' / 'ocorrencias.db'
ETL = ETL_REPO / 'etl.py'
ORIGEM = ETL_REPO / 'dados' / 'ocorrencias_exemplo.json'


def fazer_backup(database: Path, pasta: Path) -> Path:
    """Cria backup consistente, verifica integridade e publica o arquivo só após sucesso."""
    database = Path(database)
    if not database.is_file():
        raise FileNotFoundError(f'Banco SQLite não existe: {database}. Rode o ETL primeiro.')
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / ('backup_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.db')
    # Arquivo temporário na mesma pasta garante substituição atômica ao concluir.
    with tempfile.NamedTemporaryFile(dir=pasta, prefix='.backup_', suffix='.tmp', delete=False) as tmp:
        temporario = Path(tmp.name)
    try:
        with sqlite3.connect(f'file:{database.resolve()}?mode=ro', uri=True) as origem:
            with sqlite3.connect(temporario) as destino:
                origem.backup(destino)
                verificacao = destino.execute('PRAGMA quick_check').fetchone()
                if not verificacao or verificacao[0] != 'ok':
                    raise sqlite3.DatabaseError('Falha na verificação de integridade do backup.')
        temporario.replace(caminho)
        return caminho
    finally:
        # Nunca deixar um arquivo parcial como se fosse um backup concluído.
        temporario.unlink(missing_ok=True)

def executar_tarefa(tarefa: str, database: Path, origem: Path, backups: Path) -> str:
    if tarefa == 'backup':
        return 'Backup criado: ' + str(fazer_backup(database, backups))
    if tarefa == 'etl':
        if not ETL.is_file():
            raise FileNotFoundError(
                f'Não encontrei o ETL em {ETL}. '
                "Coloque as pastas agendador-python e etl-python-bancos lado a lado."
            )
        try:
            processo = subprocess.run(
                [sys.executable, str(ETL), '--origem', str(origem), '--db', str(database), '--modo', 'incremental'],
                capture_output=True, text=True, encoding='utf-8', timeout=300, check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError('ETL excedeu o limite de 300 segundos e foi interrompido.') from exc
        if processo.returncode:
            raise RuntimeError(f'ETL falhou (código {processo.returncode}): {processo.stderr[-400:]}')
        return 'ETL executado: ' + processo.stdout.strip().replace('\n',' ')
    raise ValueError('Tarefa não reconhecida.')


def log(texto: str, arquivo: Path) -> None:
    agora = datetime.now().isoformat(timespec='seconds')
    msg = f'[{agora}] {texto}'
    print(msg, flush=True)
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    with arquivo.open('a', encoding='utf-8') as f:
        f.write(msg + '\n')


def agendar(tarefa: str, database: Path, origem: Path, backups: Path,
            log_path: Path, intervalo: int | None = None, hora: str | None = None) -> None:
    """Executa a tarefa enquanto o programa estiver aberto; horário do computador."""
    if (intervalo is None) == (hora is None):
        raise ValueError('Escolha --intervalo ou --hora.')
    if intervalo is not None and intervalo < 1:
        raise ValueError('Intervalo deve ser de pelo menos 1 minuto.')
    if hora is not None:
        try:
            parsed = datetime.strptime(hora, '%H:%M')
            if parsed.strftime('%H:%M') != hora:
                raise ValueError()
        except ValueError as exc:
            raise ValueError('Use HH:MM de 00:00 a 23:59.') from exc
    ultimo_dia = None
    proxima = time.monotonic() + intervalo * 60 if intervalo else None
    log('Agendador iniciado. Pressione Ctrl+C para parar.', log_path)
    try:
        while True:
            agora = datetime.now()
            disparar = False
            if intervalo is not None and time.monotonic() >= proxima:
                disparar = True
                proxima = time.monotonic() + intervalo * 60
            elif hora and agora.strftime('%H:%M') == hora and ultimo_dia != agora.date():
                disparar = True
                ultimo_dia = agora.date()
            if disparar:
                try:
                    log(executar_tarefa(tarefa, database, origem, backups), log_path)
                except (RuntimeError, OSError, sqlite3.Error) as exc:
                    log(f'FALHA: {exc}', log_path)
            time.sleep(1)
    except KeyboardInterrupt:
        log('Agendador encerrado.', log_path)


def main():
    parser = argparse.ArgumentParser(description='Agendador de ETL e backup seguro')
    parser.add_argument('--tarefa', choices=['etl', 'backup'], required=True)
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument('--uma-vez', action='store_true')
    grupo.add_argument('--intervalo', type=int, help='Executar a cada X minutos')
    grupo.add_argument('--hora', help='Executar todo dia em HH:MM')
    parser.add_argument('--db', type=Path, default=DATA_BASE)
    parser.add_argument('--origem', type=Path, default=ORIGEM)
    parser.add_argument('--backups', type=Path, default=ROOT / 'backups')
    parser.add_argument('--log', type=Path, default=ROOT / 'logs' / 'agendador.log')
    args = parser.parse_args()
    try:
        if args.uma_vez:
            log(executar_tarefa(args.tarefa, args.db, args.origem, args.backups), args.log)
        else:
            agendar(args.tarefa, args.db, args.origem, args.backups,
                    args.log, intervalo=args.intervalo, hora=args.hora)
    except (ValueError, RuntimeError, OSError, sqlite3.Error) as exc:
        parser.exit(1, f'Erro: {exc}\n')


if __name__ == '__main__': main()
