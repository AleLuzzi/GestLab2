"""Test per il salvataggio multi-tenant dell'ingresso merce."""

import datetime
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from core import MovIngressoMerce
from core.repositories import ingresso_merce_repo
from core.services import ingresso_merce
from saas.schemas import IngressoMerceCreate
from saas.main import conferma_ingresso_merce


class FakeCursor:
    def __init__(self, error=None):
        self.error = error
        self.query = None
        self.rows = None
        self.statements = []
        self.rowcount = 1

    def executemany(self, query, rows):
        self.query = query
        self.rows = rows
        self.statements.append((query, rows))
        if self.error:
            raise self.error

    def execute(self, query, params):
        self.statements.append((query, params))


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


class IngressoMerceTests(unittest.TestCase):
    def test_schema_accepts_valid_payload_and_rejects_invalid_peso(self):
        payload = IngressoMerceCreate(
            prog_acq="12A",
            data="2026-10-03",
            num_ddt="DDT123",
            fornitore="Fornitore",
            righe=[{"taglio": "Costata", "peso": "12.5", "id_merc": 10}],
        )
        self.assertEqual(payload.data, datetime.date(2026, 10, 3))

        with self.assertRaises(ValueError):
            IngressoMerceCreate(
                prog_acq="12A",
                data="2026-10-03",
                fornitore="Fornitore",
                righe=[{"taglio": "Costata", "peso": "0", "id_merc": 10}],
            )

    def test_service_maps_each_line_to_the_model(self):
        row = type(
            "Riga",
            (),
            {"taglio": "Costata", "peso": "12.5", "id_merc": 10},
        )()
        with patch.object(ingresso_merce_repo, "insert_many", return_value=[]) as insert:
            ingresso_merce.salva_movimenti(
                "12A", datetime.date(2026, 10, 3), "DDT123", "Fornitore", [row], 42
            )

        movimenti, tenant_id = insert.call_args.args
        self.assertEqual(tenant_id, 42)
        self.assertEqual(len(movimenti), 1)
        self.assertIsInstance(movimenti[0], MovIngressoMerce)
        self.assertEqual(
            movimenti[0].params_insert(),
            ("12A", datetime.date(2026, 10, 3), "DDT123", "Fornitore",
             "Costata", "12.5", "12.5", "no", 10),
        )

    def test_api_passes_authenticated_tenant_to_service(self):
        payload = IngressoMerceCreate(
            prog_acq="12A",
            data="2026-10-03",
            fornitore="Fornitore",
            righe=[{"taglio": "Costata", "peso": "12.5", "id_merc": 10}],
        )
        with patch(
            "saas.main.ingresso_merce_service.salva_movimenti",
            return_value=[MovIngressoMerce()],
        ) as save:
            result = conferma_ingresso_merce(payload, {"tenant_id": 42})

        self.assertEqual(result, {"inseriti": 1})
        self.assertEqual(save.call_args.kwargs["tenant_id"], 42)

    def test_repository_inserts_rows_in_one_tenant_transaction(self):
        cursor = FakeCursor()
        connection = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield connection

        movement = MovIngressoMerce(
            prog_acq="12A",
            data=datetime.date(2026, 10, 3),
            num_ddt="DDT123",
            fornitore="Fornitore",
            taglio="Costata",
            peso_i="12.5",
            peso_f="12.5",
            lotto_chiuso="no",
            id_merc=10,
        )
        with patch.object(ingresso_merce_repo, "connection", fake_connection):
            saved = ingresso_merce_repo.insert_many([movement, movement], tenant_id=42)

        self.assertEqual(len(saved), 2)
        self.assertIn("tenant_id", cursor.query)
        self.assertEqual(cursor.rows[0][-1], 42)
        self.assertEqual(cursor.rows[1][-1], 42)
        self.assertIn("UPDATE progressivi", cursor.statements[1][0])
        self.assertIn("prog_acq = prog_acq + 1", cursor.statements[1][0])
        self.assertEqual(cursor.statements[1][1], (42,))
        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.rollbacks, 0)

    def test_repository_rolls_back_when_progressivo_is_missing(self):
        cursor = FakeCursor()
        cursor.rowcount = 0
        connection = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield connection

        with patch.object(ingresso_merce_repo, "connection", fake_connection):
            with self.assertRaisesRegex(RuntimeError, "progressivo acquisti"):
                ingresso_merce_repo.insert_many(
                    [MovIngressoMerce(prog_acq="12A", id_merc=10)], tenant_id=42
                )

        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 1)

    def test_repository_rolls_back_when_insert_fails(self):
        cursor = FakeCursor(error=RuntimeError("insert failed"))
        connection = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield connection

        with patch.object(ingresso_merce_repo, "connection", fake_connection):
            with self.assertRaisesRegex(RuntimeError, "insert failed"):
                ingresso_merce_repo.insert_many(
                    [MovIngressoMerce(prog_acq="12A", id_merc=10)], tenant_id=42
                )

        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 1)


if __name__ == "__main__":
    unittest.main()
