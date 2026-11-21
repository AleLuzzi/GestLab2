"""Export JSON/CSV del tenant, riservato all'admin e senza segreti."""

import io
import json
import unittest
import zipfile
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

import mysql.connector
from fastapi import HTTPException

from saas import auth
from saas.main import app, esporta_dati_tenant
from saas.services import export_tenant

TENANT = 4

SCHEMA = [
    ("tenant", "id"),
    ("tenant", "nome"),
    ("utenti", "id"),
    ("utenti", "tenant_id"),
    ("utenti", "email"),
    ("utenti", "password_hash"),
    ("password_reset", "id"),
    ("password_reset", "tenant_id"),
    ("password_reset", "token_hash"),
    ("refresh_token", "id"),
    ("refresh_token", "token_hash"),
    ("dispositivi_stampa", "id"),
    ("dispositivi_stampa", "tenant_id"),
    ("dispositivi_stampa", "nome"),
    ("dispositivi_stampa", "token"),
    ("lotti", "id"),
    ("lotti", "tenant_id"),
    ("lotti", "quantita"),
    ("lotti", "creato_il"),
    ("schema_migrazioni", "id"),
    ("schema_migrazioni", "nome"),
]


class FakeCursor:
    def __init__(self):
        self.statements = []
        self.result = []

    def execute(self, query, params=None):
        params = params or ()
        self.statements.append((query, params))
        if "information_schema.COLUMNS" in query:
            self.result = list(SCHEMA)
            return
        if "FROM `tenant`" in query:
            self.result = [(TENANT, "Laboratorio prova")] if params == (TENANT,) else [(9, "Altro")]
            return
        if "FROM `utenti`" in query:
            self.result = [(1, TENANT, "admin@laboratorio.it")]
            if "password_hash" in query:
                self.result[0] = self.result[0] + ("hash-segreto",)
            return
        if "FROM `dispositivi_stampa`" in query:
            self.result = [(3, TENANT, "Banco")]
            if "`token`" in query:
                self.result[0] = self.result[0] + ("token-segreto",)
            return
        if "FROM `lotti`" in query:
            self.result = [(8, TENANT, Decimal("1.500"), datetime(2026, 11, 21, 20, 11))]
            return
        if "FROM `password_reset`" in query or "FROM `refresh_token`" in query:
            self.result = [("token-segreto",)]
            return
        self.result = []

    def fetchall(self):
        return list(self.result)


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor


def _connection(cursor):
    @contextmanager
    def fake_connection():
        yield FakeConnection(cursor)

    return fake_connection


