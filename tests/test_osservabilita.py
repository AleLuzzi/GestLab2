"""Health check, log operativo e segnalazione degli errori."""

import asyncio
import logging
import os
import sys
import unittest
from contextlib import contextmanager
from types import ModuleType
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request

from saas import main, osservabilita


def _richiesta(percorso="/api/v1/lotti"):
    return Request({
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": percorso,
        "raw_path": percorso.encode(),
        "query_string": b"token=segreto",
        "headers": [],
        "client": ("127.0.0.1", 9),
        "server": ("test", 80),
        "root_path": "",
    })


class HealthTests(unittest.TestCase):
    def test_health_is_ok_when_the_database_answers(self):
        @contextmanager
        def fake_connection():
            class Cursor:
                def execute(self, query):
                    self.query = query

                def fetchone(self):
                    return (1,)

            class Connection:
                def cursor(self):
                    return Cursor()

            yield Connection()

        with patch.object(osservabilita, "connection", fake_connection):
            codice, corpo = osservabilita.esito_salute()

        self.assertEqual(codice, 200)
        self.assertEqual(corpo, {"status": "ok", "database": "ok"})

    def test_health_is_degraded_when_the_database_is_down(self):
        @contextmanager
        def fake_connection():
            raise RuntimeError("connessione rifiutata")
            yield

        with patch.object(osservabilita, "connection", fake_connection), \
                self.assertLogs("gestlab.saas", level="ERROR") as logs:
            codice, corpo = osservabilita.esito_salute()

        self.assertEqual(codice, 503)
        self.assertEqual(corpo, {"status": "degraded", "database": "error"})
        self.assertIn("database non raggiungibile", logs.output[0])
        self.assertNotIn("connessione rifiutata", str(corpo))


class AccessLogTests(unittest.TestCase):
    def test_successful_health_check_is_not_logged(self):
        with self.assertNoLogs("gestlab.saas", level="INFO"):
            osservabilita.riga_accesso("GET", "/health", 200, 0.01)

    def test_failed_health_and_other_requests_are_logged_without_the_query(self):
        with self.assertLogs("gestlab.saas", level="INFO") as logs:
            osservabilita.riga_accesso("GET", "/health", 503, 0.2)
            osservabilita.riga_accesso("POST", "/api/v1/tracciabilita/ingressi", 201, 0.05)
            osservabilita.riga_accesso("GET", "/api/v1/lotti", 404, 0.01)

        testo = "\n".join(logs.output)
        self.assertIn("HTTP 503 GET /health 200ms", testo)
        self.assertIn("HTTP 201 POST /api/v1/tracciabilita/ingressi 50ms", testo)
        self.assertIn("HTTP 404 GET /api/v1/lotti 10ms", testo)
        self.assertNotIn("token=segreto", testo)


class ErrorTrackingTests(unittest.TestCase):
    def setUp(self):
        self.precedente = osservabilita._invia_errore
        osservabilita._invia_errore = None

    def tearDown(self):
        osservabilita._invia_errore = self.precedente

    def test_unhandled_error_gets_a_reference_and_notifies_the_tracker(self):
        ricevuti = []
        osservabilita._invia_errore = lambda errore, riferimento, metodo, percorso: ricevuti.append(
            (errore, riferimento, metodo, percorso)
        )
        errore = RuntimeError("guasto")
        with self.assertLogs("gestlab.saas", level="ERROR") as logs:
            riferimento = osservabilita.registra_errore("POST", "/api/v1/vendite", errore)

        self.assertEqual(len(riferimento), 32)
        self.assertIn(riferimento, logs.output[0])
        self.assertIn("Errore non gestito", logs.output[0])
        self.assertEqual(ricevuti, [(errore, riferimento, "POST", "/api/v1/vendite")])

    def test_tracker_failure_still_returns_the_reference(self):
        def guasto(*_args):
            raise RuntimeError("sentry irraggiungibile")

        osservabilita._invia_errore = guasto
        with self.assertLogs("gestlab.saas", level="ERROR"):
            riferimento = osservabilita.registra_errore(
                "GET", "/api/v1/lotti", RuntimeError("guasto")
            )
        self.assertEqual(len(riferimento), 32)

    def test_missing_sdk_is_reported_and_tracking_stays_off(self):
        with patch.dict(os.environ, {"SENTRY_DSN": "https://pubblica@example.ingest/1"}, clear=False), \
                patch.dict(sys.modules, {"sentry_sdk": None}), \
                self.assertLogs("gestlab.saas", level="ERROR") as logs:
            attivo = osservabilita.avvia_error_tracking()

        self.assertFalse(attivo)
        self.assertIsNone(osservabilita._invia_errore)
        self.assertIn("sentry-sdk non è installato", logs.output[0])

    def test_configured_dsn_sends_the_exception_without_default_pii(self):
        modulo = ModuleType("sentry_sdk")
        chiamate = {}

        def init(**kwargs):
            chiamate["init"] = kwargs

        def set_tag(chiave, valore):
            chiamate.setdefault("tag", []).append((chiave, valore))

        def capture_exception(errore):
            chiamate["errore"] = errore

        modulo.init = init
        modulo.set_tag = set_tag
        modulo.capture_exception = capture_exception
        errore = RuntimeError("guasto")
        with patch.dict(os.environ, {"SENTRY_DSN": "https://pubblica@example.ingest/1", "GESTLAB_ENV": "staging"}), \
                patch.dict(sys.modules, {"sentry_sdk": modulo}):
            self.assertTrue(osservabilita.avvia_error_tracking())
            riferimento = osservabilita.registra_errore("GET", "/api/v1/lotti", errore)

        self.assertEqual(chiamate["init"]["dsn"], "https://pubblica@example.ingest/1")
        self.assertEqual(chiamate["init"]["environment"], "staging")
        self.assertFalse(chiamate["init"]["send_default_pii"])
        self.assertIn(("riferimento", riferimento), chiamate["tag"])
        self.assertIn(("path", "/api/v1/lotti"), chiamate["tag"])
        self.assertIs(chiamate["errore"], errore)

    def test_http_exception_keeps_its_status_and_unhandled_errors_are_traced(self):
        async def esegui():
            nota = await main.errori_non_gestiti(
                _richiesta(), HTTPException(status_code=404, detail="Lotto non trovato")
            )
            with self.assertLogs("gestlab.saas", level="ERROR"):
                guasto = await main.errori_non_gestiti(
                    _richiesta(), RuntimeError("guasto imprevisto")
                )
            return nota, guasto

        nota, guasto = asyncio.run(esegui())
        self.assertEqual(nota.status_code, 404)
        self.assertEqual(guasto.status_code, 500)
        self.assertIn("Riferimento assistenza", guasto.body.decode())


if __name__ == "__main__":
    logging.basicConfig()
    unittest.main()
