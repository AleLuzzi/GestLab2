import unittest
from contextlib import nullcontext
from unittest.mock import patch

from core.core_models import Dipendente
from core.repositories import dipendenti as dipendenti_repo
from core.services import dipendenti as dipendenti_service
from saas.schemas import DipendenteCreate, DipendenteUpdate


class FakeCursor:
    lastrowid = 17

    def __init__(self, rows=()):
        self.rows = list(rows)
        self.statement = None

    def execute(self, query, params=None):
        self.statement = (query, params)

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.commits = 0

    def cursor(self):
        return self._cursor

    def commit(self):
        self.commits += 1


class DipendentiTests(unittest.TestCase):
    def test_api_schemas_keep_cognome_optional_for_existing_clients(self):
        create_payload = DipendenteCreate(nome="Ada")
        update_payload = DipendenteUpdate()

        self.assertEqual(create_payload.cognome, "")
        self.assertIsNone(update_payload.cognome)

    def test_from_row_reads_cognome_and_keeps_legacy_rows_compatible(self):
        dipendente = Dipendente.from_row((1, "Ada", "ada@example.test", 3, "Macelleria", "Lovelace"))
        legacy = Dipendente.from_row((2, "Alan", "alan@example.test", 4))

        self.assertEqual(dipendente.cognome, "Lovelace")
        self.assertEqual(dipendente.reparto_nome, "Macelleria")
        self.assertEqual(legacy.cognome, "")

    def test_non_tenant_crud_queries_persist_cognome(self):
        cursor = FakeCursor()
        connection = FakeConnection(cursor)
        dipendente = Dipendente(nome="Grace", email="grace@example.test", cognome="Hopper")

        dipendente.insert(cursor, connection)
        self.assertIn("cognome", cursor.statement[0])
        self.assertEqual(cursor.statement[1], ("Grace", "grace@example.test", None, "Hopper"))
        self.assertEqual(dipendente.id, cursor.lastrowid)

        dipendente.save(cursor, connection)
        self.assertIn("cognome = %s", cursor.statement[0])
        self.assertEqual(cursor.statement[1], ("Grace", "grace@example.test", None, "Hopper", 17))

    def test_tenant_crud_queries_persist_cognome(self):
        cursor = FakeCursor([(1, "Ada", "ada@example.test", 3, "Macelleria", "Lovelace")])
        connection = FakeConnection(cursor)

        with patch.object(dipendenti_repo, "connection", return_value=nullcontext(connection)):
            loaded = dipendenti_repo.find_by_id(1, tenant_id=9)
            self.assertEqual(loaded.cognome, "Lovelace")
            self.assertIn("d.cognome", cursor.statement[0])

            new = Dipendente(nome="Grace", email="grace@example.test", cognome="Hopper")
            dipendenti_repo.insert(new, tenant_id=9)
            self.assertIn("cognome", cursor.statement[0])
            self.assertEqual(cursor.statement[1], ("Grace", "grace@example.test", None, "Hopper", 9))

            new.id = 17
            dipendenti_repo.save(new, tenant_id=9)
            self.assertIn("cognome = %s", cursor.statement[0])
            self.assertEqual(cursor.statement[1], ("Grace", "grace@example.test", None, "Hopper", 17, 9))

        self.assertEqual(new.id, 17)

    def test_service_keeps_existing_positional_arguments_compatible(self):
        with patch.object(dipendenti_service.repo, "insert", side_effect=lambda value, tenant_id: value) as insert:
            dipendente = dipendenti_service.crea_dipendente("Ada", "ada@example.test", 3, 9)

        self.assertEqual(dipendente.reparto, 3)
        self.assertEqual(dipendente.cognome, "")
        insert.assert_called_once_with(dipendente, 9)

        dipendente.cognome = "Lovelace"
        with patch.object(dipendenti_service.repo, "save", side_effect=lambda value, tenant_id: value):
            dipendenti_service.aggiorna_dipendente(dipendente, "Augusta", "ada@example.test", 3, 9)
        self.assertEqual(dipendente.cognome, "Lovelace")


if __name__ == "__main__":
    unittest.main()
