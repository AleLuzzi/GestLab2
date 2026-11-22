/** Ingresso merce: profilo macelleria al posto della griglia articoli (Bovino, Vitello, Suino). */

import {
  creaProfiloBovinoAnteriore,
  creaProfiloBovinoPosteriore,
  ZONE_BOVINO_ANTERIORE,
  ZONE_BOVINO_POSTERIORE,
} from "../catalogo-disegno/profilo-bovino.js";
import { creaProfiloSuino } from "../catalogo-disegno/profilo-suino.js";
import { creaProfiloVitello } from "../catalogo-disegno/profilo-vitello.js";
import { collegaAttivazioneZona } from "../catalogo-disegno/profilo-interazione.js";

export const CATEGORIE_CON_PROFILO = ["Bovino", "Vitello", "Suino"];

/** Codici «Pulsante» nella checklist, per specie (ordine mostrato accanto al disegno). */
export const CODICI_FUORI_PROFILO = {
  Bovino: ["BOV-MEZZENA", "BOV-FILETTO"],
  Suino: ["SUI-MEZZENA", "SUI-FILETTO", "SUI-LARDO"],
  Vitello: ["VIT-MEZZENA"],
};

const CODICI_QUARTO_ANTERIORE = new Set(ZONE_BOVINO_ANTERIORE.map((zona) => zona.codice));
const CODICI_QUARTO_POSTERIORE = new Set(ZONE_BOVINO_POSTERIORE.map((zona) => zona.codice));

/**
 * Quarto da mostrare dopo una selezione per codice (scanner o altro).
 * @param {string} codice
 * @returns {"anteriore"|"posteriore"|null}
 */
export function quartoBovinoPerCodice(codice) {
  const normalizzato = String(codice ?? "").trim();
  if (CODICI_QUARTO_POSTERIORE.has(normalizzato)) {
    return "posteriore";
  }
  if (CODICI_QUARTO_ANTERIORE.has(normalizzato)) {
    return "anteriore";
  }
  return null;
}

/**
 * @param {string} categoria
 * @returns {boolean}
 */
export function categoriaUsaProfiloDisegno(categoria) {
  return CATEGORIE_CON_PROFILO.includes(categoria);
}

/** @param {Array<{ id: number|string, codice?: string }>} articoli */
function mappaArticoliPerCodice(articoli) {
  const perCodice = new Map();
  articoli.forEach((articolo) => {
    const codice = String(articolo.codice ?? "").trim();
    if (codice) {
      perCodice.set(codice, articolo);
    }
  });
  return perCodice;
}

/**
 * @param {SVGElement} svg
 * @param {Map<string, { id: number|string }>} perCodice
 * @param {Set<string>} articoliSelezionati
 */
function applicaStatoZone(svg, perCodice, articoliSelezionati) {
  svg.querySelectorAll(".profilo-zona").forEach((gruppo) => {
    const codice = gruppo.getAttribute("data-codice");
    const articolo = codice ? perCodice.get(codice) : null;
    const disattiva = !articolo;
    gruppo.classList.toggle("profilo-zona--disattiva", disattiva);
    const selezionato = articolo && articoliSelezionati.has(String(articolo.id));
    gruppo.classList.toggle("profilo-zona--selezionata", Boolean(selezionato));
    gruppo.querySelectorAll(".profilo-zona-hit").forEach((hit) => {
      hit.setAttribute("aria-pressed", String(Boolean(selezionato)));
      if (disattiva) {
        hit.setAttribute("tabindex", "-1");
        hit.setAttribute("aria-disabled", "true");
      } else {
        hit.setAttribute("tabindex", "0");
        hit.removeAttribute("aria-disabled");
      }
    });
  });
}

/** @typedef {"anteriore"|"posteriore"} QuartoBovino */

/**
 * @param {string} categoria
 * @param {QuartoBovino} quartoBovino
 * @returns {SVGSVGElement|null}
 */
function creaSvgProfilo(categoria, quartoBovino) {
  if (categoria === "Suino") {
    return creaProfiloSuino();
  }
  if (categoria === "Vitello") {
    return creaProfiloVitello();
  }
  if (categoria === "Bovino") {
    return quartoBovino === "posteriore"
      ? creaProfiloBovinoPosteriore()
      : creaProfiloBovinoAnteriore();
  }
  return null;
}

/**
 * @param {QuartoBovino} quartoAttivo
 * @param {(quarto: QuartoBovino) => void} onQuartoChange
 * @returns {HTMLDivElement}
 */
