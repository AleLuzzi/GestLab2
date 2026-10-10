"""Test del salvataggio transazionale dei nuovi lotti di vendita."""

import datetime
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from core.repositories import lotti as lotti_repo
from core.services import vendite as vendite_service


class FakeCursor:
    def __init__(self, current_progressivo=7, update_rowcount=1):
        self.current_progressivo = current_progressivo
        self.update_rowcount = update_rowcount
        self.rowcount = 0
        self.statements = []
        self.inserted_rows = []

    def execute(self, query, params=None):
        self.statements.append((query, params))
        if query.startswith("UPDATE progressivi"):
            self.rowcount = self.update_rowcount

    def fetchone(self):
        if self.current_progressivo is None:
            return None
        return (self.current_progressivo,)

    def executemany(self, query, rows):
        self.statements.append((query, rows))
        self.inserted_rows.extend(rows)


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self._cursor

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class NuovoLottoTests(unittest.TestCase):
    def _use_connection(self, connection):
        @contextmanager
        def fake_connection():
            yield connection

        return patch.object(lotti_repo, "connection", fake_connection)

    def test_save_inserts_rows_and_advances_progressivo_atomically(self):
        cursor = FakeCursor()
        connection = FakeConnection(cursor)
        righe = [{
            "lotto_acq": "12A",
            "prodotto": "Salsiccia",
            "quantita": "2.5",
            "prod_origine": "Spalla",
        }]
        data = datetime.date(2026, 10, 3)

        with self._use_connection(connection):
            progressivo = lotti_repo.salva_lotti_vendita(7, data, righe)

        self.assertEqual(progressivo, "7V")
        self.assertEqual(cursor.inserted_rows, [("7V", data, "12A", "Salsiccia", "2.5", "Spalla")])
        self.assertIn("FOR UPDATE", cursor.statements[0][0])
        self.assertIn("UPDATE progressivi", cursor.statements[2][0])
        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.rollbacks, 0)

    def test_save_rolls_back_if_progressivo_changed(self):
        cursor = FakeCursor(current_progressivo=8)
        connection = FakeConnection(cursor)
        righe = [{
            "lotto_acq": "12A",
            "prodotto": "Salsiccia",
            "quantita": "2",
            "prod_origine": "Spalla",
        }]

        with self._use_connection(connection):
            with self.assertRaisesRegex(RuntimeError, "è cambiato"):
                lotti_repo.salva_lotti_vendita(
                    7, datetime.date(2026, 10, 3), righe
                )

        self.assertEqual(cursor.inserted_rows, [])
        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 1)

    def test_service_rejects_incomplete_rows_before_database_access(self):
        with patch.object(lotti_repo, "salva_lotti_vendita") as save:
            with self.assertRaisesRegex(ValueError, "incompleta"):
                vendite_service.crea_lotto_vendita(
                    7,
                    datetime.date(2026, 10, 3),
                    [{"lotto_acq": "12A"}],
                )
        save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
