"""Test per gli schemi e gli endpoint delle anagrafiche condivise."""

import unittest
from contextlib import contextmanager
from unittest.mock import patch

from fastapi import HTTPException

from core.repositories import soggetti as soggetti_repo
from saas.main import aggiorna_soggetto, crea_soggetto
from saas.schemas import SoggettoCreate, SoggettoUpdate


class FakeCursor:
    def __init__(self):
        self.lastrowid = 13
        self.statements = []

    def execute(self, query, params=None):
        self.statements.append((query, params))

    def fetchone(self):
        return (
            13, 42, "Acme Srl", "azienda", None, None, None, None,
            "Via Roma", "1", "00100", "Roma", "RM", "Italia", None, None,
            None, None, 1, 1, 1, 1, 0, 7,
        )


class FakeConnection:
    def __init__(self):
        self._cursor = FakeCursor()
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self._cursor

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class SoggettiTests(unittest.TestCase):
    def test_schema_keeps_cap_as_text_and_supports_both_roles(self):
        soggetto = SoggettoCreate(
            denominazione="  Acme Srl  ",
            cap="00100",
            ruolo_cliente=True,
            ruolo_fornitore=True,
        )

        self.assertEqual(soggetto.denominazione, "Acme Srl")
        self.assertEqual(soggetto.cap, "00100")
        self.assertTrue(soggetto.ruolo_cliente)
        self.assertTrue(soggetto.ruolo_fornitore)

    def test_create_writes_subject_roles_and_supplier_settings_atomically(self):
        connection = FakeConnection()

        @contextmanager
        def fake_connection():
            yield connection

        with patch.object(soggetti_repo, "connection", fake_connection):
            soggetto = soggetti_repo.crea(
                42,
                SoggettoCreate(
                    denominazione="Acme Srl",
                    indirizzo="Via Roma",
                    cap="00100",
                    citta="Roma",
                    ruolo_cliente=True,
                    ruolo_fornitore=True,
                    flag1_ing_merce=True,
                ).model_dump(),
            )

        self.assertEqual(soggetto["id"], 13)
        self.assertEqual(soggetto["cap"], "00100")
        self.assertTrue(soggetto["ruolo_cliente"])
        self.assertTrue(soggetto["ruolo_fornitore"])
        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.rollbacks, 0)
        self.assertTrue(any("INSERT INTO soggetti_ruoli" in query for query, _ in connection._cursor.statements))
        supplier_insert = next(
            params for query, params in connection._cursor.statements
            if query.startswith("INSERT INTO fornitori")
        )
        self.assertEqual(supplier_insert[1:3], (1, 0))

    def test_create_uses_tenant_from_authenticated_user(self):
        payload = SoggettoCreate(
            denominazione="Acme Srl",
            ruolo_cliente=True,
            cap="00100",
        )
        expected = {"id": 13, "tenant_id": 42, **payload.model_dump()}

        with patch("saas.main.soggetti_service.crea_soggetto", return_value=expected) as create:
            result = crea_soggetto(payload, {"tenant_id": 42})

        self.assertEqual(result["id"], 13)
        create.assert_called_once_with(42, payload.model_dump())

    def test_update_preserves_unprovided_roles_and_fields(self):
        current = SoggettoCreate(
            denominazione="Acme Srl",
            indirizzo="Via Roma",
            cap="00100",
            ruolo_cliente=True,
            ruolo_fornitore=True,
        ).model_dump()
        current.update({"id": 13, "tenant_id": 42, "fornitore_legacy_id": 9})
        payload = SoggettoUpdate(denominazione="Acme Italia")

        with (
            patch("saas.main.soggetti_service.trova_soggetto", return_value=current),
            patch("saas.main.soggetti_service.aggiorna_soggetto", return_value=current) as update,
        ):
            aggiorna_soggetto(13, payload, {"tenant_id": 42})

        dati = update.call_args.args[2]
        self.assertEqual(dati["denominazione"], "Acme Italia")
        self.assertEqual(dati["indirizzo"], "Via Roma")
        self.assertTrue(dati["ruolo_cliente"])
        self.assertTrue(dati["ruolo_fornitore"])

    def test_update_reports_missing_subject(self):
        with patch("saas.main.soggetti_service.trova_soggetto", return_value=None):
            with self.assertRaises(HTTPException) as raised:
                aggiorna_soggetto(13, SoggettoUpdate(), {"tenant_id": 42})

        self.assertEqual(raised.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
