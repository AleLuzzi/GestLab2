/** Profilo laterale del suino: zone cliccabili con codice anagrafica (senza mezzena, filetto, lardo). */

import { creaGruppoZona } from "./zona-util.js";

const SVG_NS = "http://www.w3.org/2000/svg";

/** Sul disegno solo il nome del taglio (senza «di suino»). */
function etichettaBreveSuino(nome) {
  return nome.replace(/\s+di suino$/i, "");
}

/** Ordine allineato alla checklist catalogo-disegno. */
export const ZONE_SUINO = [
  {
    codice: "SUI-COPPA",
    nome: "Coppa di suino",
    d: "M 260 135 C 295 125, 325 118, 355 112 C 365 145, 372 178, 375 208 C 335 212, 295 218, 265 225 Z",
  },
  {
    codice: "SUI-LONZA",
    nome: "Lonza di suino",
    d: "M 355 112 C 430 100, 505 98, 565 108 C 550 140, 542 172, 542 202 C 485 200, 425 202, 375 208 C 372 178, 365 145, 355 112 Z",
  },
  {
    codice: "SUI-COSTINE",
    nome: "Costine di suino",
    d: "M 375 208 C 425 202, 485 200, 542 202 C 542 216, 544 228, 546 240 C 488 238, 430 240, 377 244 Z",
  },
  {
    codice: "SUI-SPALLA",
    nome: "Spalla di suino",
    d: "M 265 225 C 295 218, 335 212, 375 208 C 378 245, 378 275, 375 302 C 340 304, 305 300, 282 288 C 272 272, 266 250, 265 225 Z",
  },
  {
    codice: "SUI-PANCIA",
    nome: "Pancetta di suino",
    d: "M 377 244 C 430 240, 488 238, 546 240 C 552 258, 562 272, 572 282 C 510 302, 435 306, 375 302 C 378 282, 378 262, 377 244 Z",
  },
  {
    codice: "SUI-COSCIA",
    nome: "Coscia di suino",
    d: "M 565 108 C 625 120, 665 155, 675 205 C 680 245, 655 275, 650 300 C 625 306, 608 308, 595 308 C 585 296, 578 288, 572 282 C 552 262, 542 232, 542 202 C 542 172, 550 140, 565 108 Z",
  },
  {
    codice: "SUI-GUANCIA",
    nome: "Guanciale di suino",
    d: "M 185 245 C 195 235, 225 225, 265 225 C 266 250, 272 272, 282 288 C 245 285, 205 278, 185 268 Z",
  },
  {
    codice: "SUI-STINCO",
    nome: "Stinco di suino",
    d: [
      "M 295 294 C 318 302, 348 304, 375 302 C 374 328, 368 348, 368 368 L 336 368 C 336 350, 326 332, 315 318 Z",
      "M 595 308 C 612 308, 632 306, 650 300 C 655 325, 648 345, 648 368 L 615 368 C 615 348, 605 328, 595 308 Z",
    ],
  },
  {
    codice: "SUI-PIEDE",
    nome: "Piedino di suino",
    d: [
      "M 336 368 L 368 368 C 368 385, 365 398, 355 405 L 325 405 C 332 392, 336 380, 336 368 Z",
      "M 615 368 L 648 368 C 648 385, 645 398, 635 405 L 605 405 C 612 392, 615 380, 615 368 Z",
    ],
  },
  {
    codice: "SUI-CODA",
    nome: "Coda di suino",
    d: "M 665 165 C 685 162, 702 145, 695 130 C 688 118, 672 125, 678 138 C 684 150, 705 152, 718 142 Z",
  },
];

const SAGOMA_SUINO = [
  "M 195 140 L 180 105 L 215 118",
  "C 235 122, 250 130, 260 135",
  "C 360 105, 480 95, 565 108",
  "C 625 120, 665 155, 675 205",
  "C 680 245, 655 275, 650 300",
  "C 655 325, 648 345, 648 368",
  "C 648 385, 645 398, 635 405",
  "L 605 405",
  "C 612 392, 615 380, 615 368",
  "C 615 348, 605 328, 595 308",
  "C 585 296, 578 288, 572 282",
  "C 510 302, 435 306, 375 302",
  "C 374 328, 368 348, 368 368",
  "C 368 385, 365 398, 355 405",
  "L 325 405",
  "C 332 392, 336 380, 336 368",
  "C 336 350, 326 332, 315 318",
  "L 295 294",
  "C 250 288, 205 280, 185 268",
  "L 185 245",
  "C 165 255, 145 255, 130 250",
  "C 120 245, 115 225, 120 215",
  "C 125 212, 145 208, 160 198",
  "C 175 185, 180 165, 195 140 Z",
].join(" ");

const ORECCHIO_SUINO = "M 198 112 C 218 122, 238 142, 245 168 C 225 168, 205 158, 195 140";

/**
 * @param {SVGSVGElement} svg
 * @param {string} d
 * @param {string} classe
 */
function aggiungiTraccia(svg, d, classe) {
  const path = document.createElementNS(SVG_NS, "path");
  path.setAttribute("d", d);
  path.setAttribute("class", classe);
  path.setAttribute("aria-hidden", "true");
  svg.appendChild(path);
}

/**
 * Restituisce l'SVG del profilo suino con le dieci zone di taglio.
 * Mezzena, filetto e lardo restano pulsanti fuori dal disegno.
 * @returns {SVGSVGElement}
 */
export function creaProfiloSuino() {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "100 80 660 350");
  svg.setAttribute("class", "profilo-macelleria profilo-suino");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "Profilo suino per la selezione del taglio");
  svg.setAttribute("focusable", "false");

  aggiungiTraccia(svg, SAGOMA_SUINO, "profilo-contorno");

  const zone = document.createElementNS(SVG_NS, "g");
  zone.setAttribute("class", "profilo-zone");
  ZONE_SUINO.forEach((zona) =>
    zone.appendChild(
      creaGruppoZona({
        ...zona,
        etichetta: etichettaBreveSuino(zona.nome),
      }),
    ),
  );
  svg.appendChild(zone);

  aggiungiTraccia(svg, SAGOMA_SUINO, "profilo-contorno-linea");
  aggiungiTraccia(svg, ORECCHIO_SUINO, "profilo-contorno-linea");

  return svg;
}
