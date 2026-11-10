"""Test per la chiusura operativa dei lotti."""

import unittest
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from fastapi import HTTPException

from core.services import vendite
from saas.main import crea_vendita, lotti_disponibili_vendita
from saas.repositories import tracciabilita_repo
from saas.schemas import VenditaCreate


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
            (7, 3, "Costata", "A", "A-7", "2026-12-15", Decimal("8.500"), "kg", None),
            (8, 3, "Costata", "V", "V-8", None, Decimal("2.000"), "kg", "2026-12-10"),
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
        self.assertIn("COALESCE(l.data_scadenza, l.data_tmc) ASC", conn._cursor.query)
        self.assertIn("THEN 1 ELSE 0 END", conn._cursor.query)
        self.assertEqual(lotti[0]["id"], 7)
        self.assertEqual(lotti[0]["quantita_disponibile"], "8.500")
        self.assertIsNone(lotti[1]["data_scadenza"])
        self.assertEqual(lotti[1]["data_tmc"], "2026-12-10")

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


class FakeVenditaCursor:
    def __init__(self, cliente_valido=True):
        self.cliente_valido = cliente_valido
        self.lastrowid = 81
        self.statements = []

    def execute(self, query, params=None):
        self.statements.append((query, params))

    def fetchone(self):
        query = self.statements[-1][0]
        if query.startswith("SELECT id FROM tenant"):
            return (42,)
        if query.startswith("SELECT s.id FROM soggetti"):
            return (13,) if self.cliente_valido else None
        if query.startswith("SELECT COALESCE(MAX(numero)"):
            return (4,)
        return None


class CreaVenditaTests(unittest.TestCase):
    def invoke_repository(self, cliente_id=13, cliente_valido=True):
        cursor = FakeVenditaCursor(cliente_valido)
        connection = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield connection

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            result = tracciabilita_repo.crea_vendita(
                42,
                date(2026, 11, 10),
                cliente_id,
                "DDT",
            )
        return result, cursor, connection

    def test_creates_tenant_scoped_header_with_next_number(self):
        vendita, cursor, connection = self.invoke_repository()

        self.assertEqual(
            vendita,
            {
                "id": 81,
                "tenant_id": 42,
                "numero": 5,
                "data_vendita": date(2026, 11, 10),
                "cliente_id": 13,
                "tipo_documento": "DDT",
            },
        )
        self.assertIn("FOR UPDATE", cursor.statements[0][0])
        self.assertEqual(cursor.statements[0][1], (42,))
        self.assertEqual(
            cursor.statements[-1][1],
            (42, 5, date(2026, 11, 10), 13, "DDT"),
        )
        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.rollbacks, 0)

    def test_bank_receipt_does_not_require_a_customer(self):
        cursor = FakeVenditaCursor()
        connection = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield connection

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            vendita = tracciabilita_repo.crea_vendita(
                42, date(2026, 11, 10), None, "RICEVUTA"
            )

        self.assertIsNone(vendita["cliente_id"])
        self.assertFalse(any("FROM soggetti s" in query for query, _ in cursor.statements))
        self.assertEqual(
            cursor.statements[-1][1],
            (42, 5, date(2026, 11, 10), None, "RICEVUTA"),
        )

    def test_invalid_customer_rolls_back(self):
        cursor = FakeVenditaCursor(cliente_valido=False)
        connection = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield connection

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            with self.assertRaises(tracciabilita_repo.ClienteVenditaNonValido):
                tracciabilita_repo.crea_vendita(
                    42, date(2026, 11, 10), 13, "DDT"
                )

        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 1)

    def test_endpoint_uses_tenant_from_authenticated_user(self):
        payload = VenditaCreate(
            data=date(2026, 11, 10),
            cliente_id=13,
            tipo_documento="DDT",
        )
        expected = {"id": 81, "tenant_id": 42, "numero": 5}

        with patch.object(
            tracciabilita_repo, "crea_vendita", return_value=expected
        ) as create:
            result = crea_vendita(payload, {"tenant_id": 42})

        self.assertEqual(result, expected)
        create.assert_called_once_with(
            tenant_id=42,
            data_vendita=payload.data,
            cliente_id=13,
            tipo_documento="DDT",
        )

    def test_endpoint_translates_invalid_customer(self):
        payload = VenditaCreate(
            data=date(2026, 11, 10),
            cliente_id=13,
            tipo_documento="DDT",
        )

        with patch.object(
            tracciabilita_repo,
            "crea_vendita",
            side_effect=tracciabilita_repo.ClienteVenditaNonValido,
        ):
            with self.assertRaises(HTTPException) as error:
                crea_vendita(payload, {"tenant_id": 42})

        self.assertEqual(error.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
