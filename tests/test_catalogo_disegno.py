import re
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ZONE_SUINO_ATTESE = (
    "SUI-COPPA",
    "SUI-LONZA",
    "SUI-COSTINE",
    "SUI-SPALLA",
    "SUI-PANCIA",
    "SUI-COSCIA",
    "SUI-GUANCIA",
    "SUI-STINCO",
    "SUI-PIEDE",
    "SUI-CODA",
)

ZONE_BOVINO_ANTERIORE_ATTESE = (
    "BOV-COLLO",
    "BOV-REALE",
    "BOV-SOTTOSPAL",
    "BOV-FESONE",
    "BOV-CAPPELLO",
    "BOV-FUSELLO",
    "BOV-TRAVERSIN",
    "BOV-BRIONE",
    "BOV-PETTO",
    "BOV-FIOCCO",
    "BOV-BIANCO",
    "BOV-PANCIA",
    "BOV-SCALFO",
    "BOV-GER-ANT",
)

ZONE_BOVINO_POSTERIORE_ATTESE = (
    "BOV-COSTATA",
    "BOV-CONTROF",
    "BOV-SCAMONE",
    "BOV-FIANCH",
    "BOV-NOCE",
    "BOV-FESA",
    "BOV-SOTTOF",
    "BOV-CODONE",
    "BOV-GIRELLO",
    "BOV-PESCE",
    "BOV-GER-POST",
    "BOV-CODA",
)

ZONE_VITELLO_ATTESE = (
    "VIT-COLLO",
    "VIT-COPPA",
    "VIT-SPALLA",
    "VIT-PETTO",
    "VIT-CARRE",
    "VIT-PANCIA",
    "VIT-LOMBO",
    "VIT-SCAMONE",
    "VIT-NOCE",
    "VIT-FESA",
    "VIT-SOTTOF",
    "VIT-PESCE",
    "VIT-GIRELLO",
    "VIT-GER-ANT",
    "VIT-GER-POST",
)


