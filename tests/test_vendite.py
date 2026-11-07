"""Test per la chiusura operativa dei lotti."""

import unittest
from contextlib import contextmanager
from decimal import Decimal
from unittest.mock import patch

from core.services import vendite
from saas.main import lotti_disponibili_vendita
from saas.repositories import tracciabilita_repo


class FakeCursor:
    def __init__(self, giacenza):
        self.giacenza = giacenza
        self.rowcount = 1
        self.statements = []

    def execute(self, query, params=None):
        self.statements.append((query, params))
        if query.startswith("SELECT quantita_disponibile"):
            self.result = (self.giacenza,) if self.giacenza is not None else None

    def fetchone(self):
        return self.result


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


class ChiusuraLottoTests(unittest.TestCase):
    def invoke_with_stock(self, giacenza, lotto_id=7, tenant_id=42):
        cursor = FakeCursor(giacenza)
        conn = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(vendite, "connection", fake_connection):
            result = vendite.chiudi_lotto(lotto_id, tenant_id)
        return result, cursor, conn

    def test_closing_nonempty_lot_does_not_change_stock(self):
        cursor = FakeCursor(Decimal("1.250"))
        conn = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(vendite, "connection", fake_connection):
            with self.assertRaises(vendite.LottoNonEsaurito):
                vendite.chiudi_lotto(7, 42)

        self.assertFalse(any(query.startswith("UPDATE lotti") for query, _ in cursor.statements))
        self.assertEqual(conn.commits, 0)
        self.assertEqual(conn.rollbacks, 1)

    def test_closing_depleted_lot_only_marks_it_inactive(self):
        result, cursor, conn = self.invoke_with_stock(Decimal("0.000"))

        self.assertTrue(result)
        update, params = next(
            (query, params)
            for query, params in cursor.statements
            if query.startswith("UPDATE lotti")
        )
        self.assertIn("SET attivo = 0", update)
        self.assertNotIn("SET quantita_disponibile", update)
        self.assertEqual(params, (7, 42))
        self.assertEqual(conn.commits, 1)
        self.assertEqual(conn.rollbacks, 0)

    def test_closing_unknown_lot_returns_false_without_updating(self):
        result, cursor, conn = self.invoke_with_stock(None)

        self.assertFalse(result)
        self.assertFalse(any(query.startswith("UPDATE lotti") for query, _ in cursor.statements))
        self.assertEqual(conn.commits, 1)
        self.assertEqual(conn.rollbacks, 0)


class LottiDisponibiliVenditaTests(unittest.TestCase):
    def test_repository_returns_available_lots_in_fefo_order(self):
        rows = [
            (7, 3, "Costata", "A", "A-7", "2026-12-15", Decimal("8.500"), "kg"),
            (8, 3, "Costata", "V", "V-8", None, Decimal("2.000"), "kg"),
        ]

        class FakeCursor:
            def __init__(self):
                self.query = None
                self.params = None

            def execute(self, query, params=None):
                self.query = query
                self.params = params

            def fetchall(self):
                return rows

        class FakeConnection:
            def __init__(self):
                self._cursor = FakeCursor()

            def cursor(self):
                return self._cursor

        conn = FakeConnection()

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            lotti = tracciabilita_repo.lotti_disponibili_vendita(42)

        self.assertEqual(conn._cursor.params, (42,))
        self.assertIn("a.attivo = 1", conn._cursor.query)
        self.assertIn("l.attivo = 1", conn._cursor.query)
        self.assertIn("l.quantita_disponibile > 0", conn._cursor.query)
        self.assertIn("l.data_scadenza >= CURRENT_DATE", conn._cursor.query)
        self.assertIn("l.data_scadenza ASC", conn._cursor.query)
        self.assertIn("THEN 1 ELSE 0 END", conn._cursor.query)
        self.assertEqual(lotti[0]["id"], 7)
        self.assertEqual(lotti[0]["quantita_disponibile"], "8.500")
        self.assertIsNone(lotti[1]["data_scadenza"])

    def test_endpoint_uses_tenant_from_authenticated_user(self):
        expected = [{"id": 7, "codice_lotto": "A-7"}]

        with patch.object(
            tracciabilita_repo,
            "lotti_disponibili_vendita",
            return_value=expected,
        ) as list_lots:
            result = lotti_disponibili_vendita({"tenant_id": 42})

        self.assertEqual(result, expected)
        list_lots.assert_called_once_with(42)


if __name__ == "__main__":
    unittest.main()
