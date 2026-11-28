import os
import re
import shutil
import subprocess
import unittest
import uuid
from datetime import date, timedelta
from decimal import Decimal
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

    def test_verifica_checklist_suino_lonza_riepilogo_da_taglio_su_profilo(self):
        """Checklist §4: Suino → lonza → quantità → riepilogo con «Lonza di suino»."""
        ingresso = (ROOT / "web" / "js" / "features" / "ingresso-merce.js").read_text(
            encoding="utf-8",
        )
        self.assertIn("articolo: articolo.nome", ingresso)
        self.assertIn('name.textContent = riga.articolo', ingresso)

        nodo = shutil.which("node")
        if nodo is None:
            nodo = shutil.which("node", path=(
                "C:/Program Files/nodejs;"
                "C:/Program Files (x86)/nodejs"
            ))
        if nodo is None:
            return

        modulo = (ROOT / "web" / "js" / "features" / "ingresso-articoli-disegno.js").as_uri()
        script = f"""
import {{ JSDOM }} from "jsdom";
import {{ renderArticoliConDisegno }} from "{modulo}";

const html = `
<!DOCTYPE html>
<body>
  <div id="ingress-articoli"></div>
  <div id="ingress-riepilogo-righe"></div>
  <input type="number" id="ingress-quantita" value="2.5" />
</body>`;
const dom = new JSDOM(html);
const {{ document }} = dom.window;

const articoli = [
  {{ id: 7, codice: "SUI-LONZA", nome: "Lonza di suino", categoria: "Suino", unita_misura: "kg", attivo: true }},
  {{ id: 8, codice: "SUI-COPPA", nome: "Coppa di suino", categoria: "Suino", unita_misura: "kg", attivo: true }},
];
const selezionati = new Set();
const container = document.getElementById("ingress-articoli");

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

const quantita = Number(document.getElementById("ingress-quantita").value);
const articolo = articoli.find((a) => String(a.id) === "7");
const righeIngresso = [{{
  id: 1,
  articoloId: articolo.id,
  articolo: articolo.nome,
  categoria: articolo.categoria,
  unitaMisura: articolo.unita_misura,
  quantita,
}}];

const riepilogo = document.getElementById("ingress-riepilogo-righe");
riepilogo.replaceChildren();
righeIngresso.forEach((riga) => {{
  const item = document.createElement("div");
  item.className = "ingresso-line";
  const name = document.createElement("strong");
  name.textContent = riga.articolo;
  item.appendChild(name);
  riepilogo.appendChild(item);
}});

const testo = riepilogo.querySelector("strong")?.textContent || "";
if (testo !== "Lonza di suino") process.exit(3);
if (righeIngresso[0].articoloId !== 7) process.exit(4);
"""
        risultato = subprocess.run(
            [nodo, "--input-type=module", "-e", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if risultato.returncode != 0 and "Cannot find package 'jsdom'" in (risultato.stderr or ""):
            self.skipTest("jsdom non installato: impossibile simulare il riepilogo lonza")
        self.assertEqual(
            risultato.returncode,
            0,
            risultato.stderr or risultato.stdout,
        )

    def test_verifica_checklist_vitello_carre_e_bovino_quarti_su_profilo(self):
        """Checklist §4: Vitello carrè e bovino anteriore/posteriore → riepilogo."""
        ingresso = (ROOT / "web" / "js" / "features" / "ingresso-merce.js").read_text(
            encoding="utf-8",
        )
        self.assertIn("articolo: articolo.nome", ingresso)
        vitello = (ROOT / "web" / "js" / "catalogo-disegno" / "profilo-vitello.js").read_text(
            encoding="utf-8",
        )
        bovino = (ROOT / "web" / "js" / "catalogo-disegno" / "profilo-bovino.js").read_text(
            encoding="utf-8",
        )
        self.assertIn('"VIT-CARRE"', vitello)
        self.assertIn("Carrè di vitello", vitello)
        self.assertIn('"BOV-PETTO"', bovino)
        self.assertIn('"BOV-COSTATA"', bovino)

        nodo = _nodo_js_disponibile()
        if nodo is None:
            return

        modulo = (ROOT / "web" / "js" / "features" / "ingresso-articoli-disegno.js").as_uri()
        script = f"""
import {{ JSDOM }} from "jsdom";
import {{ renderArticoliConDisegno }} from "{modulo}";

const dom = new JSDOM("<!DOCTYPE html><body><div id='articoli'></div></body>");
const container = dom.window.document.getElementById("articoli");
const selezionati = new Set();

function provaVitello() {{
  const articoli = [
    {{ id: 41, codice: "VIT-CARRE", nome: "Carrè di vitello", unita_misura: "kg" }},
  ];
  function toggle(id) {{
    selezionati.clear();
    selezionati.add(id);
    container.replaceChildren();
    renderArticoliConDisegno(container, {{
      categoria: "Vitello",
      articoliDisponibili: articoli,
      articoliSelezionati: selezionati,
      onToggleArticolo: toggle,
    }});
  }}
  renderArticoliConDisegno(container, {{
    categoria: "Vitello",
    articoliDisponibili: articoli,
    articoliSelezionati: selezionati,
    onToggleArticolo: toggle,
  }});
  const hit = container.querySelector('.profilo-zona[data-codice="VIT-CARRE"] .profilo-zona-hit');
  if (!hit) return 1;
  hit.click();
  if (!selezionati.has("41")) return 2;
  if (articoli[0].nome !== "Carrè di vitello") return 3;
  return 0;
}}

function provaBovino(codice, id, quarto) {{
  selezionati.clear();
  container.replaceChildren();
  const articoli = [{{ id, codice, nome: codice === "BOV-PETTO" ? "Petto bovino" : "Costata bovina", unita_misura: "kg" }}];
  function toggle(rid) {{
    selezionati.clear();
    selezionati.add(rid);
    container.replaceChildren();
    renderArticoliConDisegno(container, {{
      categoria: "Bovino",
      articoliDisponibili: articoli,
      articoliSelezionati: selezionati,
      onToggleArticolo: toggle,
      quartoBovino: quarto,
      onQuartoBovinoChange: () => {{}},
    }});
  }}
  renderArticoliConDisegno(container, {{
    categoria: "Bovino",
    articoliDisponibili: articoli,
    articoliSelezionati: selezionati,
    onToggleArticolo: toggle,
    quartoBovino: quarto,
    onQuartoBovinoChange: () => {{}},
  }});
  const hit = container.querySelector(`.profilo-zona[data-codice="${{codice}}"] .profilo-zona-hit`);
  if (!hit) return 10;
  hit.click();
  if (!selezionati.has(String(id))) return 11;
  return 0;
}}

let err = provaVitello();
if (err) process.exit(err);
err = provaBovino("BOV-PETTO", 21, "anteriore");
if (err) process.exit(err);
err = provaBovino("BOV-COSTATA", 22, "posteriore");
if (err) process.exit(err + 20);
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

    def test_verifica_checklist_pulsanti_fuori_profilo_riepilogo(self):
        """Checklist §4: mezzena/filetto bovino, filetto e lardo suino → riepilogo."""
        ingresso = (ROOT / "web" / "js" / "features" / "ingresso-merce.js").read_text(
            encoding="utf-8",
        )
        self.assertIn("articolo: articolo.nome", ingresso)
        self.assertIn('name.textContent = riga.articolo', ingresso)

        nodo = _nodo_js_disponibile()
        if nodo is None:
            return

        modulo = (ROOT / "web" / "js" / "features" / "ingresso-articoli-disegno.js").as_uri()
        script = f"""
import {{ JSDOM }} from "jsdom";
import {{ renderArticoliConDisegno }} from "{modulo}";

const html = `
<!DOCTYPE html>
<body>
  <div id="ingress-articoli"></div>
  <div id="ingress-riepilogo-righe"></div>
</body>`;
const dom = new JSDOM(html);
const {{ document }} = dom.window;

function simulaRiepilogo(righeIngresso) {{
  const riepilogo = document.getElementById("ingress-riepilogo-righe");
  riepilogo.replaceChildren();
  righeIngresso.forEach((riga) => {{
    const item = document.createElement("div");
    item.className = "ingresso-line";
    const name = document.createElement("strong");
    name.textContent = riga.articolo;
    item.appendChild(name);
    riepilogo.appendChild(item);
  }});
  return riepilogo.querySelector("strong")?.textContent || "";
}}

function provaSuino(codice, id, nomeAtteso) {{
  const container = document.getElementById("ingress-articoli");
  const articoli = [
    {{ id, codice, nome: nomeAtteso, categoria: "Suino", unita_misura: "kg", attivo: true }},
    {{ id: 99, codice: "SUI-LONZA", nome: "Lonza di suino", categoria: "Suino", unita_misura: "kg", attivo: true }},
  ];
  const selezionati = new Set();
  function toggle(rid) {{
    if (selezionati.has(rid)) selezionati.delete(rid);
    else {{
      selezionati.clear();
      selezionati.add(rid);
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
  const btn = container.querySelector(`.articolo-button[data-codice="${{codice}}"]`);
  if (!btn) return 1;
  btn.click();
  if (!selezionati.has(String(id))) return 2;
  const articolo = articoli.find((a) => String(a.id) === String(id));
  const testo = simulaRiepilogo([{{
    id: 1,
    articoloId: articolo.id,
    articolo: articolo.nome,
    quantita: 1,
    unitaMisura: "kg",
  }}]);
  if (testo !== nomeAtteso) return 3;
  return 0;
}}

function provaBovino(codice, id, nomeAtteso) {{
  const container = document.getElementById("ingress-articoli");
  const articoli = [
    {{ id, codice, nome: nomeAtteso, categoria: "Bovino", unita_misura: "kg", attivo: true }},
    {{ id: 99, codice: "BOV-COLLO", nome: "Collo bovino", categoria: "Bovino", unita_misura: "kg", attivo: true }},
  ];
  const selezionati = new Set();
  function toggle(rid) {{
    if (selezionati.has(rid)) selezionati.delete(rid);
    else {{
      selezionati.clear();
      selezionati.add(rid);
    }}
    container.replaceChildren();
    renderArticoliConDisegno(container, {{
      categoria: "Bovino",
      articoliDisponibili: articoli,
      articoliSelezionati: selezionati,
      onToggleArticolo: toggle,
      quartoBovino: "anteriore",
      onQuartoBovinoChange: () => {{}},
    }});
  }}
  renderArticoliConDisegno(container, {{
    categoria: "Bovino",
    articoliDisponibili: articoli,
    articoliSelezionati: selezionati,
    onToggleArticolo: toggle,
    quartoBovino: "anteriore",
    onQuartoBovinoChange: () => {{}},
  }});
  const btn = container.querySelector(`.articolo-button[data-codice="${{codice}}"]`);
  if (!btn) return 10;
  btn.click();
  if (!selezionati.has(String(id))) return 11;
  const articolo = articoli.find((a) => String(a.id) === String(id));
  const testo = simulaRiepilogo([{{
    id: 1,
    articoloId: articolo.id,
    articolo: articolo.nome,
    quantita: 2.5,
    unitaMisura: "kg",
  }}]);
  if (testo !== nomeAtteso) return 12;
  return 0;
}}

const casi = [
  () => provaBovino("BOV-MEZZENA", 1, "Mezzena bovina"),
  () => provaBovino("BOV-FILETTO", 2, "Filetto bovino"),
  () => provaSuino("SUI-FILETTO", 3, "Filetto di suino"),
  () => provaSuino("SUI-LARDO", 4, "Lardo di suino"),
];
for (let i = 0; i < casi.length; i++) {{
  const err = casi[i]();
  if (err) process.exit(i * 10 + err);
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
            self.skipTest("jsdom non installato: impossibile simulare riepilogo fuori profilo")
        self.assertEqual(
            risultato.returncode,
            0,
            risultato.stderr or risultato.stdout,
        )

    def test_verifica_checklist_zona_spenta_dopo_disattivazione_articolo(self):
        """Checklist §4: disattivazione da Configurazioni → zona spenta, niente righe."""
        ingresso = (ROOT / "web" / "js" / "features" / "ingresso-merce.js").read_text(
            encoding="utf-8",
        )
        self.assertIn("articoli.filter((articolo) => articolo.attivo)", ingresso)
        self.assertIn(
            "articoliAttivi().filter((articolo) =>\n    articoliSelezionati.has(String(articolo.id)))",
            ingresso,
        )

        nodo = _nodo_js_disponibile()
        if nodo is None:
            return

        modulo = (ROOT / "web" / "js" / "features" / "ingresso-articoli-disegno.js").as_uri()
        script = f"""
import {{ JSDOM }} from "jsdom";
import {{ renderArticoliConDisegno }} from "{modulo}";

const dom = new JSDOM("<!DOCTYPE html><body><div id='articoli'></div></body>");
const container = dom.window.document.getElementById("articoli");
let catalogo = [
  {{ id: 7, codice: "SUI-LONZA", nome: "Lonza di suino", categoria: "Suino", unita_misura: "kg", attivo: true }},
  {{ id: 8, codice: "SUI-COPPA", nome: "Coppa di suino", categoria: "Suino", unita_misura: "kg", attivo: true }},
];
const selezionati = new Set();

function articoliAttivi() {{
  return catalogo.filter((a) => a.attivo);
}}

function disponibiliSuino() {{
  return articoliAttivi().filter(
    (a) => (a.categoria?.trim() || "Senza categoria") === "Suino",
  );
}}

function renderSuino() {{
  container.replaceChildren();
  renderArticoliConDisegno(container, {{
    categoria: "Suino",
    articoliDisponibili: disponibiliSuino(),
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

function righeAggiungibili() {{
  return articoliAttivi().filter((a) => selezionati.has(String(a.id)));
}}

renderSuino();
const lonzaHit0 = container.querySelector(
  '.profilo-zona[data-codice="SUI-LONZA"] .profilo-zona-hit',
);
if (!lonzaHit0) process.exit(1);
if (lonzaHit0.getAttribute("aria-disabled") === "true") process.exit(2);
lonzaHit0.click();
if (!selezionati.has("7")) process.exit(3);

catalogo = catalogo.map((a) =>
  a.codice === "SUI-LONZA" ? {{ ...a, attivo: false }} : a,
);
renderSuino();

const lonzaZona = container.querySelector('.profilo-zona[data-codice="SUI-LONZA"]');
if (!lonzaZona?.classList.contains("profilo-zona--disattiva")) process.exit(4);
const lonzaHit = lonzaZona.querySelector(".profilo-zona-hit");
if (lonzaHit.getAttribute("aria-disabled") !== "true") process.exit(5);

const primaClick = selezionati.size;
lonzaHit.click();
if (selezionati.size !== primaClick) process.exit(6);
if (righeAggiungibili().length !== 0) process.exit(7);

selezionati.clear();
const coppaHit = container.querySelector(
  '.profilo-zona[data-codice="SUI-COPPA"] .profilo-zona-hit',
);
if (!coppaHit || coppaHit.getAttribute("aria-disabled") === "true") process.exit(8);
coppaHit.click();
if (!selezionati.has("8")) process.exit(9);
if (righeAggiungibili().length !== 1) process.exit(10);
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

    def test_verifica_checklist_condimento_preparato_pulsanti_senza_disegno(self):
        """Checklist §4: Sale e preparati restano elenco testuale, senza profilo."""
        onboarding = (ROOT / "saas" / "services" / "onboarding.py").read_text(
            encoding="utf-8",
        )
        attesi = {
            "COND-SALE": ("Sale", "Condimento"),
            "PREP-SALSICCIA": ("Salsicce fresche", "Preparato"),
            "PREP-HAMBURGER": ("Hamburger di bovino", "Preparato"),
            "PREP-ARROSTO": ("Arrosto di vitello", "Preparato"),
        }
        for codice, (nome, categoria) in attesi.items():
            with self.subTest(codice=codice):
                self.assertRegex(
                    onboarding,
                    rf'\("{re.escape(codice)}", "{re.escape(nome)}", "{re.escape(categoria)}"',
                )

        ingresso = (ROOT / "web" / "js" / "features" / "ingresso-merce.js").read_text(
            encoding="utf-8",
        )
        self.assertIn("categoriaUsaProfiloDisegno(categoriaSelezionata)", ingresso)
        self.assertIn('container.className = "articoli-list"', ingresso)

        nodo = _nodo_js_disponibile()
        if nodo is None:
            return

        modulo = (ROOT / "web" / "js" / "features" / "ingresso-articoli-disegno.js").as_uri()
        script = f"""
import {{ JSDOM }} from "jsdom";
import {{ categoriaUsaProfiloDisegno, renderArticoliConDisegno }} from "{modulo}";

const catalogo = [
  {{ id: 1, codice: "COND-SALE", nome: "Sale", categoria: "Condimento", unita_misura: "kg", attivo: true }},
  {{ id: 2, codice: "PREP-SALSICCIA", nome: "Salsicce fresche", categoria: "Preparato", unita_misura: "kg", attivo: true }},
  {{ id: 3, codice: "PREP-HAMBURGER", nome: "Hamburger di bovino", categoria: "Preparato", unita_misura: "kg", attivo: true }},
  {{ id: 4, codice: "PREP-ARROSTO", nome: "Arrosto di vitello", categoria: "Preparato", unita_misura: "kg", attivo: true }},
  {{ id: 5, codice: "SUI-LONZA", nome: "Lonza di suino", categoria: "Suino", unita_misura: "kg", attivo: true }},
];
const selezionati = new Set();

function renderIngressoLista(container, categoria) {{
  const disponibili = catalogo.filter(
    (a) => a.attivo && (a.categoria?.trim() || "Senza categoria") === categoria,
  );
  container.replaceChildren();
  if (categoriaUsaProfiloDisegno(categoria)) {{
    renderArticoliConDisegno(container, {{
      categoria,
      articoliDisponibili: disponibili,
      articoliSelezionati: selezionati,
      onToggleArticolo: () => {{}},
    }});
    return;
  }}
  container.className = "articoli-list";
  disponibili.forEach((articolo) => {{
    const button = document.createElement("button");
    button.type = "button";
    button.className = "articolo-button";
    button.textContent = `${{articolo.nome}} (${{articolo.unita_misura}})`;
    container.appendChild(button);
  }});
}}

const dom = new JSDOM("<!DOCTYPE html><body><div id='articoli'></div></body>");
const container = dom.window.document.getElementById("articoli");

function verificaCategoria(categoria, codiciAttesi, exitBase) {{
  renderIngressoLista(container, categoria);
  if (container.querySelector(".profilo-macelleria-riga, .profilo-suino, .profilo-bovino, svg.profilo")) {{
    process.exit(exitBase);
  }}
  if (container.className !== "articoli-list") process.exit(exitBase + 1);
  const pulsanti = [...container.querySelectorAll(".articolo-button")];
  if (pulsanti.length !== codiciAttesi.length) process.exit(exitBase + 2);
  const testi = pulsanti.map((b) => b.textContent).sort();
  const attesi = codiciAttesi
    .map((c) => {{
      const a = catalogo.find((x) => x.codice === c);
      return `${{a.nome}} (${{a.unita_misura}})`;
    }})
    .sort();
  if (JSON.stringify(testi) !== JSON.stringify(attesi)) process.exit(exitBase + 3);
}}

verificaCategoria("Condimento", ["COND-SALE"], 10);
verificaCategoria("Preparato", ["PREP-SALSICCIA", "PREP-HAMBURGER", "PREP-ARROSTO"], 20);

renderIngressoLista(container, "Suino");
if (!container.querySelector(".profilo-macelleria-riga, .profilo-suino")) process.exit(30);
"""
        risultato = subprocess.run(
            [nodo, "--input-type=module", "-e", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if risultato.returncode != 0 and "Cannot find package 'jsdom'" in (risultato.stderr or ""):
            self.skipTest("jsdom non installato: verifica template e sorgente sufficiente")
        self.assertEqual(
            risultato.returncode,
            0,
            risultato.stderr or risultato.stdout,
        )

    def test_verifica_checklist_regressione_passo_1_e_3_ingresso(self):
        """Checklist §4: fornitore, quantità, azzera movimento e conferma invariati col disegno."""
        pagina = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        ingresso = (ROOT / "web" / "js" / "features" / "ingresso-merce.js").read_text(
            encoding="utf-8",
        )
        for elemento in (
            'id="btn-ingresso-step-1"',
            "Continua agli articoli",
            'id="btn-reset-ingresso"',
            "Azzera movimento",
            'id="ingress-fornitore"',
            'id="ingress-quantita"',
            'id="btn-ingresso-step-2"',
            "Vai al riepilogo",
            'id="btn-salva-ingresso"',
            "Conferma ingresso",
            'data-step="3"',
        ):
            self.assertIn(elemento, pagina, elemento)

        messaggi = (
            "Seleziona un fornitore prima di continuare.",
            "Seleziona almeno un articolo.",
            "Inserisci una quantità valida",
            "Aggiungi almeno un articolo prima di continuare.",
            "Completa l'intestazione e aggiungi almeno un articolo.",
            "Salvataggio ingresso in corso…",
            "Ingresso registrato. Lotti creati:",
        )
        for testo in messaggi:
            self.assertIn(testo, ingresso, testo)

        self.assertIn("function azzeraIngresso()", ingresso)
        self.assertIn("quartoBovino = \"anteriore\"", ingresso)
        self.assertIn('categoriaSelezionata = null', ingresso)
        self.assertIn("righeIngresso = []", ingresso)
        self.assertIn("mostraStep(1)", ingresso)
        self.assertIn('$("btn-reset-ingresso").addEventListener("click", azzeraIngresso)', ingresso)
        self.assertIn('/api/v1/tracciabilita/ingressi', ingresso)

        nodo = _nodo_js_disponibile()
        if nodo is None:
            return

        modulo = (ROOT / "web" / "js" / "features" / "ingresso-articoli-disegno.js").as_uri()
        script = f"""
import {{ JSDOM }} from "jsdom";
import {{ renderArticoliConDisegno, categoriaUsaProfiloDisegno }} from "{modulo}";

const html = `<!DOCTYPE html><body>
  <ol>
    <li data-step-indicator="1" class="active">1</li>
    <li data-step-indicator="2">2</li>
    <li data-step-indicator="3">3</li>
  </ol>
  <section class="ingresso-step active" data-step="1">
    <select id="ingress-fornitore"><option value="">—</option><option value="10">Fornitore test</option></select>
    <input id="ingress-data" type="date" value="2026-11-28" />
    <input id="ingress-ddt" type="text" />
    <button id="btn-ingresso-step-1" type="button"></button>
    <button id="btn-reset-ingresso" type="button"></button>
  </section>
  <section class="ingresso-step" data-step="2" hidden>
    <div id="ingress-articoli"></div>
    <div id="ingress-articoli-feedback"></div>
    <input id="ingress-quantita" type="number" min="0.001" step="0.001" />
    <input id="ingress-temperatura" type="number" />
    <input id="ingress-lotto-fornitore" />
    <input id="ingress-origine" />
    <input id="ingress-note-lotto" />
    <select id="ingress-tipo-data"><option value=""></option></select>
    <input id="ingress-data-lotto" type="date" />
    <button id="btn-aggiungi-ingresso" type="button"></button>
    <button id="btn-ingresso-step-2" type="button"></button>
    <div id="ingress-categorie"></div>
  </section>
  <section class="ingresso-step" data-step="3" hidden>
    <strong id="summary-fornitore">-</strong>
    <strong id="summary-conteggio">0</strong>
    <strong id="summary-quantita">0</strong>
    <strong id="summary-data">-</strong>
    <strong id="summary-ddt">-</strong>
    <span id="ingress-conteggio">0</span>
    <div id="ingress-riepilogo-righe"></div>
    <div id="ingress-error"></div>
    <div id="ingress-success"></div>
    <button id="btn-salva-ingresso" type="button"></button>
  </section>
</body>`;

const dom = new JSDOM(html);
const {{ document }} = dom.window;
const $ = (id) => document.getElementById(id);

let righeIngresso = [];
let categoriaSelezionata = null;
let articoliSelezionati = new Set();
let quartoBovino = "anteriore";
let prossimoIdRiga = 1;
let apiCalls = 0;
const catalogo = [
  {{ id: 1, codice: "SUI-LONZA", nome: "Lonza di suino", categoria: "Suino", unita_misura: "kg", attivo: true }},
];

function mostraStep(numero) {{
  document.querySelectorAll(".ingresso-step").forEach((step) => {{
    const attivo = Number(step.dataset.step) === numero;
    step.hidden = !attivo;
    step.classList.toggle("active", attivo);
  }});
}}

function articoliAttivi() {{
  return catalogo.filter((a) => a.attivo);
}}

function renderArticoli() {{
  const container = $("ingress-articoli");
  container.replaceChildren();
  if (!categoriaSelezionata || !categoriaUsaProfiloDisegno(categoriaSelezionata)) return;
  const disponibili = articoliAttivi().filter(
    (a) => (a.categoria?.trim() || "Senza categoria") === categoriaSelezionata,
  );
  renderArticoliConDisegno(container, {{
    categoria: categoriaSelezionata,
    articoliDisponibili: disponibili,
    articoliSelezionati,
    onToggleArticolo: (id) => {{
      const key = String(id);
      if (articoliSelezionati.has(key)) articoliSelezionati.delete(key);
      else {{
        articoliSelezionati.clear();
        articoliSelezionati.add(key);
      }}
      renderArticoli();
    }},
    quartoBovino,
    onQuartoBovinoChange: () => {{}},
  }});
}}

function aggiungiRighe() {{
  const inputQuantita = $("ingress-quantita");
  const quantita = inputQuantita.valueAsNumber;
  if (!categoriaSelezionata) {{
    $("ingress-articoli-feedback").textContent = "Seleziona prima una categoria.";
    return;
  }}
  if (articoliSelezionati.size === 0) {{
    $("ingress-articoli-feedback").textContent = "Seleziona almeno un articolo.";
    return;
  }}
  if (!Number.isFinite(quantita) || !inputQuantita.checkValidity()) {{
    $("ingress-articoli-feedback").textContent =
      "Inserisci una quantità valida, da 0,001 a 999.999.999,999, con massimo 3 decimali.";
    return;
  }}
  const selezionati = articoliAttivi().filter((a) => articoliSelezionati.has(String(a.id)));
  selezionati.forEach((articolo) => {{
    righeIngresso.push({{
      id: prossimoIdRiga++,
      articoloId: articolo.id,
      articolo: articolo.nome,
      quantita,
    }});
  }});
  articoliSelezionati.clear();
  $("ingress-quantita").value = "";
  renderArticoli();
}}

function azzeraIngresso() {{
  $("ingress-fornitore").value = "";
  righeIngresso = [];
  categoriaSelezionata = null;
  quartoBovino = "anteriore";
  articoliSelezionati.clear();
  prossimoIdRiga = 1;
  mostraStep(1);
  renderArticoli();
}}

$("btn-ingresso-step-1").addEventListener("click", () => {{
  if (!$("ingress-fornitore").value) {{
    $("ingress-error").textContent = "Seleziona un fornitore prima di continuare.";
    return;
  }}
  mostraStep(2);
}});
$("btn-ingresso-step-2").addEventListener("click", () => {{
  if (righeIngresso.length === 0) {{
    $("ingress-articoli-feedback").textContent = "Aggiungi almeno un articolo prima di continuare.";
    return;
  }}
  mostraStep(3);
}});
$("btn-aggiungi-ingresso").addEventListener("click", aggiungiRighe);
$("btn-reset-ingresso").addEventListener("click", azzeraIngresso);
$("btn-salva-ingresso").addEventListener("click", () => {{
  if (!$("ingress-fornitore").value || righeIngresso.length === 0) {{
    $("ingress-error").textContent = "Completa l'intestazione e aggiungi almeno un articolo.";
    return;
  }}
  apiCalls += 1;
}});

const step2 = () => document.querySelector('[data-step="2"]');

$("btn-ingresso-step-1").click();
if ($("ingress-error").textContent !== "Seleziona un fornitore prima di continuare.") process.exit(1);
if (!step2().hidden) process.exit(2);

$("ingress-fornitore").value = "10";
$("btn-ingresso-step-1").click();
if (step2().hidden) process.exit(3);

categoriaSelezionata = "Suino";
renderArticoli();
const zona = $("ingress-articoli").querySelector('[data-codice="SUI-LONZA"]');
if (!zona) process.exit(4);
zona.dispatchEvent(new dom.window.MouseEvent("click", {{ bubbles: true }}));
if (!articoliSelezionati.has("1")) process.exit(5);

$("btn-aggiungi-ingresso").click();
if (!$("ingress-articoli-feedback").textContent.includes("quantità valida")) process.exit(6);

$("ingress-quantita").value = "2.5";
$("btn-aggiungi-ingresso").click();
if (righeIngresso.length !== 1 || righeIngresso[0].articolo !== "Lonza di suino") process.exit(7);

$("btn-ingresso-step-2").click();
if (document.querySelector('[data-step="3"]').hidden) process.exit(8);

$("ingress-fornitore").value = "";
$("btn-salva-ingresso").click();
if ($("ingress-error").textContent !== "Completa l'intestazione e aggiungi almeno un articolo.") process.exit(9);
if (apiCalls !== 0) process.exit(10);

$("ingress-fornitore").value = "10";
$("btn-salva-ingresso").click();
if (apiCalls !== 1) process.exit(11);

$("btn-reset-ingresso").click();
if (!document.querySelector('[data-step="1"]').classList.contains("active")) process.exit(12);
if ($("ingress-fornitore").value !== "") process.exit(13);
if (righeIngresso.length !== 0) process.exit(14);
if (quartoBovino !== "anteriore") process.exit(15);
"""
        risultato = subprocess.run(
            [nodo, "--input-type=module", "-e", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if risultato.returncode != 0 and "Cannot find package 'jsdom'" in (risultato.stderr or ""):
            self.skipTest("jsdom non installato: verifica sorgente e HTML sufficiente")
        self.assertEqual(
            risultato.returncode,
            0,
            risultato.stderr or risultato.stdout,
        )


def _nodo_js_disponibile():
    nodo = shutil.which("node")
    if nodo is None:
        nodo = shutil.which(
            "node",
            path="C:/Program Files/nodejs;C:/Program Files (x86)/nodejs",
        )
    return nodo


def _crea_tenant_macelleria_collaudo(nome_tenant: str, email: str) -> int:
    from saas.schemas import OnboardingRichiesta
    from saas.services.onboarding import crea_laboratorio

    esito = crea_laboratorio(
        OnboardingRichiesta(
            nome=nome_tenant,
            piano="basic",
            ragione_sociale="OSA Checklist Catalogo",
            indirizzo="Via Verifica 1",
            laboratorio="Lab checklist",
            partita_iva="12345678905",
            email=email,
            password="AdminChecklist1",
            catalogo="macelleria",
        )
    )
    return esito["tenant_id"]


def _fornitore_ingresso_collaudo(tenant_id: int) -> dict:
    from core.repositories import soggetti as soggetti_repo

    return soggetti_repo.crea(
        tenant_id,
        {
            "denominazione": "Fornitore checklist catalogo",
            "tipo_soggetto": "azienda",
            "ruolo_fornitore": True,
            "flag1_ing_merce": True,
            "attivo": True,
        },
    )


class CollaudoChecklistCatalogoDisegnoLiveTests(unittest.TestCase):
    def test_tenant_macelleria_nuovo_ingresso_lonza_crea_lotto_su_articolo(self):
        """Checklist §4: conferma ingresso crea il lotto sull'articolo Lonza di suino."""
        if not os.environ.get("GESTLAB_COLLAUDO_LIVE"):
            self.skipTest("Impostare GESTLAB_COLLAUDO_LIVE=1 su DB sacrificabile")

        from saas.main import registra_ingresso_tracciato
        from saas.repositories import tracciabilita_repo
        from saas.schemas import (
            IngressoTracciatoCreate,
            IngressoTracciatoRigaCreate,
        )

        email = f"checklist.catalogo.disegno.{uuid.uuid4().hex[:12]}@example.com"
        tenant_id = _crea_tenant_macelleria_collaudo(
            "Checklist catalogo disegno lonza",
            email,
        )
        arts = {a["codice"]: a for a in tracciabilita_repo.lista_articoli(tenant_id)}
        self.assertIn("SUI-LONZA", arts)
        lonza_id = arts["SUI-LONZA"]["id"]
        self.assertEqual(arts["SUI-LONZA"]["nome"], "Lonza di suino")

        fornitore = _fornitore_ingresso_collaudo(tenant_id)
        utente = {"tenant_id": tenant_id, "ruolo": "admin", "email": email}
        oggi = date.today()
        ing = registra_ingresso_tracciato(
            IngressoTracciatoCreate(
                data=oggi,
                numero_ddt="CHECKLIST-LONZA-SUINO",
                fornitore_id=fornitore["id"],
                righe=[
                    IngressoTracciatoRigaCreate(
                        articolo_id=lonza_id,
                        quantita=Decimal("1.250"),
                        origine="Italia",
                        data_scadenza=oggi + timedelta(days=21),
                        temperatura_ingresso=Decimal("2.00"),
                    )
                ],
            ),
            utente,
        )
        self.assertEqual(len(ing["lotti"]), 1)
        lotto = ing["lotti"][0]
        self.assertEqual(lotto["articolo_id"], lonza_id)
        dettaglio = tracciabilita_repo.dettaglio_lotto(tenant_id, lotto["id"])
        self.assertEqual(dettaglio["articolo"], "Lonza di suino")
        self.assertEqual(Decimal(str(dettaglio["quantita_iniziale"])), Decimal("1.250"))

    def test_tenant_macelleria_ingresso_vitello_carre_e_bovino_entrambi_quarti(self):
        """Checklist §4: VIT-CARRE + taglio anteriore e posteriore bovino."""
        if not os.environ.get("GESTLAB_COLLAUDO_LIVE"):
            self.skipTest("Impostare GESTLAB_COLLAUDO_LIVE=1 su DB sacrificabile")

        from saas.main import registra_ingresso_tracciato
        from saas.repositories import tracciabilita_repo
        from saas.schemas import (
            IngressoTracciatoCreate,
            IngressoTracciatoRigaCreate,
        )

        email = f"checklist.catalogo.disegno.{uuid.uuid4().hex[:12]}@example.com"
        tenant_id = _crea_tenant_macelleria_collaudo(
            "Checklist vitello e bovino",
            email,
        )
        arts = {a["codice"]: a for a in tracciabilita_repo.lista_articoli(tenant_id)}
        casi = (
            ("VIT-CARRE", "Carrè di vitello", Decimal("0.800")),
            ("BOV-PETTO", "Petto bovino", Decimal("3.500")),
            ("BOV-COSTATA", "Costata bovina", Decimal("2.100")),
        )
        for codice, nome_atteso, _ in casi:
            with self.subTest(codice=codice):
                self.assertIn(codice, arts)
                self.assertEqual(arts[codice]["nome"], nome_atteso)

        fornitore = _fornitore_ingresso_collaudo(tenant_id)
        utente = {"tenant_id": tenant_id, "ruolo": "admin", "email": email}
        oggi = date.today()
        scadenza = oggi + timedelta(days=21)
        righe = [
            IngressoTracciatoRigaCreate(
                articolo_id=arts[codice]["id"],
                quantita=quantita,
                origine="Italia",
                data_scadenza=scadenza,
                temperatura_ingresso=Decimal("2.00"),
            )
            for codice, _, quantita in casi
        ]
        ing = registra_ingresso_tracciato(
            IngressoTracciatoCreate(
                data=oggi,
                numero_ddt="CHECKLIST-VIT-BOV-QUARTI",
                fornitore_id=fornitore["id"],
                righe=righe,
            ),
            utente,
        )
        self.assertEqual(len(ing["lotti"]), 3)
        per_codice = {arts[c]["id"]: (c, nome) for c, nome, _ in casi}
        for lotto in ing["lotti"]:
            codice, nome_atteso = per_codice[lotto["articolo_id"]]
            with self.subTest(lotto=codice):
                dettaglio = tracciabilita_repo.dettaglio_lotto(tenant_id, lotto["id"])
                self.assertEqual(dettaglio["articolo"], nome_atteso)

    def test_tenant_macelleria_ingresso_pulsanti_fuori_profilo(self):
        """Checklist §4: mezzena/filetto bovino, filetto e lardo suino su un DDT."""
        if not os.environ.get("GESTLAB_COLLAUDO_LIVE"):
            self.skipTest("Impostare GESTLAB_COLLAUDO_LIVE=1 su DB sacrificabile")

        from saas.main import registra_ingresso_tracciato
        from saas.repositories import tracciabilita_repo
        from saas.schemas import (
            IngressoTracciatoCreate,
            IngressoTracciatoRigaCreate,
        )

        email = f"checklist.catalogo.disegno.{uuid.uuid4().hex[:12]}@example.com"
        tenant_id = _crea_tenant_macelleria_collaudo(
            "Checklist pulsanti fuori profilo",
            email,
        )
        arts = {a["codice"]: a for a in tracciabilita_repo.lista_articoli(tenant_id)}
        casi = (
            ("BOV-MEZZENA", "Mezzena bovina", Decimal("45.000")),
            ("BOV-FILETTO", "Filetto bovino", Decimal("1.200")),
            ("SUI-FILETTO", "Filetto di suino", Decimal("0.850")),
            ("SUI-LARDO", "Lardo di suino", Decimal("3.000")),
        )
        for codice, nome_atteso, _ in casi:
            with self.subTest(codice=codice):
                self.assertIn(codice, arts)
                self.assertEqual(arts[codice]["nome"], nome_atteso)

        fornitore = _fornitore_ingresso_collaudo(tenant_id)
        utente = {"tenant_id": tenant_id, "ruolo": "admin", "email": email}
        oggi = date.today()
        scadenza = oggi + timedelta(days=21)
        righe = [
            IngressoTracciatoRigaCreate(
                articolo_id=arts[codice]["id"],
                quantita=quantita,
                origine="Italia",
                data_scadenza=scadenza,
                temperatura_ingresso=Decimal("2.00"),
            )
            for codice, _, quantita in casi
        ]
        ing = registra_ingresso_tracciato(
            IngressoTracciatoCreate(
                data=oggi,
                numero_ddt="CHECKLIST-FUORI-PROFILO",
                fornitore_id=fornitore["id"],
                righe=righe,
            ),
            utente,
        )
        self.assertEqual(len(ing["lotti"]), 4)
        per_codice = {arts[c]["id"]: (c, nome) for c, nome, _ in casi}
        for lotto in ing["lotti"]:
            codice, nome_atteso = per_codice[lotto["articolo_id"]]
            with self.subTest(lotto=codice):
                dettaglio = tracciabilita_repo.dettaglio_lotto(tenant_id, lotto["id"])
                self.assertEqual(dettaglio["articolo"], nome_atteso)

    def test_tenant_macelleria_disattiva_taglio_su_profilo(self):
        """Checklist §4: disattivazione SUI-LONZA blocca ingresso su quel taglio."""
        if not os.environ.get("GESTLAB_COLLAUDO_LIVE"):
            self.skipTest("Impostare GESTLAB_COLLAUDO_LIVE=1 su DB sacrificabile")

        from saas.main import registra_ingresso_tracciato
        from saas.repositories import tracciabilita_repo
        from saas.schemas import (
            IngressoTracciatoCreate,
            IngressoTracciatoRigaCreate,
        )

        email = f"checklist.catalogo.disegno.{uuid.uuid4().hex[:12]}@example.com"
        tenant_id = _crea_tenant_macelleria_collaudo(
            "Checklist disattiva lonza",
            email,
        )
        arts = {a["codice"]: a for a in tracciabilita_repo.lista_articoli(tenant_id)}
        lonza_id = arts["SUI-LONZA"]["id"]
        coppa_id = arts["SUI-COPPA"]["id"]

        self.assertTrue(
            tracciabilita_repo.disattiva_articolo(
                tenant_id,
                lonza_id,
                utente_email=email,
            )
        )
        arts_dopo = {a["codice"]: a for a in tracciabilita_repo.lista_articoli(tenant_id)}
        self.assertFalse(arts_dopo["SUI-LONZA"]["attivo"])
        attivi_suino = [
            a for a in arts_dopo.values() if a["categoria"] == "Suino" and a["attivo"]
        ]
        self.assertNotIn(lonza_id, {a["id"] for a in attivi_suino})

        fornitore = _fornitore_ingresso_collaudo(tenant_id)
        utente = {"tenant_id": tenant_id, "ruolo": "admin", "email": email}
        oggi = date.today()
        scadenza = oggi + timedelta(days=21)

        with self.assertRaises(tracciabilita_repo.ArticoloNonTrovato):
            tracciabilita_repo.registra_ingresso(
                tenant_id=tenant_id,
                data=oggi,
                numero_ddt="CHECKLIST-LONZA-DISATTIVA",
                fornitore_id=fornitore["id"],
                righe=[
                    IngressoTracciatoRigaCreate(
                        articolo_id=lonza_id,
                        quantita=Decimal("1.000"),
                        origine="Italia",
                        data_scadenza=scadenza,
                        temperatura_ingresso=Decimal("2.00"),
                    )
                ],
            )

        ing = registra_ingresso_tracciato(
            IngressoTracciatoCreate(
                data=oggi,
                numero_ddt="CHECKLIST-COPPA-ATTIVA",
                fornitore_id=fornitore["id"],
                righe=[
                    IngressoTracciatoRigaCreate(
                        articolo_id=coppa_id,
                        quantita=Decimal("0.500"),
                        origine="Italia",
                        data_scadenza=scadenza,
                        temperatura_ingresso=Decimal("2.00"),
                    )
                ],
            ),
            utente,
        )
        self.assertEqual(len(ing["lotti"]), 1)
        self.assertEqual(ing["lotti"][0]["articolo_id"], coppa_id)

    def test_tenant_macelleria_condimento_e_preparato_in_catalogo(self):
        """Checklist §4: tenant nuovo espone Sale e i tre preparati nelle categorie attese."""
        if not os.environ.get("GESTLAB_COLLAUDO_LIVE"):
            self.skipTest("Impostare GESTLAB_COLLAUDO_LIVE=1 su DB sacrificabile")

        from saas.repositories import tracciabilita_repo

        email = f"checklist.catalogo.disegno.{uuid.uuid4().hex[:12]}@example.com"
        tenant_id = _crea_tenant_macelleria_collaudo(
            "Checklist condimento preparato",
            email,
        )
        arts = {a["codice"]: a for a in tracciabilita_repo.lista_articoli(tenant_id)}
        attesi = (
            ("COND-SALE", "Sale", "Condimento"),
            ("PREP-SALSICCIA", "Salsicce fresche", "Preparato"),
            ("PREP-HAMBURGER", "Hamburger di bovino", "Preparato"),
            ("PREP-ARROSTO", "Arrosto di vitello", "Preparato"),
        )
        for codice, nome, categoria in attesi:
            with self.subTest(codice=codice):
                self.assertIn(codice, arts)
                self.assertEqual(arts[codice]["nome"], nome)
                self.assertEqual(arts[codice]["categoria"], categoria)
                self.assertTrue(arts[codice]["attivo"])

    def test_tenant_macelleria_ingresso_completo_crea_documento_e_lotto(self):
        """Checklist §4: passo 1–3 regressione API — documento ingresso e lotto col taglio da disegno."""
        if not os.environ.get("GESTLAB_COLLAUDO_LIVE"):
            self.skipTest("Impostare GESTLAB_COLLAUDO_LIVE=1 su DB sacrificabile")

        from saas.main import registra_ingresso_tracciato
        from saas.repositories import tracciabilita_repo
        from saas.schemas import (
            IngressoTracciatoCreate,
            IngressoTracciatoRigaCreate,
        )

        email = f"checklist.catalogo.disegno.{uuid.uuid4().hex[:12]}@example.com"
        tenant_id = _crea_tenant_macelleria_collaudo(
            "Checklist regressione ingresso passi",
            email,
        )
        arts = {a["codice"]: a for a in tracciabilita_repo.lista_articoli(tenant_id)}
        lonza_id = arts["SUI-LONZA"]["id"]
        fornitore = _fornitore_ingresso_collaudo(tenant_id)
        utente = {"tenant_id": tenant_id, "ruolo": "admin", "email": email}
        oggi = date.today()
        numero_ddt = "CHECKLIST-REGRESS-PASSI-1-3"

        ing = registra_ingresso_tracciato(
            IngressoTracciatoCreate(
                data=oggi,
                numero_ddt=numero_ddt,
                fornitore_id=fornitore["id"],
                righe=[
                    IngressoTracciatoRigaCreate(
                        articolo_id=lonza_id,
                        quantita=Decimal("4.750"),
                        origine="Italia",
                        data_scadenza=oggi + timedelta(days=14),
                        temperatura_ingresso=Decimal("1.50"),
                    )
                ],
            ),
            utente,
        )
        doc_id = ing.get("documento_ingresso_id")
        self.assertIsNotNone(doc_id)
        self.assertEqual(len(ing["lotti"]), 1)
        lotto = ing["lotti"][0]
        self.assertEqual(lotto["articolo_id"], lonza_id)
        self.assertEqual(lotto["documento_ingresso_id"], doc_id)
        self.assertTrue(str(lotto.get("codice_lotto", "")).endswith("A"))

        dettaglio = tracciabilita_repo.dettaglio_lotto(tenant_id, lotto["id"])
        self.assertEqual(dettaglio["articolo"], "Lonza di suino")
        self.assertEqual(Decimal(str(dettaglio["quantita_iniziale"])), Decimal("4.750"))
        doc = dettaglio.get("documento_ingresso") or {}
        self.assertEqual(doc.get("numero_ddt"), numero_ddt)
        self.assertEqual(doc.get("fornitore"), fornitore["denominazione"])
        self.assertEqual(doc.get("id"), doc_id)

        with self.assertRaises(tracciabilita_repo.FornitoreNonValido):
            tracciabilita_repo.registra_ingresso(
                tenant_id=tenant_id,
                data=oggi,
                numero_ddt="CHECKLIST-SENZA-FORNITORE",
                fornitore_id=999_999_999,
                righe=[
                    IngressoTracciatoRigaCreate(
                        articolo_id=lonza_id,
                        quantita=Decimal("1.000"),
                        origine="Italia",
                        data_scadenza=oggi + timedelta(days=7),
                    )
                ],
            )


if __name__ == "__main__":
    unittest.main()