import os
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from core.services import printing
from saas.main import agent_next_job
from saas.print_agent import PrintAgent


class PrintAgentTests(unittest.TestCase):
    def test_receipt_print_includes_quantity_and_non_fiscal_notice(self):
        notice = (
            "GestLab · RICEVUTA NON FISCALE #12\n"
            "Documento non fiscale — non sostituisce lo scontrino del registratore telematico"
        )

        receipt = printing.genera_scontrino_escpos(
            testata=notice,
            righe=[
                {
                    "descrizione": "Salsiccia · lotto V-10",
                    "prezzo": "12,50 € / kg",
                    "qta": "1,250 kg",
                }
            ],
            totale="15,63 €",
            iva="0,00 €",
        ).decode("utf-8")

        self.assertIn("RICEVUTA NON FISCALE #12", receipt)
        self.assertIn("non sostituisce lo scontrino", receipt)
        self.assertIn("Salsiccia · lotto V-10", receipt)
        self.assertIn("1,250 kg", receipt)
        self.assertIn("12,50 € / kg", receipt)
        self.assertIn("15,63 €", receipt)
        self.assertIn("\x1d\x56\x41", receipt)

    def test_agent_job_contains_registered_dymo_name(self):
        queued_job = {
            "id": 12,
            "tenant_id": 42,
            "dispositivo_id": 5,
            "tipo": "etichetta",
            "payload": "{}",
        }
        with (
            patch(
                "saas.main.print_repo.trova_dispositivo_by_token",
                return_value={
                    "id": 5,
                    "stampante_dymo": "DYMO LabelWriter 450 Turbo",
                },
            ),
            patch("saas.main.print_repo.aggiorna_heartbeat"),
            patch(
                "saas.main.print_repo.prendi_prossimo_job",
                return_value=queued_job,
            ) as prendi_job,
        ):
            result = agent_next_job("device-token")

        prendi_job.assert_called_once_with(5)
        self.assertEqual(
            result["job"]["stampante_dymo"], "DYMO LabelWriter 450 Turbo"
        )

    def test_label_without_configured_dymo_fails(self):
        agent = PrintAgent("http://localhost", "device-token")
        with patch(
            "saas.print_agent.printing_service.stampa_pdf_via_win32"
        ) as stampa_pdf:
            result = agent._esegui_job({
                "id": 12,
                "tipo": "etichetta",
                "payload": '{"plu":"3","prodotto":"Salsiccia"}',
            })

        self.assertFalse(result)
        stampa_pdf.assert_not_called()

    def test_pdf_dispatch_targets_configured_windows_printer(self):
        win32api = Mock()
        win32api.ShellExecute.return_value = 33
        with tempfile.TemporaryDirectory() as output_dir:
            with patch.dict(sys.modules, {"win32api": win32api}):
                result = printing.stampa_pdf_via_win32(
                    b"%PDF-label",
                    nome_file="etichetta.pdf",
                    output_dir=output_dir,
                    printer_name="DYMO LabelWriter 450 Turbo",
                )

            self.assertTrue(result)
            win32api.ShellExecute.assert_called_once_with(
                None,
                "printto",
                os.path.join(output_dir, "etichetta.pdf"),
                '"DYMO LabelWriter 450 Turbo"',
                output_dir,
                0,
            )

    def test_pdf_dispatch_rejects_windows_print_failure(self):
        win32api = Mock()
        win32api.ShellExecute.return_value = 31
        with tempfile.TemporaryDirectory() as output_dir:
            with patch.dict(sys.modules, {"win32api": win32api}):
                with self.assertRaisesRegex(RuntimeError, "non ha accettato"):
                    printing.stampa_pdf_via_win32(
                        b"%PDF-label",
                        output_dir=output_dir,
                        printer_name="DYMO LabelWriter 450 Turbo",
                    )


if __name__ == "__main__":
    unittest.main()
