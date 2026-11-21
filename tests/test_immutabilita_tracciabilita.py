"""Verifica che lotti e documenti di tracciabilità non siano cancellabili dall'API."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_FILE = ROOT / "saas" / "init_database.sql"
MAIN_FILE = ROOT / "saas" / "main.py"
CODE_DIRS = (ROOT / "saas", ROOT / "core")

TABELLE_TRACCIABILITA = (
    "lotti",
    "movimenti_lotto",
    "documenti_ingresso",
    "lavorazioni",
    "vendite",
    "righe_vendita",
)

DELETE_TRACCIABILITA = re.compile(
    r"DELETE\s+FROM\s+`?(" + "|".join(TABELLE_TRACCIABILITA) + r")`?",
    re.IGNORECASE,
)

SEGMENTI_API_NON_CANCELLABILI = (
    "tracciabilita",
    "vendite",
    "lotti",
    "documenti",
    "ingresso",
)


class ImmutabilitaTracciabilitaTests(unittest.TestCase):
    def test_api_non_espone_delete_su_lotti_vendite_e_documenti(self):
        main = MAIN_FILE.read_text(encoding="utf-8")
        for match in re.finditer(
            r'@app\.delete\(\s*["\']([^"\']+)["\']',
            main,
            re.DOTALL,
        ):
            path = match.group(1).strip()
            path_lower = path.lower()
            if any(segment in path_lower for segment in SEGMENTI_API_NON_CANCELLABILI):
                self.fail(f"DELETE non ammesso sulla tracciabilità: {path}")

    def test_schema_vincola_cancellazioni_a_restrict_tra_entita_tracciate(self):
        schema = SCHEMA_FILE.read_text(encoding="utf-8")
        for table in TABELLE_TRACCIABILITA:
            block = re.search(
                rf"CREATE TABLE IF NOT EXISTS `{table}` \((.*?)\) ENGINE=",
                schema,
                re.DOTALL,
            )
            self.assertIsNotNone(block, f"tabella {table} mancante nello schema")
            definition = block.group(1)
            foreign_keys = re.findall(
                r"REFERENCES `([^`]+)` \([^)]+\) ON DELETE (\w+)",
                definition,
            )
            self.assertTrue(foreign_keys, f"{table}: nessuna FK ON DELETE")
            for referenced, on_delete in foreign_keys:
                if referenced == "tenant":
                    continue
                with self.subTest(table=table, referenced=referenced):
                    self.assertEqual(
                        on_delete.upper(),
                        "RESTRICT",
                        f"{table} → {referenced} deve usare ON DELETE RESTRICT",
                    )

    def test_codice_non_contiene_delete_hard_su_tabelle_tracciabilita(self):
        violazioni = []
        for base in CODE_DIRS:
            for path in base.rglob("*.py"):
                if "test_" in path.name:
                    continue
                testo = path.read_text(encoding="utf-8")
                for match in DELETE_TRACCIABILITA.finditer(testo):
                    violazioni.append(f"{path.relative_to(ROOT)}: {match.group(0)}")
        self.assertEqual(violazioni, [])