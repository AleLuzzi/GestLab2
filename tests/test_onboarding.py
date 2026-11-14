"""Onboarding interno: tenant, dati OSA, primo admin e catalogo."""

import unittest
from contextlib import contextmanager, redirect_stdout
from io import StringIO
from unittest.mock import patch

import mysql.connector
from pydantic import ValidationError

from saas import onboarding as onboarding_cli
from saas.repositories import tenant_repo
from saas.schemas import OnboardingRichiesta
from saas.services import onboarding
from saas.services.onboarding import TEMPLATE_MACELLERIA, OnboardingError


def _richiesta(**sovrascritture):
    dati = {
        "nome": "Macelleria Rossi",
        "piano": "basic",
        "ragione_sociale": "Rossi Carni Srl",
        "indirizzo": "Via Roma 1, Milano",
        "laboratorio": "Laboratorio Rossi",
        "partita_iva": "12345678901",
        "email": "admin@rossi.example",
        "password": "Admin1234!",
        "catalogo": "vuoto",
    }
    dati.update(sovrascritture)
    return OnboardingRichiesta(**dati)


class FakeCursor:
    def __init__(self, handler=None):
        self.handler = handler
        self.statements = []
        self.lastrowid = 0

    def execute(self, query, params=None):
        self.statements.append((" ".join(query.split()), params))
        if self.handler is not None:
            self.handler(query, params)
        if query.lstrip().upper().startswith("INSERT"):
            self.lastrowid += 1


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


class OnboardingRepositoryTests(unittest.TestCase):
    def _esegui(self, articoli, handler=None):
        cursor = FakeCursor(handler)
        conn = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(tenant_repo, "connection", fake_connection):
            esito = tenant_repo.esegui_onboarding(
                "Macelleria Rossi",
                "pro",
                "Rossi Carni Srl",
                "Via Roma 1, Milano",
                "Laboratorio Rossi",
                "12345678901",
                "admin@rossi.example",
                "hash",
                articoli,
            )
        return esito, cursor, conn

    def test_empty_catalog_creates_tenant_osa_and_admin_in_one_transaction(self):
        esito, cursor, conn = self._esegui(())

        self.assertEqual(esito, {"tenant_id": 1, "utente_id": 2, "articoli": 0})
        tenant_sql, tenant_params = cursor.statements[0]
        self.assertIn("INSERT INTO tenant", tenant_sql)
        self.assertIn("osa_ragione_sociale", tenant_sql)
        self.assertEqual(
            tenant_params,
            (
                "Macelleria Rossi",
                "pro",
                "Rossi Carni Srl",
                "Via Roma 1, Milano",
                "Laboratorio Rossi",
                "12345678901",
            ),
        )
        utente_sql, utente_params = cursor.statements[1]
        self.assertIn("INSERT INTO utenti", utente_sql)
        self.assertEqual(
            utente_params,
            (1, "admin@rossi.example", "hash"),
        )
        self.assertNotIn("articoli", " ".join(sql for sql, _ in cursor.statements))
        self.assertEqual(conn.commits, 1)
        self.assertEqual(conn.rollbacks, 0)

    def test_butcher_template_inserts_articles_without_lots(self):
        esito, cursor, conn = self._esegui(TEMPLATE_MACELLERIA)

        articoli = [
            params
            for sql, params in cursor.statements
            if "INSERT INTO articoli" in sql
        ]
        self.assertEqual(len(articoli), len(TEMPLATE_MACELLERIA))
        self.assertEqual(articoli[2][1:], ("SUI-PANCIA", "Pancia di suino", "Suino", "kg", 1))
        self.assertEqual(
            articoli[-3][1:],
            ("PREP-SALSICCIA", "Salsicce fresche", "Preparato", "kg", 0),
        )
        self.assertNotIn("INSERT INTO lotti", " ".join(sql for sql, _ in cursor.statements))
        self.assertEqual(esito["articoli"], len(TEMPLATE_MACELLERIA))
        self.assertEqual(conn.commits, 1)

    def test_failed_article_insert_rolls_back_tenant_and_admin(self):
        def handler(query, _params):
            if "INSERT INTO articoli" in query:
                raise mysql.connector.Error("catalogo non scritto")

        cursor = FakeCursor(handler)
        conn = FakeConnection(cursor)

        @contextmanager
        def fake_connection():
            yield conn

        with patch.object(tenant_repo, "connection", fake_connection):
            with self.assertRaises(mysql.connector.Error):
                tenant_repo.esegui_onboarding(
                    "Macelleria Rossi",
                    "basic",
                    "Rossi Carni Srl",
                    "Via Roma 1",
                    "Laboratorio Rossi",
                    "12345678901",
                    "admin@rossi.example",
                    "hash",
                    TEMPLATE_MACELLERIA[:1],
                )

        self.assertEqual(conn.commits, 0)
        self.assertEqual(conn.rollbacks, 1)
        self.assertIn("INSERT INTO tenant", cursor.statements[0][0])
        self.assertIn("INSERT INTO utenti", cursor.statements[1][0])


