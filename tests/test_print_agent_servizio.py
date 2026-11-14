"""Configurazione e arresto del Local Print Agent come servizio."""

import os
import tempfile
import threading
import unittest
from unittest.mock import patch

from saas.print_agent import PrintAgent
from saas.print_agent_servizio import avviato_dal_gestore_servizi, carica_configurazione


class PrintAgentServiceConfigTests(unittest.TestCase):
    def test_configuration_reads_url_token_and_interval(self):
        with tempfile.TemporaryDirectory() as directory:
            percorso = os.path.join(directory, "print-agent.env")
            with open(percorso, "w", encoding="utf-8") as file:
                file.write(
                    "# segreto locale\n"
                    "GESTLAB_API_URL=https://app.example.com\n"
                    "GESTLAB_AGENT_TOKEN=token-banco\n"
                    "GESTLAB_AGENT_INTERVAL=8\n"
                )
            url, token, intervallo = carica_configurazione(percorso)

        self.assertEqual(url, "https://app.example.com")
        self.assertEqual(token, "token-banco")
        self.assertEqual(intervallo, 8.0)

    def test_configuration_accepts_a_windows_bom(self):
        with tempfile.TemporaryDirectory() as directory:
            percorso = os.path.join(directory, "print-agent.env")
            with open(percorso, "w", encoding="utf-8-sig") as file:
                file.write(
                    "GESTLAB_API_URL=https://app.example.com\n"
                    "GESTLAB_AGENT_TOKEN=token-banco\n"
                )
            url, token, intervallo = carica_configurazione(percorso)

        self.assertEqual(url, "https://app.example.com")
        self.assertEqual(token, "token-banco")
        self.assertEqual(intervallo, 5.0)

    def test_configuration_requires_url_and_token(self):
        with tempfile.TemporaryDirectory() as directory:
            percorso = os.path.join(directory, "print-agent.env")
            with open(percorso, "w", encoding="utf-8") as file:
                file.write("GESTLAB_API_URL=https://app.example.com\n")
            with self.assertRaisesRegex(RuntimeError, "GESTLAB_AGENT_TOKEN"):
                carica_configurazione(percorso)

    def test_stop_ends_the_polling_loop(self):
        agent = PrintAgent("http://127.0.0.1:9", "token-banco", interval=30)
        agent._get = lambda path: {"job": None}
        thread = threading.Thread(target=agent.run)
        thread.start()
        agent.ferma()
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())

    def test_service_host_does_not_treat_startup_as_an_install_command(self):
        with patch("saas.print_agent_servizio.sys.executable", r"C:\venv\pythonservice.exe"):
            self.assertTrue(avviato_dal_gestore_servizi())
        with patch("saas.print_agent_servizio.sys.executable", r"C:\venv\Scripts\python.exe"):
            self.assertFalse(avviato_dal_gestore_servizi())
