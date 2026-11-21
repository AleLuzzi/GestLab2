"""Billing self-service e Stripe sono fuori perimetro v1 (piloti a contratto manuale)."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN_FILE = ROOT / "saas" / "main.py"
CODE_DIRS = (ROOT / "saas", ROOT / "core", ROOT / "web" / "js")

SAAAS_BILLING = re.compile(
    r"\b(stripe|paypal|abbonament|subscription|"
    r"/api/v1/billing|/api/v1/checkout|/api/v1/pagament)",
    re.IGNORECASE,
)


class BillingFuoriV1Tests(unittest.TestCase):
    def test_api_non_espone_billing_o_stripe(self):
        main = MAIN_FILE.read_text(encoding="utf-8")
        for decorator in ("@app.get", "@app.post", "@app.put", "@app.delete", "@app.patch"):
            for match in re.finditer(
                decorator + r'\(\s*["\']([^"\']+)["\']',
                main,
                re.DOTALL,
            ):
                path = match.group(1).strip().lower()
                if any(
                    keyword in path
                    for keyword in ("billing", "stripe", "subscription", "abbonament", "pagament")
                ):
                    self.fail(f"Endpoint billing non previsto in v1: {match.group(1)}")

    def test_login_non_verifica_canone_o_piano(self):
        main = MAIN_FILE.read_text(encoding="utf-8")
        login_block = re.search(
            r"def login\(.*?\n(?=def |\Z)",
            main,
            re.DOTALL,
        )
        self.assertIsNotNone(login_block)
        body = login_block.group(0).lower()
        for vietato in ("stripe", "billing", "canone", "abbonament", '["piano"]', "pagament"):
            self.assertNotIn(vietato, body, f"login non deve dipendere da {vietato}")

    def test_codice_saas_non_integra_provider_di_pagamento(self):
        violazioni = []
        for base in CODE_DIRS:
            if not base.is_dir():
                continue
            for path in base.rglob("*"):
                if path.suffix not in {".py", ".js"}:
                    continue
                if "test_" in path.name:
                    continue
                testo = path.read_text(encoding="utf-8")
                for match in SAAAS_BILLING.finditer(testo):
                    violazioni.append(f"{path.relative_to(ROOT)}: {match.group(0)}")
        self.assertEqual(violazioni, [])