class OnboardingServiceTests(unittest.TestCase):
    def test_password_policy_is_checked_before_insert(self):
        with patch.object(tenant_repo, "esegui_onboarding") as crea:
            with self.assertRaisesRegex(OnboardingError, "almeno una lettera"):
                onboarding.crea_laboratorio(_richiesta(password="1234567890"))
        crea.assert_not_called()

    def test_empty_catalog_passes_no_articles(self):
        with patch.object(onboarding.auth, "hash_password", return_value="hash"), \
                patch.object(
                    tenant_repo,
                    "esegui_onboarding",
                    return_value={"tenant_id": 7, "utente_id": 8, "articoli": 0},
                ) as crea:
            esito = onboarding.crea_laboratorio(_richiesta())

        self.assertEqual(crea.call_args.args[-1], ())
        self.assertEqual(esito["catalogo"], "vuoto")
        self.assertNotIn("password", esito)
        self.assertEqual(esito["tenant_id"], 7)

    def test_butcher_catalog_uses_the_template(self):
        with patch.object(onboarding.auth, "hash_password", return_value="hash"), \
                patch.object(
                    tenant_repo,
                    "esegui_onboarding",
                    return_value={
                        "tenant_id": 7,
                        "utente_id": 8,
                        "articoli": len(TEMPLATE_MACELLERIA),
                    },
                ) as crea:
            esito = onboarding.crea_laboratorio(_richiesta(catalogo="macelleria"))

        self.assertEqual(crea.call_args.args[-1], TEMPLATE_MACELLERIA)
        self.assertEqual(esito["articoli"], len(TEMPLATE_MACELLERIA))

    def test_duplicate_email_is_a_readable_error(self):
        errore = mysql.connector.IntegrityError("Duplicate entry for key 'email'")
        errore.errno = 1062
        with patch.object(onboarding.auth, "hash_password", return_value="hash"), \
                patch.object(tenant_repo, "esegui_onboarding", side_effect=errore):
            with self.assertRaisesRegex(OnboardingError, "questa email"):
                onboarding.crea_laboratorio(_richiesta())

    def test_partita_iva_must_be_eleven_digits(self):
        with self.assertRaises(ValidationError):
            _richiesta(partita_iva="IT12345678901")


class OnboardingCliTests(unittest.TestCase):
    def test_cli_creates_the_laboratory_without_printing_the_password(self):
        output = StringIO()
        with patch.object(
            onboarding_cli,
            "crea_laboratorio",
            return_value={
                "tenant_id": 4,
                "utente_id": 9,
                "email": "admin@rossi.example",
                "catalogo": "macelleria",
                "articoli": 9,
            },
        ) as crea, redirect_stdout(output):
            codice = onboarding_cli.main([
                "--nome", "Macelleria Rossi",
                "--piano", "pro",
                "--ragione-sociale", "Rossi Carni Srl",
                "--sede", "Via Roma 1, Milano",
                "--laboratorio", "Laboratorio Rossi",
                "--partita-iva", "12345678901",
                "--email", "admin@rossi.example",
                "--password", "Admin1234!",
                "--catalogo", "macelleria",
            ])

        self.assertEqual(codice, 0)
        self.assertNotIn("Admin1234!", output.getvalue())
        self.assertIn("Tenant ID: 4", output.getvalue())
        richiesta = crea.call_args.args[0]
        self.assertEqual(richiesta.piano, "pro")
        self.assertEqual(richiesta.catalogo, "macelleria")
        self.assertEqual(richiesta.indirizzo, "Via Roma 1, Milano")
        self.assertEqual(richiesta.password, "Admin1234!")