class ExportTenantTests(unittest.TestCase):
    def _raccogli(self):
        cursor = FakeCursor()
        with patch.object(export_tenant, "connection", _connection(cursor)):
            dati = export_tenant.raccogli(TENANT)
        return cursor, dati

    def test_queries_are_limited_to_the_caller_tenant_and_skip_secrets(self):
        cursor, dati = self._raccogli()
        select = [query for query, _params in cursor.statements if query.startswith("SELECT `")]
        self.assertTrue(select)
        for query, params in cursor.statements:
            if query.startswith("SELECT `"):
                self.assertEqual(params, (TENANT,))
        joined = "\n".join(query for query, _params in cursor.statements)
        self.assertNotIn("FROM `password_reset`", joined)
        self.assertNotIn("FROM `refresh_token`", joined)
        self.assertNotIn("FROM `schema_migrazioni`", joined)
        self.assertNotIn("password_hash", joined)
        self.assertNotIn("`token`", joined)
        self.assertNotIn("password_hash", dati["utenti"]["colonne"])
        self.assertNotIn("token", dati["dispositivi_stampa"]["colonne"])
        self.assertEqual(dati["utenti"]["righe"][0]["email"], "admin@laboratorio.it")
        self.assertEqual(dati["lotti"]["righe"][0]["quantita"], "1.500")
        self.assertEqual(dati["lotti"]["righe"][0]["creato_il"], "2026-11-21 20:11:00")
        self.assertEqual(list(dati), ["tenant", "dispositivi_stampa", "lotti", "utenti"])

    def test_json_and_csv_keep_tenant_rows_and_omit_secrets(self):
        cursor = FakeCursor()
        with patch.object(export_tenant, "connection", _connection(cursor)):
            contenuto, media, nome = export_tenant.prepara(TENANT, "json")
            zip_bytes, zip_media, zip_nome = export_tenant.prepara(TENANT, "csv")

        self.assertEqual((media, nome), ("application/json", "dati-laboratorio.json"))
        documento = json.loads(contenuto.decode("utf-8"))
        self.assertEqual(documento["tenant_id"], TENANT)
        self.assertEqual(documento["tabelle"]["tenant"][0]["nome"], "Laboratorio prova")
        self.assertNotIn("password_hash", json.dumps(documento))
        self.assertNotIn("token-segreto", json.dumps(documento))
        self.assertNotIn("hash-segreto", json.dumps(documento))

        self.assertEqual((zip_media, zip_nome), ("application/zip", "dati-laboratorio-csv.zip"))
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archivio:
            nomi = set(archivio.namelist())
            self.assertIn("LEGGIMI.txt", nomi)
            self.assertIn("utenti.csv", nomi)
            self.assertIn("lotti.csv", nomi)
            self.assertNotIn("password_reset.csv", nomi)
            self.assertNotIn("refresh_token.csv", nomi)
            utenti = archivio.read("utenti.csv").decode("utf-8-sig")
            self.assertIn("email", utenti.splitlines()[0])
            self.assertNotIn("password_hash", utenti)
            self.assertIn("admin@laboratorio.it", utenti)
            self.assertIn("1.500", archivio.read("lotti.csv").decode("utf-8-sig"))

    def test_endpoint_uses_the_token_tenant_and_rejects_a_requested_one(self):
        with patch.object(
            export_tenant,
            "prepara",
            return_value=(b"{}", "application/json", "dati-laboratorio.json"),
        ) as prepara:
            response = esporta_dati_tenant("json", None, {"tenant_id": TENANT, "ruolo": "admin"})
        prepara.assert_called_once_with(TENANT, "json")
        self.assertEqual(response.headers["content-disposition"], 'attachment; filename="dati-laboratorio.json"')

        with self.assertRaises(HTTPException) as errore:
            esporta_dati_tenant("json", 9, {"tenant_id": TENANT, "ruolo": "admin"})
        self.assertEqual(errore.exception.status_code, 400)

        with self.assertRaises(HTTPException) as formato:
            esporta_dati_tenant("xml", None, {"tenant_id": TENANT, "ruolo": "admin"})
        self.assertEqual(formato.exception.status_code, 400)
        self.assertIn("json oppure csv", formato.exception.detail)

    def test_database_errors_stay_generic(self):
        with patch.object(export_tenant, "prepara", side_effect=mysql.connector.Error("dettaglio sql")):
            with self.assertRaises(HTTPException) as errore:
                esporta_dati_tenant("csv", None, {"tenant_id": TENANT, "ruolo": "admin"})
        self.assertEqual(errore.exception.status_code, 500)
        self.assertNotIn("dettaglio sql", errore.exception.detail)

    def test_route_is_admin_only(self):
        route = next(route for route in app.routes if getattr(route, "path", None) == "/api/v1/export/tenant")
        ruoli = [
            getattr(dipendenza.call, "ruoli_ammessi", None)
            for dipendenza in route.dependant.dependencies
        ]
        self.assertIn(("admin",), ruoli)

        with self.assertRaises(HTTPException) as errore:
            auth.require_roles("admin")({"ruolo": "operatore", "tenant_id": 9})
        self.assertEqual(errore.exception.status_code, 403)
