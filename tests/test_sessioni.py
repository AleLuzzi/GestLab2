"""Rate limit del login, rotazione dei refresh token e logout."""

import unittest
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from saas import auth
from saas.main import login, logout, refresh_token
from saas.repositories import tenant_repo
from saas.schemas import LoginRequest, LogoutRequest, RefreshRequest
from saas.services import login_guard, sessioni


def _richiesta(host="203.0.113.10"):
    return SimpleNamespace(client=SimpleNamespace(host=host))


class LoginLimitTests(unittest.TestCase):
    def setUp(self):
        self.now = [1_000.0]
        self.previous = login_guard.guard
        login_guard.guard = login_guard.LoginGuard(
            finestra_secondi=900,
            clock=lambda: self.now[0],
        )

    def tearDown(self):
        login_guard.guard = self.previous

    def test_eleventh_failure_for_the_same_email_is_rejected(self):
        payload = LoginRequest(email="admin@example.com", password="sbagliata")
        with patch.object(tenant_repo, "trova_utente_by_email", return_value=None) as lookup:
            for _ in range(10):
                with self.assertRaises(HTTPException) as error:
                    login(payload, _richiesta())
                self.assertEqual(error.exception.status_code, 401)
            with self.assertRaises(HTTPException) as limited:
                login(payload, _richiesta())

        self.assertEqual(limited.exception.status_code, 429)
        self.assertIn("Troppi tentativi", limited.exception.detail)
        self.assertEqual(limited.exception.headers["Retry-After"], "900")
        self.assertEqual(lookup.call_count, 10)

    def test_a_successful_login_clears_the_email_counter(self):
        utente = {
            "id": 9,
            "tenant_id": 4,
            "email": "admin@example.com",
            "password_hash": "hash",
            "ruolo": "admin",
            "attivo": 1,
        }
        wrong = LoginRequest(email="admin@example.com", password="sbagliata1")
        right = LoginRequest(email="admin@example.com", password="Giusta1234")
        with patch.object(tenant_repo, "trova_utente_by_email", return_value=utente), \
                patch.object(auth, "verify_password", side_effect=[False] * 9 + [True]), \
                patch.object(sessioni, "apri_sessione", return_value=("access", "refresh")):
            for _ in range(9):
                with self.assertRaises(HTTPException):
                    login(wrong, _richiesta())
            response = login(right, _richiesta())
        self.assertEqual(response.access_token, "access")

        with patch.object(tenant_repo, "trova_utente_by_email", return_value=None):
            for _ in range(10):
                with self.assertRaises(HTTPException) as error:
                    login(wrong, _richiesta())
                self.assertEqual(error.exception.status_code, 401)

    def test_shared_ip_stops_after_fifty_failures_across_emails(self):
        with patch.object(tenant_repo, "trova_utente_by_email", return_value=None):
            for index in range(50):
                payload = LoginRequest(
                    email=f"utente{index}@example.com",
                    password="sbagliata",
                )
                with self.assertRaises(HTTPException) as error:
                    login(payload, _richiesta("198.51.100.4"))
                self.assertEqual(error.exception.status_code, 401)
            with self.assertRaises(HTTPException) as limited:
                login(
                    LoginRequest(email="nuovo@example.com", password="sbagliata"),
                    _richiesta("198.51.100.4"),
                )
        self.assertEqual(limited.exception.status_code, 429)

    def test_failures_expire_after_the_window(self):
        payload = LoginRequest(email="admin@example.com", password="sbagliata")
        with patch.object(tenant_repo, "trova_utente_by_email", return_value=None):
            for _ in range(10):
                with self.assertRaises(HTTPException):
                    login(payload, _richiesta())
            self.now[0] += 901
            with self.assertRaises(HTTPException) as error:
                login(payload, _richiesta())
        self.assertEqual(error.exception.status_code, 401)