function creaComandiQuartoBovino(quartoAttivo, onQuartoChange) {
  const gruppo = document.createElement("div");
  gruppo.className = "profilo-bovino-quarti";
  gruppo.setAttribute("role", "group");
  gruppo.setAttribute("aria-label", "Quarto di mezzena bovina");

  /** @type {Array<{ id: QuartoBovino, etichetta: string }>} */
  const opzioni = [
    { id: "anteriore", etichetta: "Quarto anteriore" },
    { id: "posteriore", etichetta: "Quarto posteriore" },
  ];
  opzioni.forEach(({ id, etichetta }) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "categoria-button";
    button.textContent = etichetta;
    button.setAttribute("aria-pressed", String(quartoAttivo === id));
    button.addEventListener("click", () => {
      if (quartoAttivo !== id) {
        onQuartoChange(id);
      }
    });
    gruppo.appendChild(button);
  });
  return gruppo;
}

/**
 * @param {{ nome: string, unita_misura: string, id: number|string }} articolo
 * @param {Set<string>} articoliSelezionati
 * @param {(id: string) => void} onToggleArticolo
 * @returns {HTMLButtonElement}
 */
function creaPulsanteArticolo(articolo, articoliSelezionati, onToggleArticolo) {
  const id = String(articolo.id);
  const button = document.createElement("button");
  button.type = "button";
  button.className = "articolo-button";
  button.textContent = `${articolo.nome} (${articolo.unita_misura})`;
  button.setAttribute("aria-pressed", String(articoliSelezionati.has(id)));
  button.dataset.codice = String(articolo.codice ?? "").trim();
  button.addEventListener("click", () => onToggleArticolo(id));
  return button;
}

/**
 * @param {HTMLElement} container `#ingress-articoli`
 * @param {{
 *   categoria: string,
 *   articoliDisponibili: Array<{ id: number|string, codice?: string, nome: string, unita_misura: string }>,
 *   articoliSelezionati: Set<string>,
 *   onToggleArticolo: (id: string) => void,
 *   quartoBovino?: QuartoBovino,
 *   onQuartoBovinoChange?: (quarto: QuartoBovino) => void,
 * }} opzioni
 */
export function renderArticoliConDisegno(container, opzioni) {
  const {
    categoria,
    articoliDisponibili,
    articoliSelezionati,
    onToggleArticolo,
    quartoBovino = "anteriore",
    onQuartoBovinoChange,
  } = opzioni;

  container.replaceChildren();
  container.className = "ingress-articoli-disegno";
  container.setAttribute("aria-label", "Selezione taglio sul profilo");

  if (categoria === "Bovino" && typeof onQuartoBovinoChange === "function") {
    container.appendChild(creaComandiQuartoBovino(quartoBovino, onQuartoBovinoChange));
  }

  const perCodice = mappaArticoliPerCodice(articoliDisponibili);
  const svg = creaSvgProfilo(categoria, quartoBovino);

  if (svg) {
    applicaStatoZone(svg, perCodice, articoliSelezionati);

    svg.querySelectorAll(".profilo-zona:not(.profilo-zona--disattiva) .profilo-zona-hit").forEach((hit) => {
      collegaAttivazioneZona(hit, () => {
        const codice = hit.closest(".profilo-zona")?.getAttribute("data-codice");
        const articolo = codice ? perCodice.get(codice) : null;
        if (!articolo) {
          return;
        }
        onToggleArticolo(String(articolo.id));
      });
    });

    const rigaProfilo = document.createElement("div");
    rigaProfilo.className = "profilo-macelleria-riga";

    const wrap = document.createElement("div");
    wrap.className = "profilo-macelleria-wrap";
    wrap.appendChild(svg);
    rigaProfilo.appendChild(wrap);

    const codiciFuori = CODICI_FUORI_PROFILO[categoria] ?? [];
    const pulsantiFuori = codiciFuori
      .map((codice) => perCodice.get(codice))
      .filter(Boolean);

    if (pulsantiFuori.length) {
      const riga = document.createElement("div");
      riga.className = "articoli-fuori-profilo";
      riga.setAttribute("aria-label", "Tagli fuori profilo");
      pulsantiFuori.forEach((articolo) => {
        riga.appendChild(creaPulsanteArticolo(articolo, articoliSelezionati, onToggleArticolo));
      });
      rigaProfilo.appendChild(riga);
    }

    container.appendChild(rigaProfilo);
  }
}