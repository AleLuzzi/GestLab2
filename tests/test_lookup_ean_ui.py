import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LookupEanUiTests(unittest.TestCase):
    def test_la_dashboard_non_mostra_il_json_del_lookup(self):
        dashboard = (ROOT / "web" / "js" / "features" / "dashboard.js").read_text(encoding="utf-8")
        pagina = (ROOT / "web" / "index.html").read_text(encoding="utf-8")

        self.assertIn("export function riepilogoEan", dashboard)
        self.assertIn("ean-name", dashboard)
        self.assertNotIn("JSON.stringify", dashboard)
        self.assertIn('id="ean-result"', pagina)
        self.assertNotIn('id="ean-result" class="code-box"', pagina)
        self.assertNotIn("<pre id=\"ean-result\"", pagina)


if __name__ == "__main__":
    unittest.main()