class SessionServiceTests(unittest.TestCase):
    def test_login_persists_only_the_refresh_hash(self):
        utente = {
            "id": 9,
            "email": "admin@example.com",
            "tenant_id": 4,
            "ruolo": "admin",
        }
        with patch.object(tenant_repo, "salva_refresh_token") as save:
            access, refresh = sessioni.apri_sessione(utente)

        jti = auth.decode_token(refresh)["jti"]
        self.assertEqual(save.call_args.args[0], 9)
        self.assertEqual(save.call_args.args[1], auth.hash_token(jti))
        self.assertNotEqual(save.call_args.args[1], jti)
        self.assertNotIn("jti", auth.decode_token(access))

    def test_refresh_rotates_the_token_and_reads_the_current_role(self):
        vecchio = auth.create_token(
            "admin@example.com", 4, "admin", "refresh", jti="jti-vecchio"
        )
        with patch.object(
            tenant_repo,
            "ruota_refresh_token",
            return_value={
                "stato": "ruotato",
                "utente": {
                    "id": 9,
                    "tenant_id": 4,
                    "email": "admin@example.com",
                    "ruolo": "operatore",
                },
            },
        ) as rotate:
            access, refresh = sessioni.rinnova_sessione(vecchio)

        self.assertEqual(rotate.call_args.args[0], auth.hash_token("jti-vecchio"))
        self.assertEqual(auth.decode_token(access)["ruolo"], "operatore")
        self.assertNotEqual(auth.decode_token(refresh)["jti"], "jti-vecchio")
        self.assertEqual(auth.decode_token(refresh)["type"], "refresh")

    def test_reused_refresh_is_rejected(self):
        vecchio = auth.create_token(
            "admin@example.com", 4, "admin", "refresh", jti="jti-gia-usato"
        )
        with patch.object(
            tenant_repo, "ruota_refresh_token", return_value={"stato": "riuso"}
        ):
            with self.assertRaises(HTTPException) as error:
                sessioni.rinnova_sessione(vecchio)
        self.assertEqual(error.exception.status_code, 401)
        self.assertIn("Sessione non più valida", error.exception.detail)

    def test_logout_revokes_the_presented_family(self):
        refresh = auth.create_token(
            "admin@example.com", 4, "admin", "refresh", jti="jti-aperto"
        )
        with patch.object(tenant_repo, "revoca_refresh_token") as revoke:
            sessioni.chiudi_sessione(refresh)
            response = logout(LogoutRequest(refresh_token=refresh))
        self.assertEqual(revoke.call_args.args[0], auth.hash_token("jti-aperto"))
        self.assertEqual(response.messaggio, "Sessione chiusa.")

    def test_refresh_endpoint_returns_the_rotated_pair(self):
        with patch.object(
            sessioni, "rinnova_sessione", return_value=("nuovo-access", "nuovo-refresh")
        ), patch.object(
            auth,
            "decode_token",
            return_value={"sub": "admin@example.com", "ruolo": "admin", "tenant_id": 4},
        ):
            response = refresh_token(RefreshRequest(refresh_token="vecchio"))
        self.assertEqual(response.access_token, "nuovo-access")
        self.assertEqual(response.refresh_token, "nuovo-refresh")


class RefreshRepositoryTests(unittest.TestCase):
    def test_rotation_revokes_the_old_token_and_keeps_the_family(self):
        cursor = _RefreshCursor(
            token_row=(1, 9, "famiglia-1", 0, 0),
            user_row=(9, 4, "admin@example.com", "operatore", 1),
        )
        connection = _FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield connection

        with patch.object(tenant_repo, "connection", fake_connection):
            esito = tenant_repo.ruota_refresh_token("a" * 64, "b" * 64, "2026-11-21")

        self.assertEqual(esito["stato"], "ruotato")
        self.assertEqual(esito["utente"]["ruolo"], "operatore")
        self.assertEqual(connection.commits, 1)
        select, user_select, insert, update = cursor.statements
        self.assertIn("FOR UPDATE", select[0])
        self.assertEqual(insert[1][1:], ("b" * 64, "famiglia-1", "2026-11-21"))
        self.assertEqual(update[1], (1,))
        self.assertIn("revocato_il", update[0])

    def test_reuse_revokes_the_whole_family(self):
        cursor = _RefreshCursor(token_row=(1, 9, "famiglia-1", 1, 0))
        connection = _FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield connection

        with patch.object(tenant_repo, "connection", fake_connection):
            esito = tenant_repo.ruota_refresh_token("a" * 64, "b" * 64, "2026-11-21")

        self.assertEqual(esito["stato"], "riuso")
        self.assertEqual(connection.commits, 1)
        self.assertEqual(len(cursor.statements), 2)
        self.assertEqual(cursor.statements[1][1], ("famiglia-1",))
        self.assertNotIn("INSERT", cursor.statements[1][0])

    def test_missing_token_does_not_create_a_successor(self):
        cursor = _RefreshCursor(token_row=None)
        connection = _FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield connection

        with patch.object(tenant_repo, "connection", fake_connection):
            esito = tenant_repo.ruota_refresh_token("a" * 64, "b" * 64, "2026-11-21")

        self.assertEqual(esito["stato"], "non_valido")
        self.assertEqual(connection.rollbacks, 1)
        self.assertEqual(connection.commits, 0)
        self.assertEqual(len(cursor.statements), 1)

    def test_logout_revokes_every_open_token_of_the_family(self):
        cursor = _RefreshCursor(token_row=(8, 9, "famiglia-2", 0, 0))
        connection = _FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield connection

        with patch.object(tenant_repo, "connection", fake_connection):
            tenant_repo.revoca_refresh_token("c" * 64)

        self.assertEqual(connection.commits, 1)
        select, update = cursor.statements
        self.assertIn("FOR UPDATE", select[0])
        self.assertEqual(update[1], ("famiglia-2",))


class _RefreshCursor:
    def __init__(self, token_row, user_row=None):
        self.token_row = token_row
        self.user_row = user_row
        self.statements = []
        self._query = ""

    def execute(self, query, params=None):
        self.statements.append((query, params))
        self._query = " ".join(query.split())

    def fetchone(self):
        if self._query.startswith("SELECT id, utente_id, famiglia"):
            return self.token_row
        if self._query.startswith("SELECT id, tenant_id"):
            return self.user_row
        if self._query.startswith("SELECT famiglia"):
            return None if self.token_row is None else (self.token_row[2],)
        return None


class _FakeConnection:
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


if __name__ == "__main__":
    unittest.main()
