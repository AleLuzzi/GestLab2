"""Test per la chiusura operativa dei lotti."""

import unittest
from contextlib import contextmanager
from decimal import Decimal
from unittest.mock import patch

from core.services import vendite


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


if __name__ == "__main__":
    unittest.main()
