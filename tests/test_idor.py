"""Un GET del tenant A non restituisce record del tenant B."""

import unittest
from contextlib import contextmanager

from fastapi import HTTPException

from core.repositories import soggetti as soggetti_repo
from saas.main import (
    dettaglio_dispositivo,
    dettaglio_lotto_tracciato,
    dettaglio_soggetto,
    genera_ddt_vendita,
    stato_job,
)
from saas.repositories import print_repo, tracciabilita_repo

TENANT_A = 4
UTENTE_A = {"tenant_id": TENANT_A, "ruolo": "admin", "sub": "a@example.com"}


class LeakyCursor:
    """Restituisce il record altrui solo se la query non filtra il tenant chiamante."""

    def __init__(self, foreign_row):
        self.foreign_row = foreign_row
        self.result = []
        self.statements = []

    def execute(self, query, params=None):
        params = params or ()
        self.statements.append((query, params))
        scoped = "tenant_id" in query and TENANT_A in params
        if scoped:
            self.result = []
        elif isinstance(self.foreign_row, list):
            self.result = self.foreign_row
        else:
            self.result = [self.foreign_row]

    def fetchone(self):
        return self.result[0] if self.result else None

    def fetchall(self):
        return list(self.result)


class LeakyConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def commit(self):
        return None

    def rollback(self):
        return None


def _connection(cursor):
    @contextmanager
    def fake_connection():
        yield LeakyConnection(cursor)

    return fake_connection


class CrossTenantReadTests(unittest.TestCase):
    def _assert_not_found(self, error):
        self.assertEqual(error.exception.status_code, 404)

    def _assert_scoped(self, cursor):
        self.assertTrue(cursor.statements)
        query, params = cursor.statements[0]
        self.assertIn("tenant_id", query)
        self.assertIn(TENANT_A, params)

    def test_lot_of_another_tenant_is_not_found(self):
        cursor = LeakyCursor((99, 3, "Costata", "A", 1, "B-99") + (None,) * 21)
        with patch_connection(tracciabilita_repo, cursor):
            with self.assertRaises(HTTPException) as error:
                dettaglio_lotto_tracciato(99, UTENTE_A)
        self._assert_not_found(error)
        self._assert_scoped(cursor)

    def test_subject_of_another_tenant_is_not_found(self):
        cursor = LeakyCursor(
            (
                9, 7, "Cliente B", "azienda", None, None, None, None,
                None, None, None, None, None, "Italia", None, None,
                None, None, 1, 1, 0, 0, 0, None,
            )
        )
        with patch_connection(soggetti_repo, cursor):
            with self.assertRaises(HTTPException) as error:
                dettaglio_soggetto(9, UTENTE_A)
        self._assert_not_found(error)
        self._assert_scoped(cursor)

    def test_sale_of_another_tenant_is_not_found(self):
        cursor = LeakyCursor((8, 3, "2026-11-14", "DDT") + (None,) * 12)
        with patch_connection(tracciabilita_repo, cursor):
            with self.assertRaises(HTTPException) as error:
                genera_ddt_vendita(8, UTENTE_A)
        self._assert_not_found(error)
        self._assert_scoped(cursor)

    def test_print_job_of_another_tenant_is_not_found(self):
        cursor = LeakyCursor(
            [(6, 7, None, "etichetta", "pending", "{}", None, None)]
        )
        with patch_connection(print_repo, cursor):
            with self.assertRaises(HTTPException) as error:
                stato_job(6, UTENTE_A)
        self._assert_not_found(error)
        self._assert_scoped(cursor)

    def test_device_of_another_tenant_is_not_found(self):
        cursor = LeakyCursor((5, "Banco B", "DYMO B", None))
        with patch_connection(print_repo, cursor):
            with self.assertRaises(HTTPException) as error:
                dettaglio_dispositivo(5, UTENTE_A)
        self._assert_not_found(error)
        self._assert_scoped(cursor)
        self.assertNotIn("token", cursor.statements[0][0])


class patch_connection:
    def __init__(self, module, cursor):
        self.module = module
        self.cursor = cursor
        self._patch = None

    def __enter__(self):
        from unittest.mock import patch

        self._patch = patch.object(self.module, "connection", _connection(self.cursor))
        return self._patch.__enter__()

    def __exit__(self, exc_type, exc, tb):
        return self._patch.__exit__(exc_type, exc, tb)


if __name__ == "__main__":
    unittest.main()
