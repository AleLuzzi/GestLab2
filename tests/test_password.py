"""Policy password e reset via email."""

import unittest
from contextlib import contextmanager
from unittest.mock import patch

from fastapi import HTTPException

from saas import auth
from saas.main import crea_utente, password_dimenticata, password_reimposta
from saas.repositories import tenant_repo
from saas.schemas import (
    PasswordDimenticataRequest,
    PasswordReimpostaRequest,
    UtenteCreate,
)
from saas.services import password_reset


class PasswordPolicyTests(unittest.TestCase):
    def test_policy_rejects_short_password_without_letter_or_digit(self):
        with self.assertRaisesRegex(ValueError, "almeno 10 caratteri"):
            auth.valida_password("Corta1!")
        with self.assertRaisesRegex(ValueError, "almeno una lettera"):
            auth.valida_password("1234567890")
        with self.assertRaisesRegex(ValueError, "almeno un numero"):
            auth.valida_password("sololettere")

    def test_policy_accepts_a_mixed_password(self):
        auth.valida_password("Admin1234!")
        hashed = auth.hash_password("Admin1234!")
        self.assertTrue(auth.verify_password("Admin1234!", hashed))
        self.assertNotEqual(auth.hash_reset_token("segreto"), "segreto")

    def test_create_user_rejects_weak_password_before_saving(self):
        payload = UtenteCreate(email="operatore@example.com", password="corta")
        with patch.object(tenant_repo, "crea_utente") as create, self.assertRaises(
            HTTPException
        ) as error:
            crea_utente(payload, {"tenant_id": 4})

        self.assertEqual(error.exception.status_code, 400)
        self.assertIn("almeno 10 caratteri", error.exception.detail)
        create.assert_not_called()


