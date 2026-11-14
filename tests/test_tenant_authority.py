"""Il tenant delle API arriva dal JWT, mai dal body."""

import unittest
from contextlib import contextmanager
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError

from saas import schemas
from saas.main import agent_job_done, crea_soggetto
from saas.repositories import print_repo
from saas.schemas import SoggettoCreate


class FakeCursor:
    def __init__(self, row=None, rowcount=1):
        self.row = row
        self.rowcount = rowcount
        self.statements = []

    def execute(self, query, params=None):
        self.statements.append((query, params))

    def fetchone(self):
        row = self.row
        self.row = None
        return row

    def fetchall(self):
        return []


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.commits = 0

    def cursor(self):
        return self._cursor

    def commit(self):
        self.commits += 1


class TenantAuthorityTests(unittest.TestCase):
    def test_request_models_reject_a_client_supplied_tenant(self):
        controllati = 0
        for name, model in vars(schemas).items():
            if not isinstance(model, type) or not issubclass(model, schemas.ModelloAPI):
                continue
            if model is schemas.ModelloAPI or "tenant_id" in model.model_fields:
                continue
            controllati += 1
            with self.subTest(model=name):
                with self.assertRaises(ValidationError) as error:
                    model.model_validate({"tenant_id": 99})
                self.assertIn("token di accesso", str(error.exception))

        self.assertGreater(controllati, 20)
        self.assertIn("tenant_id", schemas.SoggettoOut.model_fields)
        self.assertIn("tenant_id", schemas.TokenResponse.model_fields)

    def test_create_subject_keeps_the_token_tenant(self):
        with self.assertRaises(ValidationError):
            SoggettoCreate.model_validate({
                "denominazione": "AIA",
                "tenant_id": 99,
            })

        payload = SoggettoCreate.model_validate({"denominazione": "AIA"})
        with patch(
            "saas.main.soggetti_service.crea_soggetto", return_value={"id": 1}
        ) as create:
            crea_soggetto(payload, {"tenant_id": 4, "ruolo": "operatore"})

        create.assert_called_once()
        self.assertEqual(create.call_args.args[0], 4)
        self.assertNotIn("tenant_id", create.call_args.args[1])

    def test_agent_reads_and_updates_only_its_device_tenant(self):
        cursor = FakeCursor(row=(8, 4, None, "etichetta", "{}"))
        conn = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(print_repo, "connection", fake_connection):
            job = print_repo.prendi_prossimo_job(5, 4)

        self.assertEqual(job["id"], 8)
        select_query, select_params = cursor.statements[0]
        update_query, update_params = cursor.statements[1]
        self.assertIn("tenant_id = %s", select_query)
        self.assertNotIn("WHERE stato = 'pending' ORDER BY", select_query)
        self.assertEqual(select_params, (4, 5))
        self.assertIn("WHERE id = %s AND tenant_id = %s", update_query)
        self.assertEqual(update_params, (8, 4))
        self.assertEqual(conn.commits, 1)

        cursor = FakeCursor(rowcount=0)
        conn = FakeConnection(cursor)
        with patch.object(print_repo, "connection", fake_connection):
            aggiornato = print_repo.aggiorna_stato_job(8, "done", 4)
        self.assertFalse(aggiornato)
        self.assertIn("tenant_id = %s", cursor.statements[0][0])
        self.assertEqual(cursor.statements[0][1], ("done", 8, 4))

    def test_agent_completion_of_another_tenant_job_is_not_found(self):
        with (
            unittest.mock.patch(
                "saas.main.print_repo.trova_dispositivo_by_token",
                return_value={"id": 5, "tenant_id": 4},
            ),
            unittest.mock.patch(
                "saas.main.print_repo.aggiorna_stato_job", return_value=False
            ) as update,
        ):
            with self.assertRaises(HTTPException) as error:
                agent_job_done(8, "device-token")

        self.assertEqual(error.exception.status_code, 404)
        update.assert_called_once_with(8, "done", 4)


if __name__ == "__main__":
    unittest.main()
