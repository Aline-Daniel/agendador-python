import sqlite3
from tempfile import TemporaryDirectory
from pathlib import Path
import sys
import unittest
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
