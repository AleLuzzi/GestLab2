import datetime
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from fastapi import HTTPException

from core.repositories import lotti as lotti_repo
from saas.bootstrap import SCHEMA_FILE, _archivia_ingresso_merce_legacy
from saas.main import conferma_ingresso_merce
from saas.schemas import IngressoMerceCreate


class TableCursor:
    def __init__(self, tables=()):
        self.tables = set(tables)
        self.result = None
        self.statements = []

    def execute(self, query, params=None):
        self.statements.append((query, params))
        if "information_schema.tables" in query:
            self.result = (int(params[0] in self.tables),)
        elif query.startswith("RENAME TABLE"):
            self.tables.remove("ingresso_merce")
            self.tables.add("ingresso_merce_legacy_archive")

    def fetchone(self):
        return self.result


class LegacyIngressoMigrationTests(unittest.TestCase):
    def test_new_schema_does_not_create_legacy_table(self):
        with open(SCHEMA_FILE, encoding="utf-8") as schema_file:
            schema = schema_file.read()

        self.assertNotIn("CREATE TABLE IF NOT EXISTS `ingresso_merce`", schema)

    def test_archives_legacy_table_atomically_and_is_idempotent(self):
        cursor = TableCursor({"ingresso_merce"})

        self.assertTrue(_archivia_ingresso_merce_legacy(cursor))
        self.assertEqual(cursor.tables, {"ingresso_merce_legacy_archive"})
        self.assertFalse(_archivia_ingresso_merce_legacy(cursor))
        self.assertEqual(
            sum(query.startswith("RENAME TABLE") for query, _ in cursor.statements),
            1,
        )

    def test_does_nothing_for_new_database(self):
        cursor = TableCursor()

        self.assertFalse(_archivia_ingresso_merce_legacy(cursor))
        self.assertEqual(cursor.tables, set())

    def test_fails_if_legacy_table_and_archive_both_exist(self):
        cursor = TableCursor(
            {"ingresso_merce", "ingresso_merce_legacy_archive"}
        )

        with self.assertRaisesRegex(RuntimeError, "riconciliare manualmente"):
            _archivia_ingresso_merce_legacy(cursor)

        self.assertEqual(
            cursor.tables,
            {"ingresso_merce", "ingresso_merce_legacy_archive"},
        )


class LegacyIngressoEndpointTests(unittest.TestCase):
    def test_old_endpoint_remains_gone(self):
        payload = IngressoMerceCreate(
            prog_acq="12A",
            data=datetime.date(2026, 10, 3),
            num_ddt="DDT123",
            fornitore_id=1,
            righe=[{"taglio": "Costata", "peso": "12.5", "id_merc": 10}],
        )

        with self.assertRaises(HTTPException) as error:
            conferma_ingresso_merce(payload, {"tenant_id": 42})

        self.assertEqual(error.exception.status_code, 410)


class TrackedOpenLotsTests(unittest.TestCase):
    def test_open_lots_read_tracked_tables(self):
        class FakeCursor:
            def __init__(self):
                self.query = None
                self.params = None

            def execute(self, query, params=None):
                self.query = query
                self.params = params

            def __iter__(self):
                return iter([("A-1", "Fornitore", "Costata", 12.5)])

        class FakeConnection:
            def __init__(self):
                self._cursor = FakeCursor()

            def cursor(self):
                return self._cursor

        connection = FakeConnection()

        @contextmanager
        def fake_connection():
            yield connection

        with patch.object(lotti_repo, "connection", fake_connection):
            lotti = lotti_repo.lotti_aperti(tenant_id=42)

        self.assertIn("FROM lotti l", connection._cursor.query)
        self.assertIn("documenti_ingresso", connection._cursor.query)
        self.assertNotIn("ingresso_merce", connection._cursor.query)
        self.assertEqual(connection._cursor.params, (42,))
        self.assertEqual(
            lotti,
            [{"number": "A-1", "fornit": "Fornitore", "name": "Costata", "peso": "12.5"}],
        )


if __name__ == "__main__":
    unittest.main()
