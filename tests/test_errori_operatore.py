"""Errori API mostrati all'operatore: frasi italiane, senza JSON."""

import asyncio
import json
import unittest
from pathlib import Path

from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from saas import main
from saas.errori_operatore import messaggio_validazione
from saas.schemas import LoginRequest


ROOT = Path(__file__).resolve().parents[1]


def _errori(modello, payload):
    try:
        modello.model_validate(payload)
    except ValidationError as exc:
        return exc.errors()
    raise AssertionError("la validazione doveva fallire")


class MessaggiValidazioneTests(unittest.TestCase):
    def test_campi_mancanti_e_email_non_sono_in_inglese(self):
        testo = messaggio_validazione(_errori(LoginRequest, {"email": "senza-chiocciola", "password": ""}))

        self.assertIn("Indirizzo email non valido.", testo)
        self.assertNotIn("Field required", testo)
        self.assertNotIn("valid email", testo)
        self.assertNotIn("{", testo)
        self.assertNotIn("should", testo.lower())

    def test_il_messaggio_personalizzato_resta_in_italiano(self):
        testo = messaggio_validazione([{
            "type": "value_error",
            "loc": ("body",),
            "msg": "Value error, Il tenant non si indica nella richiesta: arriva dal token di accesso.",
        }])

        self.assertEqual(
            testo,
            "Il tenant non si indica nella richiesta: arriva dal token di accesso.",
        )

    def test_la_riga_e_il_numero_non_valido_citano_il_campo(self):
        testo = messaggio_validazione([{
            "type": "decimal_parsing",
            "loc": ("body", "righe", 0, "quantita"),
            "msg": "Input should be a valid decimal",
        }])

        self.assertEqual(testo, "Riga 1: Quantità: inserire un numero.")

    def test_senza_errori_resta_una_frase_generica(self):
        self.assertEqual(messaggio_validazione([]), "Dati non validi.")


class HandlerValidazioneTests(unittest.TestCase):
    def test_la_risposta_422_ha_un_dettaglio_italiano(self):
        exc = RequestValidationError(_errori(LoginRequest, {}))

        async def esegui():
            return await main.errori_validazione(None, exc)

        risposta = asyncio.run(esegui())
        corpo = json.loads(risposta.body)

        self.assertEqual(risposta.status_code, 422)
        self.assertIsInstance(corpo["detail"], str)
        self.assertIn("Indirizzo email", corpo["detail"])
        self.assertIn("Password", corpo["detail"])
        self.assertNotIn("Field required", corpo["detail"])
        self.assertIs(
            main.app.exception_handlers[RequestValidationError],
            main.errori_validazione,
        )


class ClientErroriUiTests(unittest.TestCase):
    def test_la_console_non_mostra_il_json_dell_errore(self):
        client = (ROOT / "web" / "js" / "api" / "client.js").read_text(encoding="utf-8")

        self.assertIn("export function messaggioOperatore", client)
        self.assertIn("messaggioOperatore(detail, response.status)", client)
        self.assertIn("Elemento non trovato.", client)
        self.assertNotIn("JSON.stringify(body.detail", client)


if __name__ == "__main__":
    unittest.main()
