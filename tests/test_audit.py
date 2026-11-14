"""Audit log di cancellazioni e rettifiche."""

import unittest
from contextlib import contextmanager
from decimal import Decimal
from unittest.mock import patch

from fastapi import HTTPException

from core.repositories import dipendenti as dipendenti_repo
from saas.main import elimina_dipendente, lista_audit, rettifica_lotto_tracciato
from saas.repositories import audit_repo, tracciabilita_repo
from saas.schemas import RettificaLottoCreate


class Record:
    def __init__(self, record_id):
        self.id = record_id


class FakeCursor:
    def __init__(self, handler=None, rowcount=1):
        self.handler = handler or (lambda query, params: [])
        self.rowcount = rowcount
        self.result = []
        self.statements = []

    def execute(self, query, params=None):
        self.statements.append((query, params))
        outcome = self.handler(query, params)
        if isinstance(outcome, int):
            self.rowcount = outcome
            self.result = []
            return
        self.result = outcome or []

    def fetchone(self):
        return self.result[0] if self.result else None

    def fetchall(self):
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


class AuditLogTests(unittest.TestCase):
    def test_employee_delete_writes_audit_in_the_same_transaction(self):
        cursor = FakeCursor()
        conn = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(dipendenti_repo, "connection", fake_connection):
            dipendenti_repo.delete(Record(9), tenant_id=4, utente_email="admin@example.com")

        delete_query, delete_params = cursor.statements[0]
        audit_query, audit_params = cursor.statements[1]
        self.assertIn("DELETE FROM dipendenti WHERE id = %s AND tenant_id = %s", delete_query)
        self.assertEqual(delete_params, (9, 4))
        self.assertIn("INSERT INTO audit_log", audit_query)
        self.assertEqual(audit_params[:4], (4, "admin@example.com", "CANCELLAZIONE", "dipendenti"))
        self.assertEqual(audit_params[4], "9")
        self.assertEqual(conn.commits, 1)
        self.assertEqual(conn.rollbacks, 0)

    def test_employee_delete_rolls_back_when_audit_insert_fails(self):
        def handle(query, params):
            if query.startswith("INSERT INTO audit_log"):
                raise RuntimeError("audit non scritto")
            return 1

        cursor = FakeCursor(handle)
        conn = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(dipendenti_repo, "connection", fake_connection):
            with self.assertRaisesRegex(RuntimeError, "audit non scritto"):
                dipendenti_repo.delete(
                    Record(9), tenant_id=4, utente_email="admin@example.com"
                )

        self.assertEqual(conn.commits, 0)
        self.assertEqual(conn.rollbacks, 1)

    def test_delete_endpoint_requires_the_authenticated_user(self):
        with patch.object(dipendenti_repo, "find_by_id", return_value=Record(9)):
            with self.assertRaises(HTTPException) as error:
                elimina_dipendente(9, {"tenant_id": 4, "ruolo": "admin"})

        self.assertEqual(error.exception.status_code, 401)

    def test_rectification_rolls_back_when_audit_insert_fails(self):
        def handle(query, params):
            if query.startswith("SELECT quantita_disponibile FROM lotti"):
                return [(Decimal("1.250"),)]
            if query.startswith("INSERT INTO audit_log"):
                raise RuntimeError("audit non scritto")
            return []

        cursor = FakeCursor(handle)
        conn = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(tracciabilita_repo, "connection", fake_connection):
            with self.assertRaisesRegex(RuntimeError, "audit non scritto"):
                rettifica_lotto_tracciato(
                    7,
                    RettificaLottoCreate(delta="-0.250", motivo="inventario"),
                    {"tenant_id": 4, "ruolo": "admin", "sub": "admin@example.com"},
                )

        self.assertTrue(any("UPDATE lotti" in query for query, _ in cursor.statements))
        self.assertEqual(conn.commits, 0)
        self.assertEqual(conn.rollbacks, 1)

    def test_audit_list_uses_only_the_token_tenant(self):
        expected = [{"id": 1, "azione": "RETTIFICA", "entita": "lotti"}]
        with patch.object(audit_repo, "lista", return_value=expected) as listed:
            result = lista_audit(50, {"tenant_id": 4, "ruolo": "admin", "sub": "admin@example.com"})

        self.assertEqual(result, expected)
        listed.assert_called_once_with(4, 50)


if __name__ == "__main__":
    unittest.main()
