/** Profilo laterale del vitello: zone cliccabili (mezzena esclusa, pulsante in fase 3). */

import { creaGruppoZona } from "./zona-util.js";

const SVG_NS = "http://www.w3.org/2000/svg";

/** Ordine zone sulla tabella checklist, senza VIT-MEZZENA. */
export const ZONE_VITELLO = [
  {
    codice: "VIT-COLLO",
    nome: "Collo di vitello",
    d: "M 36 52 L 88 44 L 96 108 L 44 116 Z",
  },
  {
    codice: "VIT-COPPA",
    nome: "Coppa di vitello",
    d: "M 94 40 L 148 34 L 156 98 L 102 106 Z",
  },
  {
    codice: "VIT-SPALLA",
    nome: "Spalla di vitello",
    d: "M 102 106 L 158 98 L 166 168 L 110 176 Z",
  },
  {
    codice: "VIT-PETTO",
    nome: "Petto di vitello",
    d: "M 110 176 L 168 168 L 176 228 L 118 236 Z",
  },
  {
    codice: "VIT-CARRE",
    nome: "Carrè di vitello",
    d: "M 158 98 L 238 92 L 246 148 L 166 156 Z",
  },
  {
    codice: "VIT-PANCIA",
    nome: "Pancia di vitello",
    d: "M 166 156 L 272 148 L 280 208 L 174 216 Z",
  },
  {
    codice: "VIT-LOMBO",
    nome: "Lombo di vitello",
    d: "M 152 34 L 278 28 L 286 88 L 160 94 Z",
  },
  {
    codice: "VIT-SCAMONE",
    nome: "Scamone di vitello",
    d: "M 238 92 L 318 86 L 326 142 L 246 148 Z",
  },
  {
    codice: "VIT-NOCE",
    nome: "Noce di vitello",
    d: "M 246 148 L 314 142 L 322 198 L 254 206 Z",
  },
  {
    codice: "VIT-FESA",
    nome: "Fesa di vitello",
    d: "M 318 86 L 378 92 L 370 152 L 310 146 Z",
  },
  {
    codice: "VIT-SOTTOF",
    nome: "Sottofesa di vitello",
    d: "M 310 146 L 370 152 L 362 202 L 302 196 Z",
  },
  {
    codice: "VIT-PESCE",
    nome: "Pesce di vitello",
    d: "M 278 28 L 378 24 L 386 86 L 286 92 Z",
  },
  {
    codice: "VIT-GIRELLO",
    nome: "Girello di vitello",
    d: "M 322 198 L 372 204 L 364 252 L 314 246 Z",
  },
  {
    codice: "VIT-GER-ANT",
    nome: "Garretto anteriore di vitello",
    d: "M 118 236 L 162 232 L 168 282 L 124 286 Z",
  },
  {
    codice: "VIT-GER-POST",
    nome: "Garretto posteriore di vitello",
    d: "M 314 246 L 364 252 L 356 290 L 306 284 Z",
  },
];

const CONTORNO_VITELLO = [
  "M 10 152",
  "Q 8 100 32 62",
  "Q 58 32 102 24",
  "L 388 16",
  "Q 424 22 442 48",
  "L 452 82",
  "Q 456 118 438 148",
  "L 398 168",
  "L 372 192",
  "L 358 238",
  "L 332 272",
  "L 268 282",
  "L 188 278",
  "L 132 258",
  "L 98 224",
  "L 68 188",
  "L 38 168",
  "Q 20 162 10 152",
  "Z",
].join(" ");

/**
 * Restituisce l'SVG del profilo vitello con le quindici zone di taglio.
 * @returns {SVGSVGElement}
 */
export function creaProfiloVitello() {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 480 300");
  svg.setAttribute("class", "profilo-macelleria profilo-vitello");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "Profilo vitello per la selezione del taglio");
  svg.setAttribute("focusable", "false");

  const contorno = document.createElementNS(SVG_NS, "path");
  contorno.setAttribute("d", CONTORNO_VITELLO);
  contorno.setAttribute("class", "profilo-contorno");
  contorno.setAttribute("aria-hidden", "true");
  svg.appendChild(contorno);

  const zone = document.createElementNS(SVG_NS, "g");
  zone.setAttribute("class", "profilo-zone");
  ZONE_VITELLO.forEach((zona) => zone.appendChild(creaGruppoZona(zona)));
  svg.appendChild(zone);

  return svg;
}