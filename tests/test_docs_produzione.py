"""In produzione Swagger, ReDoc e lo schema OpenAPI non sono pubblicati."""

import asyncio
import json
import os
import unittest
from unittest.mock import patch

from saas import main


async def _richiesta(path):
    messaggi = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messaggi.append(message)

    await main.app(
        {
            "type": "http",
            "asgi": {"spec_version": "2.3", "version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 1234),
            "server": ("testserver", 80),
            "root_path": "",
        },
        receive,
        send,
    )
    start = next(m for m in messaggi if m["type"] == "http.response.start")
    body = b"".join(
        m.get("body", b"") for m in messaggi if m["type"] == "http.response.body"
    )
    headers = {k.decode().lower(): v.decode() for k, v in start.get("headers", [])}
    return start["status"], headers, body


def richiedi(path):
    return asyncio.run(_richiesta(path))


class DocsProduzioneTests(unittest.TestCase):
    def test_fuori_produzione_la_documentazione_resta_aperta(self):
        with patch.dict(os.environ, {"GESTLAB_ENV": "development"}):
            docs, docs_headers, docs_body = richiedi("/docs")
            schema, _, schema_body = richiedi("/openapi.json")

        self.assertEqual(docs, 200)
        self.assertIn("text/html", docs_headers["content-type"])
        self.assertIn("swagger", docs_body.decode().lower())
        self.assertEqual(schema, 200)
        self.assertIn("/api/v1", schema_body.decode())

    def test_produzione_chiude_docs_redoc_e_schema(self):
        with patch.dict(os.environ, {"GESTLAB_ENV": " Production "}):
            for percorso in ("/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json"):
                codice, _, body = richiedi(percorso)
                testo = body.decode()
                self.assertEqual(codice, 404, percorso)
                self.assertEqual(json.loads(testo), {"detail": "Non disponibile."})
                self.assertNotIn("swagger", testo.lower())
                self.assertNotIn("openapi", testo.lower())

    def test_produzione_lascia_aperta_la_console(self):
        with patch.dict(os.environ, {"GESTLAB_ENV": "production"}):
            codice, headers, _ = richiedi("/")

        self.assertEqual(codice, 200)
        self.assertIn("text/html", headers["content-type"])

    def test_staging_mantiene_la_documentazione(self):
        with patch.dict(os.environ, {"GESTLAB_ENV": "staging"}):
            codice, headers, _ = richiedi("/redoc")

        self.assertEqual(codice, 200)
        self.assertIn("text/html", headers["content-type"])
