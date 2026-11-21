import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TabletUiTests(unittest.TestCase):
    def test_viewport_tastiera_e_scanner_nei_flussi_operativi(self):
        pagina = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "web" / "app.css").read_text(encoding="utf-8")
        app = (ROOT / "web" / "js" / "app.js").read_text(encoding="utf-8")
        ingresso = (ROOT / "web" / "js" / "features" / "ingresso-merce.js").read_text(encoding="utf-8")
        vendite = (ROOT / "web" / "js" / "features" / "vendite.js").read_text(encoding="utf-8")
        dashboard = (ROOT / "web" / "js" / "features" / "dashboard.js").read_text(encoding="utf-8")
        tastiera = (ROOT / "web" / "js" / "core" / "tastiera.js").read_text(encoding="utf-8")

        self.assertIn('name="viewport" content="width=device-width, initial-scale=1.0"', pagina)
        self.assertIn('id="ean-input"', pagina)
        self.assertIn('inputmode="none"', pagina)
        self.assertIn('id="btn-ean-tastiera"', pagina)
        self.assertIn("font-size: 16px;", css)
        self.assertIn("min-height: 44px;", css)
        self.assertIn(".form-card.ingresso-card,", css)
        self.assertIn(".form-card.sales-selection { max-width: none; }", css)
        compatto = css.split("@media (max-width: 1024px)", 1)[1].split("@media", 1)[0]
        self.assertIn("margin-left: 0", compatto)
        self.assertIn("position: sticky", compatto)
        navigazione = (ROOT / "web" / "js" / "core" / "navigation.js").read_text(encoding="utf-8")
        for modulo in ("dashboard.js?v=20261121-5", "ingresso-merce.js?v=20261121-5", "vendite.js?v=20261121-5"):
            self.assertIn(modulo, app)
            self.assertIn(modulo, navigazione)
        self.assertIn("initTastieraVirtuale", app)
        self.assertIn('from "../core/scanner.js?v=20261121-5"', dashboard)
        self.assertIn('from "../core/scanner.js?v=20261121-5"', ingresso)
        self.assertIn('from "../core/scanner.js?v=20261121-5"', vendite)
        self.assertIn('from "./core/scanner.js?v=20261121-5"', app)
        self.assertIn("initScanner", app)
        self.assertIn("visualViewport", tastiera)
        self.assertIn("scrollIntoView", tastiera)
        self.assertIn("--keyboard-inset", tastiera)
        for modulo in (dashboard, ingresso, vendite):
            self.assertIn("registraScanner", modulo)
        scanner = (ROOT / "web" / "js" / "core" / "scanner.js").read_text(encoding="utf-8")
        self.assertIn("const INTERVALLO_MASSIMO_MS = 45;", scanner)
        self.assertIn("const LUNGHEZZA_MINIMA = 6;", scanner)
        self.assertIn("event.preventDefault()", scanner)

    def test_lo_scanner_accetta_solo_la_raffica_hid(self):
        nodo = shutil.which("node")
        if nodo is None:
            self.skipTest("Node non disponibile per il buffer dello scanner")
        modulo = (ROOT / "web" / "js" / "core" / "scanner.js").as_uri()
        script = """
import { creaBufferScanner } from "MODULO";

function raffica(intervallo, chiusura) {
  const buffer = creaBufferScanner();
  let istante = 1000;
  for (const carattere of '8001234567890') {
    istante += intervallo;
    buffer.aggiungi(carattere, istante);
  }
  return buffer.chiudi(istante + chiusura);
}

if (raffica(10, 10) !== '8001234567890') process.exit(1);
if (raffica(200, 10) !== null) process.exit(2);

const corto = creaBufferScanner();
let istante = 1000;
for (const carattere of '12345') {
  istante += 10;
  corto.aggiungi(carattere, istante);
}
if (corto.chiudi(istante + 10) !== null) process.exit(3);

const misto = creaBufferScanner();
misto.aggiungi('A', 1000);
if (misto.aggiungi('B', 1010) !== true) process.exit(4);
if (misto.aggiungi('C', 1200) !== false) process.exit(5);
""".replace("MODULO", modulo)
        risultato = subprocess.run(
            [nodo, "--input-type=module", "-e", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            risultato.returncode,
            0,
            risultato.stderr or risultato.stdout,
        )


if __name__ == "__main__":
    unittest.main()