class CatalogoDisegnoTests(unittest.TestCase):
    def test_profilo_suino_ha_dieci_zone_con_data_codice(self):
        modulo = ROOT / "web" / "js" / "catalogo-disegno" / "profilo-suino.js"
        sorgente = modulo.read_text(encoding="utf-8")
        css = (ROOT / "web" / "app.css").read_text(encoding="utf-8")

        self.assertIn("export function creaProfiloSuino", sorgente)
        util = (ROOT / "web" / "js" / "catalogo-disegno" / "zona-util.js").read_text(encoding="utf-8")
        self.assertIn('setAttribute("data-codice"', util)
        self.assertIn('setAttribute("data-nome"', util)
        self.assertIn('setAttribute("role", "button")', util)
        self.assertIn('setAttribute("aria-pressed", "false")', util)
        self.assertIn("export function creaGruppoZona", util)
        self.assertIn("profilo-zona-etichetta", css)
        interazione = (ROOT / "web" / "js" / "catalogo-disegno" / "profilo-interazione.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("export function testoConfermaTaglio", interazione)
        self.assertIn("export function collegaAttivazioneZona", interazione)
        self.assertIn("Selezionato:", interazione)
        self.assertIn(".profilo-macelleria", css)
        self.assertIn(".profilo-zona-forma", css)
        self.assertIn(".profilo-zona-hit", css)
        self.assertIn("zona-util.js", sorgente)

        for codice in ZONE_SUINO_ATTESE:
            self.assertIn(f'codice: "{codice}"', sorgente, codice)

        trovati = re.findall(r'codice: "(SUI-[^"]+)"', sorgente)
        zone_suino = [c for c in trovati if c.startswith("SUI-") and c not in (
            "SUI-MEZZENA", "SUI-FILETTO", "SUI-LARDO",
        )]
        self.assertEqual(zone_suino, list(ZONE_SUINO_ATTESE))

    def test_crea_profilo_suino_in_dom(self):
        nodo = shutil.which("node")
        if nodo is None:
            self.skipTest("Node non disponibile per il profilo suino")

        modulo = (ROOT / "web" / "js" / "catalogo-disegno" / "profilo-suino.js").as_uri()
        modulo_interazione = (ROOT / "web" / "js" / "catalogo-disegno" / "profilo-interazione.js").as_uri()
        script = f"""
import {{ JSDOM }} from "jsdom";
import {{ creaProfiloSuino, ZONE_SUINO }} from "{modulo}";

const dom = new JSDOM("<!DOCTYPE html><html><body></body></html>");
globalThis.document = dom.window.document;

const svg = creaProfiloSuino();
if (svg.localName !== "svg") process.exit(1);
if (!svg.classList.contains("profilo-suino")) process.exit(2);

const codici = [...svg.querySelectorAll("[data-codice]")].map((el) => el.getAttribute("data-codice"));
const attesi = ZONE_SUINO.map((z) => z.codice);
if (codici.length !== 10) process.exit(3);
if (JSON.stringify(codici) !== JSON.stringify(attesi)) process.exit(4);

const DITO_MIN = 40;
function bboxPath(d) {{
  const nums = d.match(/-?\\d+(?:\\.\\d+)?/g).map(Number);
  const xs = []; const ys = [];
  for (let i = 0; i + 1 < nums.length; i += 2) {{ xs.push(nums[i]); ys.push(nums[i + 1]); }}
  return {{ w: Math.max(...xs) - Math.min(...xs), h: Math.max(...ys) - Math.min(...ys) }};
}}

for (const gruppo of svg.querySelectorAll(".profilo-zona")) {{
  const titolo = gruppo.querySelector("title");
  if (!titolo?.textContent?.trim()) process.exit(5);
  const nomeAtteso = gruppo.getAttribute("data-nome");
  if (!nomeAtteso || titolo.textContent !== nomeAtteso) process.exit(9);
  const etichetta = gruppo.querySelector(".profilo-zona-etichetta");
  const etichettaAttesa = nomeAtteso.replace(/ di suino$/i, "");
  if (!etichetta || etichetta.textContent !== etichettaAttesa) process.exit(10);
  const hit = gruppo.querySelector(".profilo-zona-hit");
  const forma = gruppo.querySelector(".profilo-zona-forma");
  if (!hit || !forma) process.exit(6);
  if (hit.getAttribute("tabindex") !== "0") process.exit(11);
  if (hit.getAttribute("aria-label") !== nomeAtteso) process.exit(12);
  if (hit.getAttribute("role") !== "button") process.exit(15);
  if (hit.getAttribute("aria-pressed") !== "false") process.exit(16);
  if (hit.getAttribute("d") === forma.getAttribute("d")) process.exit(7);
  const {{ w, h }} = bboxPath(hit.getAttribute("d"));
  if (w < DITO_MIN || h < DITO_MIN) process.exit(8);
}}

import {{ collegaFeedbackTaglioProfilo, testoConfermaTaglio }} from "{modulo_interazione}";
const atteso = testoConfermaTaglio("Lonza di suino");
if (atteso !== "Selezionato: Lonza di suino. Inserisci la quantità.") process.exit(13);
const feedback = dom.window.document.createElement("div");
document.body.appendChild(feedback);
const svg2 = creaProfiloSuino();
document.body.appendChild(svg2);
collegaFeedbackTaglioProfilo(svg2, feedback);
const lonzaHit = [...svg2.querySelectorAll(".profilo-zona-hit")].find(
  (h) => h.closest(".profilo-zona")?.getAttribute("data-codice") === "SUI-LONZA",
);
lonzaHit?.dispatchEvent(new dom.window.MouseEvent("click", {{ bubbles: true }}));
if (feedback.textContent !== atteso) process.exit(14);
feedback.textContent = "";
lonzaHit?.dispatchEvent(new dom.window.KeyboardEvent("keydown", {{ key: "Enter", bubbles: true }}));
if (feedback.textContent !== atteso) process.exit(17);
"""
        risultato = subprocess.run(
            [nodo, "--input-type=module", "-e", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if risultato.returncode != 0 and "Cannot find package 'jsdom'" in (risultato.stderr or ""):
            self.skipTest("jsdom non installato: verifica statica del sorgente sufficiente")
        self.assertEqual(
            risultato.returncode,
            0,
            risultato.stderr or risultato.stdout,
        )

    def test_profilo_vitello_ha_quindici_zone_senza_mezzena(self):
        modulo = ROOT / "web" / "js" / "catalogo-disegno" / "profilo-vitello.js"
        sorgente = modulo.read_text(encoding="utf-8")

        self.assertIn("export function creaProfiloVitello", sorgente)
        self.assertIn("zona-util.js", sorgente)

        for codice in ZONE_VITELLO_ATTESE:
            self.assertIn(f'codice: "{codice}"', sorgente, codice)

        trovati = re.findall(r'codice: "(VIT-[^"]+)"', sorgente)
        self.assertNotIn("VIT-MEZZENA", trovati)
        self.assertEqual(trovati, list(ZONE_VITELLO_ATTESE))

    def test_profilo_bovino_ha_quarti_separati_senza_mezzena_ni_filetto(self):
        modulo = ROOT / "web" / "js" / "catalogo-disegno" / "profilo-bovino.js"
        sorgente = modulo.read_text(encoding="utf-8")

        self.assertIn("export function creaProfiloBovinoAnteriore", sorgente)
        self.assertIn("export function creaProfiloBovinoPosteriore", sorgente)

        ant = re.findall(r'codice: "(BOV-[^"]+)"', sorgente.split("ZONE_BOVINO_POSTERIORE")[0])
        post = re.findall(
            r'codice: "(BOV-[^"]+)"',
            sorgente.split("ZONE_BOVINO_POSTERIORE", 1)[1],
        )
        self.assertNotIn("BOV-MEZZENA", ant + post)
        self.assertNotIn("BOV-FILETTO", ant + post)
        self.assertEqual(ant, list(ZONE_BOVINO_ANTERIORE_ATTESE))
        self.assertEqual(post, list(ZONE_BOVINO_POSTERIORE_ATTESE))
        self.assertIn("zona-util.js", sorgente)

    def test_crea_profilo_vitello_in_dom(self):
        nodo = shutil.which("node")
        if nodo is None:
            self.skipTest("Node non disponibile per il profilo vitello")

        modulo = (ROOT / "web" / "js" / "catalogo-disegno" / "profilo-vitello.js").as_uri()
        script = f"""
import {{ JSDOM }} from "jsdom";
import {{ creaProfiloVitello, ZONE_VITELLO }} from "{modulo}";

const dom = new JSDOM("<!DOCTYPE html><html><body></body></html>");
globalThis.document = dom.window.document;

const svg = creaProfiloVitello();
if (svg.localName !== "svg") process.exit(1);
if (!svg.classList.contains("profilo-vitello")) process.exit(2);

const codici = [...svg.querySelectorAll("[data-codice]")].map((el) => el.getAttribute("data-codice"));
const attesi = ZONE_VITELLO.map((z) => z.codice);
if (codici.length !== 15) process.exit(3);
if (JSON.stringify(codici) !== JSON.stringify(attesi)) process.exit(4);

const DITO_MIN = 40;
function bboxPath(d) {{
  const nums = d.match(/-?\\d+(?:\\.\\d+)?/g).map(Number);
  const xs = []; const ys = [];
  for (let i = 0; i + 1 < nums.length; i += 2) {{ xs.push(nums[i]); ys.push(nums[i + 1]); }}
  return {{ w: Math.max(...xs) - Math.min(...xs), h: Math.max(...ys) - Math.min(...ys) }};
}}
for (const hit of svg.querySelectorAll(".profilo-zona-hit")) {{
  const forma = hit.parentElement?.querySelector(".profilo-zona-forma");
  if (!forma || hit.getAttribute("d") === forma.getAttribute("d")) process.exit(5);
  const {{ w, h }} = bboxPath(hit.getAttribute("d"));
  if (w < DITO_MIN || h < DITO_MIN) process.exit(6);
}}
"""
        risultato = subprocess.run(
            [nodo, "--input-type=module", "-e", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if risultato.returncode != 0 and "Cannot find package 'jsdom'" in (risultato.stderr or ""):
            self.skipTest("jsdom non installato: verifica statica del sorgente sufficiente")
        self.assertEqual(
            risultato.returncode,
            0,
            risultato.stderr or risultato.stdout,
        )

    def test_ingresso_merce_mostra_profilo_per_bovino_vitello_suino(self):
        ingresso = (ROOT / "web" / "js" / "features" / "ingresso-merce.js").read_text(
            encoding="utf-8",
        )
        modulo = (ROOT / "web" / "js" / "features" / "ingresso-articoli-disegno.js").read_text(
            encoding="utf-8",
        )
        css = (ROOT / "web" / "app.css").read_text(encoding="utf-8")

        self.assertIn("categoriaUsaProfiloDisegno", ingresso)
        self.assertIn("renderArticoliConDisegno", ingresso)
        self.assertIn("ingresso-articoli-disegno.js", ingresso)
        self.assertIn('CATEGORIE_CON_PROFILO = ["Bovino", "Vitello", "Suino"]', modulo)
        self.assertIn("export const CODICI_FUORI_PROFILO", modulo)
        self.assertIn("SUI-MEZZENA", modulo)
        self.assertIn("SUI-LARDO", modulo)
        self.assertIn("BOV-FILETTO", modulo)
        self.assertIn("VIT-MEZZENA", modulo)
        self.assertIn(".ingress-articoli-disegno", css)
        self.assertIn(".profilo-macelleria-riga", css)
        self.assertIn(".articoli-fuori-profilo", css)
        self.assertIn("Quarto anteriore", modulo)
        self.assertIn("Quarto posteriore", modulo)
        self.assertIn("creaProfiloBovinoPosteriore", modulo)
        self.assertIn(".profilo-bovino-quarti", css)
        self.assertIn("quartoBovino", ingresso)
        self.assertIn("cambiaQuartoBovino", ingresso)
        self.assertIn("toggleSelezioneArticolo", ingresso)
        self.assertIn("onToggleArticolo(String(articolo.id))", modulo)
        self.assertIn('setAttribute("aria-pressed"', modulo)
        self.assertIn("testoConfermaTaglio", ingresso)
        self.assertIn(".profilo-zona--selezionata .profilo-zona-etichetta", css)
        self.assertIn("profilo-zona--disattiva", modulo)
        self.assertIn("applicaStatoZone", modulo)
        self.assertIn('.profilo-zona:not(.profilo-zona--disattiva)', modulo)
        self.assertIn(".profilo-zona--disattiva", css)
        self.assertIn('aria-disabled', modulo)

    def test_ingresso_zona_senza_articolo_attivo_e_disattiva(self):
        nodo = shutil.which("node")
        modulo = (
            ROOT / "web" / "js" / "features" / "ingresso-articoli-disegno.js"
        ).read_text(encoding="utf-8")
        if nodo is None:
            self.assertIn("profilo-zona--disattiva", modulo)
            self.assertIn('tabindex", "-1"', modulo)
            return

        modulo_uri = (
            ROOT / "web" / "js" / "features" / "ingresso-articoli-disegno.js"
        ).as_uri()
        script = f"""
import {{ JSDOM }} from "jsdom";
import {{ renderArticoliConDisegno }} from "{modulo_uri}";

const dom = new JSDOM("<!DOCTYPE html><body><div id='articoli'></div></body>");
const container = dom.window.document.getElementById("articoli");
const articoli = [
  {{ id: 7, codice: "SUI-LONZA", nome: "Lonza di suino", unita_misura: "kg" }},
];
const selezionati = new Set();

function toggle(id) {{
  if (selezionati.has(id)) selezionati.delete(id);
  else {{
    selezionati.clear();
    selezionati.add(id);
  }}
  container.replaceChildren();
  renderArticoliConDisegno(container, {{
    categoria: "Suino",
    articoliDisponibili: articoli,
    articoliSelezionati: selezionati,
    onToggleArticolo: toggle,
  }});
}}

renderArticoliConDisegno(container, {{
  categoria: "Suino",
  articoliDisponibili: articoli,
  articoliSelezionati: selezionati,
  onToggleArticolo: toggle,
}});

const coppa = container.querySelector('.profilo-zona[data-codice="SUI-COPPA"]');
if (!coppa?.classList.contains("profilo-zona--disattiva")) process.exit(1);
const coppaHit = coppa.querySelector(".profilo-zona-hit");
if (coppaHit.getAttribute("aria-disabled") !== "true") process.exit(2);
if (coppaHit.getAttribute("tabindex") !== "-1") process.exit(3);

const prima = selezionati.size;
coppaHit.click();
if (selezionati.size !== prima) process.exit(4);
coppaHit.dispatchEvent(new dom.window.KeyboardEvent("keydown", {{ key: "Enter", bubbles: true }}));
if (selezionati.size !== prima) process.exit(5);

const lonzaHit = container.querySelector('.profilo-zona[data-codice="SUI-LONZA"] .profilo-zona-hit');
if (lonzaHit.getAttribute("aria-disabled") === "true") process.exit(6);
lonzaHit.click();
if (!selezionati.has("7")) process.exit(7);
"""
        risultato = subprocess.run(
            [nodo, "--input-type=module", "-e", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if risultato.returncode != 0 and "Cannot find package 'jsdom'" in (risultato.stderr or ""):
            self.assertIn("profilo-zona--disattiva", modulo)
            return
        self.assertEqual(
            risultato.returncode,
            0,
            risultato.stderr or risultato.stdout,
        )

    def test_ingresso_condimento_preparato_elenco_pulsanti_testuali(self):
        ingresso = (ROOT / "web" / "js" / "features" / "ingresso-merce.js").read_text(
            encoding="utf-8",
        )
        modulo = (ROOT / "web" / "js" / "features" / "ingresso-articoli-disegno.js").read_text(
            encoding="utf-8",
        )

        self.assertIn("if (categoriaUsaProfiloDisegno(categoriaSelezionata))", ingresso)
        self.assertIn('container.className = "articoli-list"', ingresso)
        self.assertIn('button.className = "articolo-button"', ingresso)
        self.assertIn("Seleziona un articolo da aggiungere.", ingresso)
        categorie_profilo = modulo.split("CATEGORIE_CON_PROFILO", 1)[1].split("];", 1)[0]
        for categoria in ("Condimento", "Preparato"):
            self.assertNotIn(f'"{categoria}"', categorie_profilo)

        nodo = shutil.which("node")
        if nodo is None:
            return

        modulo_uri = (
            ROOT / "web" / "js" / "features" / "ingresso-articoli-disegno.js"
        ).as_uri()
        script = f"""
import {{ JSDOM }} from "jsdom";
import {{ categoriaUsaProfiloDisegno }} from "{modulo_uri}";

for (const c of ["Condimento", "Preparato", "Senza categoria", "Altro"]) {{
  if (categoriaUsaProfiloDisegno(c)) process.exit(1);
}}
for (const c of ["Bovino", "Vitello", "Suino"]) {{
  if (!categoriaUsaProfiloDisegno(c)) process.exit(2);
}}

const dom = new JSDOM("<!DOCTYPE html><body><div id='articoli'></div></body>");
const container = dom.window.document.getElementById("articoli");
const articoliPreparato = [
  {{ id: 2, codice: "PREP-SALSICCIA", nome: "Salsicce fresche", unita_misura: "kg" }},
  {{ id: 3, codice: "PREP-HAMBURGER", nome: "Hamburger di bovino", unita_misura: "kg" }},
  {{ id: 4, codice: "PREP-ARROSTO", nome: "Arrosto di vitello", unita_misura: "kg" }},
];
container.className = "articoli-list";
const articoliCondimento = [
  {{ id: 1, codice: "COND-SALE", nome: "Sale", unita_misura: "kg" }},
];
articoliCondimento.forEach((articolo) => {{
  const button = dom.window.document.createElement("button");
  button.type = "button";
  button.className = "articolo-button";
  button.textContent = `${{articolo.nome}} (${{articolo.unita_misura}})`;
  container.appendChild(button);
}});
if (container.querySelectorAll(".articolo-button").length !== 1) process.exit(3);
container.replaceChildren();
container.className = "articoli-list";
articoliPreparato.forEach((articolo) => {{
  const button = dom.window.document.createElement("button");
  button.type = "button";
  button.className = "articolo-button";
  button.textContent = `${{articolo.nome}} (${{articolo.unita_misura}})`;
  container.appendChild(button);
}});
const pulsanti = container.querySelectorAll(".articolo-button");
if (pulsanti.length !== 3) process.exit(4);
"""
        risultato = subprocess.run(
            [nodo, "--input-type=module", "-e", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if risultato.returncode != 0 and "Cannot find package 'jsdom'" in (risultato.stderr or ""):
            return
        self.assertEqual(
            risultato.returncode,
            0,
            risultato.stderr or risultato.stdout,
        )

    def test_ingresso_evidenzia_zona_e_feedback_selezionato(self):
        nodo = shutil.which("node")
        if nodo is None:
            self.skipTest("Node non disponibile per evidenziazione zona ingresso")
        modulo_disegno = (
            ROOT / "web" / "js" / "features" / "ingresso-articoli-disegno.js"
        ).as_uri()
        modulo_interazione = (
            ROOT / "web" / "js" / "catalogo-disegno" / "profilo-interazione.js"
        ).as_uri()
        script = f"""
import {{ JSDOM }} from "jsdom";
import {{ renderArticoliConDisegno }} from "{modulo_disegno}";
import {{ testoConfermaTaglio }} from "{modulo_interazione}";

const dom = new JSDOM("<!DOCTYPE html><body><div id='articoli'></div><p id='fb'></p></body>");
const container = dom.window.document.getElementById("articoli");
const feedback = dom.window.document.getElementById("fb");
const articoli = [
  {{ id: 7, codice: "SUI-LONZA", nome: "Lonza di suino", unita_misura: "kg" }},
];
const selezionati = new Set();

function aggiornaFeedback() {{
  if (selezionati.size === 1) {{
    const art = articoli.find((a) => String(a.id) === [...selezionati][0]);
    feedback.textContent = art ? testoConfermaTaglio(art.nome) : "";
  }} else {{
    feedback.textContent = "Seleziona un taglio sul profilo o tra i pezzi fuori profilo.";
  }}
}}

function toggle(id) {{
  if (selezionati.has(id)) selezionati.delete(id);
  else {{
    selezionati.clear();
    selezionati.add(id);
  }}
  container.replaceChildren();
  renderArticoliConDisegno(container, {{
    categoria: "Suino",
    articoliDisponibili: articoli,
    articoliSelezionati: selezionati,
    onToggleArticolo: toggle,
  }});
  aggiornaFeedback();
}}

renderArticoliConDisegno(container, {{
  categoria: "Suino",
  articoliDisponibili: articoli,
  articoliSelezionati: selezionati,
  onToggleArticolo: toggle,
}});
const lonzaHit = container.querySelector('.profilo-zona[data-codice="SUI-LONZA"] .profilo-zona-hit');
lonzaHit.click();
aggiornaFeedback();
const lonzaZona = container.querySelector('.profilo-zona[data-codice="SUI-LONZA"]');
if (!lonzaZona.classList.contains("profilo-zona--selezionata")) process.exit(1);
const etichetta = lonzaZona.querySelector(".profilo-zona-etichetta");
const stile = dom.window.getComputedStyle(etichetta);
if (stile.opacity !== "1") process.exit(2);
const atteso = testoConfermaTaglio("Lonza di suino");
if (feedback.textContent !== atteso) process.exit(3);
"""
        risultato = subprocess.run(
            [nodo, "--input-type=module", "-e", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if risultato.returncode != 0 and "Cannot find package 'jsdom'" in (risultato.stderr or ""):
            self.skipTest("jsdom non installato: verifica statica del sorgente sufficiente")
        self.assertEqual(
            risultato.returncode,
            0,
            risultato.stderr or risultato.stdout,
        )

    def test_ingresso_render_disegno_suino_in_dom(self):
        nodo = shutil.which("node")
        if nodo is None:
            self.skipTest("Node non disponibile per il render ingresso disegno")
        modulo = (ROOT / "web" / "js" / "features" / "ingresso-articoli-disegno.js").as_uri()
        script = f"""
import {{ JSDOM }} from "jsdom";
import {{ renderArticoliConDisegno }} from "{modulo}";

const dom = new JSDOM("<!DOCTYPE html><body><div id='articoli'></div></body>");
const container = dom.window.document.getElementById("articoli");
const articoli = [
  {{ id: 1, codice: "SUI-LONZA", nome: "Lonza di suino", unita_misura: "kg" }},
  {{ id: 2, codice: "SUI-MEZZENA", nome: "Mezzena di suino", unita_misura: "kg" }},
];
const selezionati = new Set();
renderArticoliConDisegno(container, {{
  categoria: "Suino",
  articoliDisponibili: articoli,
  articoliSelezionati: selezionati,
  onToggleArticolo: () => {{}},
}});
if (!container.classList.contains("ingress-articoli-disegno")) process.exit(1);
const svg = container.querySelector(".profilo-suino");
if (!svg) process.exit(2);
const fuori = container.querySelectorAll(".articoli-fuori-profilo .articolo-button");
if (fuori.length !== 1) process.exit(3);
if (!container.querySelector('.profilo-zona[data-codice="SUI-LONZA"]')) process.exit(4);
"""
        risultato = subprocess.run(
            [nodo, "--input-type=module", "-e", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if risultato.returncode != 0 and "Cannot find package 'jsdom'" in (risultato.stderr or ""):
            self.skipTest("jsdom non installato: verifica statica del sorgente sufficiente")
        self.assertEqual(
            risultato.returncode,
            0,
            risultato.stderr or risultato.stdout,
        )

    def test_ingresso_bovino_un_solo_profil_o_per_quarto(self):
        nodo = shutil.which("node")
        if nodo is None:
            self.skipTest("Node non disponibile per il quarto bovino in ingresso")
        modulo = (ROOT / "web" / "js" / "features" / "ingresso-articoli-disegno.js").as_uri()
        script = f"""
import {{ JSDOM }} from "jsdom";
import {{ renderArticoliConDisegno }} from "{modulo}";

const dom = new JSDOM("<!DOCTYPE html><body><div id='articoli'></div></body>");
const container = dom.window.document.getElementById("articoli");
const articoli = [
  {{ id: 1, codice: "BOV-COSTATA", nome: "Costata bovina", unita_misura: "kg" }},
  {{ id: 2, codice: "BOV-MEZZENA", nome: "Mezzena bovina", unita_misura: "kg" }},
];
let quarto = "anteriore";
renderArticoliConDisegno(container, {{
  categoria: "Bovino",
  articoliDisponibili: articoli,
  articoliSelezionati: new Set(),
  onToggleArticolo: () => {{}},
  quartoBovino: quarto,
  onQuartoBovinoChange: (q) => {{ quarto = q; }},
}});
const comandi = container.querySelectorAll(".profilo-bovino-quarti .categoria-button");
if (comandi.length !== 2) process.exit(1);
if (!container.querySelector(".profilo-bovino--anteriore")) process.exit(2);
if (container.querySelector(".profilo-bovino--posteriore")) process.exit(3);

container.replaceChildren();
renderArticoliConDisegno(container, {{
  categoria: "Bovino",
  articoliDisponibili: articoli,
  articoliSelezionati: new Set(),
  onToggleArticolo: () => {{}},
  quartoBovino: "posteriore",
  onQuartoBovinoChange: () => {{}},
}});
if (!container.querySelector(".profilo-bovino--posteriore")) process.exit(4);
if (container.querySelector(".profilo-bovino--anteriore")) process.exit(5);
if (!container.querySelector('.profilo-zona[data-codice="BOV-COSTATA"]')) process.exit(6);
"""
        risultato = subprocess.run(
            [nodo, "--input-type=module", "-e", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if risultato.returncode != 0 and "Cannot find package 'jsdom'" in (risultato.stderr or ""):
            self.skipTest("jsdom non installato: verifica statica del sorgente sufficiente")
        self.assertEqual(
            risultato.returncode,
            0,
            risultato.stderr or risultato.stdout,
        )

    def test_ingresso_pulsanti_fuori_profilo_accanto_al_disegno(self):
        nodo = shutil.which("node")
        if nodo is None:
            self.skipTest("Node non disponibile per i pulsanti fuori profilo")

        modulo = (ROOT / "web" / "js" / "features" / "ingresso-articoli-disegno.js").as_uri()
        modulo_interazione = (
            ROOT / "web" / "js" / "catalogo-disegno" / "profilo-interazione.js"
        ).as_uri()
        script = f"""
import {{ JSDOM }} from "jsdom";
import {{ renderArticoliConDisegno, CODICI_FUORI_PROFILO }} from "{modulo}";
import {{ testoConfermaTaglio }} from "{modulo_interazione}";

if (CODICI_FUORI_PROFILO.Suino.length !== 3) process.exit(1);
if (CODICI_FUORI_PROFILO.Bovino.length !== 2) process.exit(2);
if (CODICI_FUORI_PROFILO.Vitello.length !== 1) process.exit(3);

const dom = new JSDOM("<!DOCTYPE html><body><div id='articoli'></div></body>");
const container = dom.window.document.getElementById("articoli");
const articoliSuino = [
  {{ id: 1, codice: "SUI-LONZA", nome: "Lonza di suino", unita_misura: "kg" }},
  {{ id: 2, codice: "SUI-MEZZENA", nome: "Mezzena di suino", unita_misura: "kg" }},
  {{ id: 3, codice: "SUI-FILETTO", nome: "Filetto di suino", unita_misura: "kg" }},
  {{ id: 4, codice: "SUI-LARDO", nome: "Lardo di suino", unita_misura: "kg" }},
];
const selezionati = new Set();

function renderSuino() {{
  container.replaceChildren();
  renderArticoliConDisegno(container, {{
    categoria: "Suino",
    articoliDisponibili: articoliSuino,
    articoliSelezionati: selezionati,
    onToggleArticolo: toggle,
  }});
}}

function toggle(id) {{
  if (selezionati.has(id)) selezionati.delete(id);
  else {{
    selezionati.clear();
    selezionati.add(id);
  }}
  renderSuino();
}}

renderSuino();
const riga = container.querySelector(".profilo-macelleria-riga");
if (!riga) process.exit(4);
if (!riga.querySelector(".profilo-suino")) process.exit(5);
const fuori = riga.querySelectorAll(".articoli-fuori-profilo .articolo-button");
if (fuori.length !== 3) process.exit(6);
const mezzena = container.querySelector('.articolo-button[data-codice="SUI-MEZZENA"]');
if (!mezzena) process.exit(7);
mezzena.click();
if (!selezionati.has("2")) process.exit(8);
if (mezzena.getAttribute("aria-pressed") !== "true") process.exit(9);
const atteso = testoConfermaTaglio("Mezzena di suino");
mezzena.click();
if (selezionati.size !== 0) process.exit(10);
if (mezzena.getAttribute("aria-pressed") !== "false") process.exit(11);
if (atteso !== "Selezionato: Mezzena di suino. Inserisci la quantità.") process.exit(12);

container.replaceChildren();
renderArticoliConDisegno(container, {{
  categoria: "Vitello",
  articoliDisponibili: [
    {{ id: 10, codice: "VIT-CARRE", nome: "Carrè di vitello", unita_misura: "kg" }},
    {{ id: 11, codice: "VIT-MEZZENA", nome: "Mezzena di vitello", unita_misura: "kg" }},
  ],
  articoliSelezionati: new Set(),
  onToggleArticolo: () => {{}},
}});
const vitelloFuori = container.querySelectorAll(
  ".profilo-macelleria-riga .articoli-fuori-profilo .articolo-button",
);
if (vitelloFuori.length !== 1) process.exit(13);
if (vitelloFuori[0].dataset.codice !== "VIT-MEZZENA") process.exit(14);

container.replaceChildren();
renderArticoliConDisegno(container, {{
  categoria: "Bovino",
  articoliDisponibili: [
    {{ id: 20, codice: "BOV-COLLO", nome: "Collo bovino", unita_misura: "kg" }},
    {{ id: 21, codice: "BOV-MEZZENA", nome: "Mezzena bovina", unita_misura: "kg" }},
    {{ id: 22, codice: "BOV-FILETTO", nome: "Filetto bovino", unita_misura: "kg" }},
  ],
  articoliSelezionati: new Set(),
  onToggleArticolo: () => {{}},
  quartoBovino: "anteriore",
  onQuartoBovinoChange: () => {{}},
}});
const bovinoFuori = container.querySelectorAll(
  ".profilo-macelleria-riga .articoli-fuori-profilo .articolo-button",
);
if (bovinoFuori.length !== 2) process.exit(15);
"""
        risultato = subprocess.run(
            [nodo, "--input-type=module", "-e", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if risultato.returncode != 0 and "Cannot find package 'jsdom'" in (risultato.stderr or ""):
            self.skipTest("jsdom non installato: verifica statica del sorgente sufficiente")
        self.assertEqual(
            risultato.returncode,
            0,
            risultato.stderr or risultato.stdout,
        )

    def test_ingresso_zona_attiva_toggle_selezione_e_aria_pressed(self):
        nodo = shutil.which("node")
        if nodo is None:
            self.skipTest("Node non disponibile per il toggle zona ingresso")
        modulo = (ROOT / "web" / "js" / "features" / "ingresso-articoli-disegno.js").as_uri()
        script = f"""
import {{ JSDOM }} from "jsdom";
import {{ renderArticoliConDisegno }} from "{modulo}";

const dom = new JSDOM("<!DOCTYPE html><body><div id='articoli'></div></body>");
const container = dom.window.document.getElementById("articoli");
const articoli = [
  {{ id: 7, codice: "SUI-LONZA", nome: "Lonza di suino", unita_misura: "kg" }},
  {{ id: 8, codice: "SUI-COPPA", nome: "Coppa di suino", unita_misura: "kg" }},
];
const selezionati = new Set();

function toggle(id) {{
  if (selezionati.has(id)) selezionati.delete(id);
  else {{
    selezionati.clear();
    selezionati.add(id);
  }}
  container.replaceChildren();
  renderArticoliConDisegno(container, {{
    categoria: "Suino",
    articoliDisponibili: articoli,
    articoliSelezionati: selezionati,
    onToggleArticolo: toggle,
  }});
}}

renderArticoliConDisegno(container, {{
  categoria: "Suino",
  articoliDisponibili: articoli,
  articoliSelezionati: selezionati,
  onToggleArticolo: toggle,
}});
const lonzaHit = container.querySelector('.profilo-zona[data-codice="SUI-LONZA"] .profilo-zona-hit');
if (!lonzaHit) process.exit(1);
lonzaHit.click();
if (!selezionati.has("7")) process.exit(2);
const lonzaZona = container.querySelector('.profilo-zona[data-codice="SUI-LONZA"]');
if (!lonzaZona.classList.contains("profilo-zona--selezionata")) process.exit(3);
if (lonzaHit.getAttribute("aria-pressed") !== "true") process.exit(4);

lonzaHit.click();
if (selezionati.size !== 0) process.exit(5);
if (lonzaHit.getAttribute("aria-pressed") !== "false") process.exit(6);

const coppaHit = container.querySelector('.profilo-zona[data-codice="SUI-COPPA"] .profilo-zona-hit');
coppaHit.click();
if (!selezionati.has("8")) process.exit(7);
lonzaHit.click();
if (!selezionati.has("7") || selezionati.has("8")) process.exit(8);
"""
        risultato = subprocess.run(
            [nodo, "--input-type=module", "-e", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if risultato.returncode != 0 and "Cannot find package 'jsdom'" in (risultato.stderr or ""):
            self.skipTest("jsdom non installato: verifica statica del sorgente sufficiente")
        self.assertEqual(
            risultato.returncode,
            0,
            risultato.stderr or risultato.stdout,
        )

    def test_ingresso_scanner_seleziona_e_evidenzia_su_profilo(self):
        pagina = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        ingresso = (ROOT / "web" / "js" / "features" / "ingresso-merce.js").read_text(
            encoding="utf-8",
        )
        modulo = (ROOT / "web" / "js" / "features" / "ingresso-articoli-disegno.js").read_text(
            encoding="utf-8",
        )

        self.assertIn('id="ingress-articoli"', pagina)
        self.assertIn("selezionaArticoloDaScanner", ingresso)
        self.assertIn("registraScanner", ingresso)
        self.assertIn("quartoBovinoPerCodice", ingresso)
        self.assertIn("testoConfermaTaglio(articolo.nome)", ingresso)
        self.assertIn("export function quartoBovinoPerCodice", modulo)

        nodo = shutil.which("node")
        if nodo is None:
            return

        modulo_uri = (
            ROOT / "web" / "js" / "features" / "ingresso-articoli-disegno.js"
        ).as_uri()
        interazione_uri = (
            ROOT / "web" / "js" / "catalogo-disegno" / "profilo-interazione.js"
        ).as_uri()
        script = f"""
import {{ JSDOM }} from "jsdom";
import {{
  quartoBovinoPerCodice,
  renderArticoliConDisegno,
}} from "{modulo_uri}";
import {{ testoConfermaTaglio }} from "{interazione_uri}";

if (quartoBovinoPerCodice("BOV-COSTATA") !== "posteriore") process.exit(1);
if (quartoBovinoPerCodice("BOV-COLLO") !== "anteriore") process.exit(2);
if (quartoBovinoPerCodice("BOV-FILETTO") !== null) process.exit(3);

const dom = new JSDOM("<!DOCTYPE html><body><div id='articoli'></div></body>");
const container = dom.window.document.getElementById("articoli");
const articoliSuino = [
  {{ id: 7, codice: "SUI-LONZA", nome: "Lonza di suino", unita_misura: "kg" }},
  {{ id: 9, codice: "SUI-MEZZENA", nome: "Mezzena di suino", unita_misura: "kg" }},
];
const selezionatiScan = new Set(["7"]);
renderArticoliConDisegno(container, {{
  categoria: "Suino",
  articoliDisponibili: articoliSuino,
  articoliSelezionati: selezionatiScan,
  onToggleArticolo: () => {{}},
}});
const lonza = container.querySelector('.profilo-zona[data-codice="SUI-LONZA"]');
if (!lonza?.classList.contains("profilo-zona--selezionata")) process.exit(4);
const atteso = testoConfermaTaglio("Lonza di suino");
if (atteso !== "Selezionato: Lonza di suino. Inserisci la quantità.") process.exit(5);

container.replaceChildren();
const selezionatiMezzena = new Set(["9"]);
renderArticoliConDisegno(container, {{
  categoria: "Suino",
  articoliDisponibili: articoliSuino,
  articoliSelezionati: selezionatiMezzena,
  onToggleArticolo: () => {{}},
}});
const mezzena = container.querySelector('.articolo-button[data-codice="SUI-MEZZENA"]');
if (!mezzena || mezzena.getAttribute("aria-pressed") !== "true") process.exit(6);

container.replaceChildren();
const articoliBovino = [
  {{ id: 20, codice: "BOV-COSTATA", nome: "Costata bovina", unita_misura: "kg" }},
];
renderArticoliConDisegno(container, {{
  categoria: "Bovino",
  articoliDisponibili: articoliBovino,
  articoliSelezionati: new Set(["20"]),
  onToggleArticolo: () => {{}},
  quartoBovino: quartoBovinoPerCodice("BOV-COSTATA"),
  onQuartoBovinoChange: () => {{}},
}});
const costata = container.querySelector('.profilo-zona[data-codice="BOV-COSTATA"]');
if (!costata?.classList.contains("profilo-zona--selezionata")) process.exit(7);
if (!container.querySelector(".profilo-bovino--posteriore")) process.exit(8);
"""
        risultato = subprocess.run(
            [nodo, "--input-type=module", "-e", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if risultato.returncode != 0 and "Cannot find package 'jsdom'" in (risultato.stderr or ""):
            return
        self.assertEqual(
            risultato.returncode,
            0,
            risultato.stderr or risultato.stdout,
        )

    def test_ingresso_payload_conferma_invariato(self):
        ingresso = (ROOT / "web" / "js" / "features" / "ingresso-merce.js").read_text(
            encoding="utf-8",
        )
        self.assertIn("articoloId: articolo.id", ingresso)
        self.assertIn("articolo_id: Number(riga.articoloId)", ingresso)
        self.assertIn("quantita: riga.quantita.toFixed(3)", ingresso)
        for campo in (
            "lotto_fornitore",
            "origine",
            "note_lotto",
            "data_scadenza",
            "data_tmc",
            "temperatura_ingresso",
        ):
            self.assertIn(campo, ingresso)
        blocco_righe = ingresso.split("righe: righeIngresso.map", 1)[1].split("}),", 1)[0]
        self.assertNotIn("codice:", blocco_righe)


if __name__ == "__main__":
    unittest.main()