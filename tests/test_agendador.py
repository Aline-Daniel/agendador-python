import sqlite3
import subprocess
from tempfile import TemporaryDirectory
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agendador import fazer_backup, executar_tarefa, log


class TestAgendador(unittest.TestCase):
    def test_backup_consistente(self):
        with TemporaryDirectory() as root:
            db = Path(root)/'origem.db'
            with sqlite3.connect(db) as con:
                con.execute('CREATE TABLE teste (id INTEGER PRIMARY KEY, texto TEXT)')
                con.execute('INSERT INTO teste VALUES (1,?)', ('Olá',))
            output = fazer_backup(db,Path(root)/'backup')
            self.assertTrue(output.is_file())
            with sqlite3.connect(output) as con:
                self.assertEqual(con.execute('SELECT texto FROM teste').fetchone()[0], 'Olá')

    def test_backups_sao_independentes_e_integros(self):
        with TemporaryDirectory() as root:
            db = Path(root) / 'origem.db'
            pasta = Path(root) / 'backups'
            with sqlite3.connect(db) as con:
                con.execute('CREATE TABLE exemplo (nome TEXT NOT NULL)')
                con.execute('INSERT INTO exemplo VALUES (?)', ('Dados de teste',))
            primeiro = fazer_backup(db, pasta)
            segundo = fazer_backup(db, pasta)
            self.assertNotEqual(primeiro, segundo)
            self.assertEqual(len(list(pasta.glob('backup_*.db'))), 2)
            self.assertEqual(len(list(pasta.glob('.backup_*.tmp'))), 0)
            for caminho in (primeiro, segundo):
                with sqlite3.connect(caminho) as con:
                    self.assertEqual(con.execute('PRAGMA quick_check').fetchone()[0], 'ok')
                    self.assertEqual(con.execute('SELECT nome FROM exemplo').fetchone()[0], 'Dados de teste')

    def test_backup_corrompido_nao_deixa_arquivo_parcial(self):
        with TemporaryDirectory() as root:
            db = Path(root) / 'corrompido.db'
            pasta = Path(root) / 'backups'
            db.write_bytes(b'isto nao e um banco sqlite valido')
            with self.assertRaises(sqlite3.DatabaseError):
                fazer_backup(db, pasta)
            self.assertEqual(list(pasta.iterdir()), [])

    def test_timeout_etl_exibe_erro_claro(self):
        with TemporaryDirectory() as root:
            fake_etl = Path(root) / 'etl.py'
            fake_etl.write_text('print("exemplo")', encoding='utf-8')
            with patch('agendador.ETL', fake_etl):
                with patch('agendador.subprocess.run',
                           side_effect=subprocess.TimeoutExpired(['python', 'etl.py'], 300)):
                    with self.assertRaisesRegex(RuntimeError, 'excedeu o limite de 300 segundos'):
                        executar_tarefa('etl', Path(root) / 'dados.db',
                                        Path(root) / 'dados.json', Path(root) / 'backups')

    def test_erro_backup_sem_banco(self):
        with TemporaryDirectory() as root:
            with self.assertRaises(FileNotFoundError):
                fazer_backup(Path(root)/'inexistente.db',Path(root)/'out')

    def test_rejeitar_tarefa_desconhecida(self):
        with self.assertRaises(ValueError):
            executar_tarefa('comando_livre', Path('x'),Path('y'),Path('z'))

    def test_registrar_log(self):
        with TemporaryDirectory() as root:
            path = Path(root)/'logs'/'run.log'
            log('OK teste',path)
            self.assertIn('OK teste',path.read_text(encoding='utf-8'))


if __name__ == '__main__': unittest.main()