class PasswordResetTests(unittest.TestCase):
    def test_missing_smtp_does_not_look_up_the_user(self):
        with patch.object(password_reset.mail, "smtp_configurato", return_value=False), \
                patch.object(tenant_repo, "trova_utente_by_email") as lookup, \
                self.assertRaises(password_reset.InvioEmailNonDisponibile):
            password_reset.richiedi_reimpostazione("admin@example.com")

        lookup.assert_not_called()

    def test_unknown_and_known_emails_share_the_same_message(self):
        sent = []

        def send(destinatario, oggetto, corpo):
            sent.append((destinatario, oggetto, corpo))

        utente = {
            "id": 9,
            "email": "admin@example.com",
            "attivo": 1,
        }
        with patch.object(password_reset.mail, "smtp_configurato", return_value=True), \
                patch.object(password_reset.mail, "invia_email", side_effect=send), \
                patch.object(tenant_repo, "trova_utente_by_email", return_value=None), \
                patch.object(tenant_repo, "salva_token_reset") as save:
            missing = password_reset.richiedi_reimpostazione("sconosciuto@example.com")
        save.assert_not_called()

        with patch.object(password_reset.mail, "smtp_configurato", return_value=True), \
                patch.object(password_reset.mail, "invia_email", side_effect=send), \
                patch.object(tenant_repo, "trova_utente_by_email", return_value=utente), \
                patch.object(tenant_repo, "salva_token_reset") as save:
            known = password_reset.richiedi_reimpostazione(utente["email"])

        self.assertEqual(missing, known)
        self.assertEqual(save.call_args.args[0], 9)
        stored_hash = save.call_args.args[1]
        self.assertEqual(len(stored_hash), 64)
        self.assertEqual(len(sent), 1)
        self.assertNotIn(stored_hash, sent[0][2])
        self.assertIn("/?reset=", sent[0][2])

    def test_failed_email_cancels_the_unused_token(self):
        utente = {"id": 9, "email": "admin@example.com", "attivo": 1}
        with patch.object(password_reset.mail, "smtp_configurato", return_value=True), \
                patch.object(
                    password_reset.mail, "invia_email", side_effect=OSError("smtp")
                ), \
                patch.object(tenant_repo, "trova_utente_by_email", return_value=utente), \
                patch.object(tenant_repo, "salva_token_reset") as save, \
                patch.object(tenant_repo, "annulla_token_reset") as cancel, \
                self.assertRaises(password_reset.InvioEmailNonDisponibile):
            password_reset.richiedi_reimpostazione(utente["email"])

        cancel.assert_called_once_with(save.call_args.args[1])

    def test_confirm_rejects_a_weak_password_without_consuming_the_token(self):
        with patch.object(tenant_repo, "consuma_token_reset") as consume, \
                self.assertRaisesRegex(ValueError, "almeno un numero"):
            password_reset.reimposta_password("token-lungo-di-reset-valido", "sololettere")
        consume.assert_not_called()

    def test_confirm_stores_the_new_hash_and_rejects_an_unknown_token(self):
        with patch.object(tenant_repo, "consuma_token_reset", return_value=True) as consume:
            password_reset.reimposta_password(
                "token-lungo-di-reset-valido", "NuovaPass1"
            )
        stored_hash = consume.call_args.args[1]
        self.assertTrue(auth.verify_password("NuovaPass1", stored_hash))
        self.assertEqual(
            consume.call_args.args[0],
            auth.hash_reset_token("token-lungo-di-reset-valido"),
        )

        with patch.object(tenant_repo, "consuma_token_reset", return_value=False):
            with self.assertRaises(password_reset.TokenResetNonValido):
                password_reset.reimposta_password(
                    "token-lungo-di-reset-scaduto", "NuovaPass1"
                )

    def test_request_endpoint_hides_lookup_when_smtp_is_missing(self):
        with patch.object(password_reset.mail, "smtp_configurato", return_value=False):
            with self.assertRaises(HTTPException) as error:
                password_dimenticata(
                    PasswordDimenticataRequest(email="admin@example.com")
                )
        self.assertEqual(error.exception.status_code, 503)
        self.assertIn("SMTP_HOST", error.exception.detail)

    def test_confirm_endpoint_returns_an_italian_success_message(self):
        with patch.object(tenant_repo, "consuma_token_reset", return_value=True):
            response = password_reimposta(
                PasswordReimpostaRequest(
                    token="token-lungo-di-reset-valido",
                    password="NuovaPass1",
                )
            )
        self.assertEqual(response.messaggio, "Password aggiornata. Ora puoi accedere.")


class PasswordResetRepositoryTests(unittest.TestCase):
    def test_consuming_a_token_updates_password_and_marks_it_used(self):
        cursor = _ResetCursor(row=(3, 9))
        connection = _FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield connection

        with patch.object(tenant_repo, "connection", fake_connection):
            updated = tenant_repo.consuma_token_reset("a" * 64, "hash-bcrypt")

        self.assertTrue(updated)
        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.rollbacks, 0)
        select, update_user, update_token = cursor.statements
        self.assertIn("FOR UPDATE", select[0])
        self.assertIn("%s", select[0])
        self.assertEqual(update_user[1], ("hash-bcrypt", 9))
        self.assertEqual(update_token[1], (3,))

    def test_missing_token_rolls_back_without_changing_the_password(self):
        cursor = _ResetCursor(row=None)
        connection = _FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield connection

        with patch.object(tenant_repo, "connection", fake_connection):
            updated = tenant_repo.consuma_token_reset("a" * 64, "hash-bcrypt")

        self.assertFalse(updated)
        self.assertEqual(connection.rollbacks, 1)
        self.assertEqual(connection.commits, 0)
        self.assertEqual(len(cursor.statements), 1)


class _ResetCursor:
    def __init__(self, row):
        self.row = row
        self.statements = []
        self.rowcount = 0
        self._query = ""

    def execute(self, query, params=None):
        self.statements.append((query, params))
        self._query = query
        if query.startswith("UPDATE utenti"):
            self.rowcount = 1

    def fetchone(self):
        if self._query.startswith("SELECT"):
            return self.row
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
