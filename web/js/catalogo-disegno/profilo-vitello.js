/** Profilo laterale del vitello: zone cliccabili (mezzena esclusa, pulsante in fase 3). */

import { creaGruppoZona } from "./zona-util.js";

const SVG_NS = "http://www.w3.org/2000/svg";

/** Ordine zone sulla tabella checklist, senza VIT-MEZZENA. I bordi seguono la sagoma. */
export const ZONE_VITELLO = [
  {
    codice: "VIT-COLLO",
    nome: "Collo di vitello",
    d: "M 322 72 C 325 140 305 205 266 256 L 298 246 L 330 158 L 340 71 C 334 72 328 72 322 72 Z",
    testi: [{ t: "Collo", x: 312, y: 165, rotate: -68 }],
  },
  {
    codice: "VIT-COPPA",
    nome: "Coppa di vitello",
    d: "M 340 71 C 370 63 410 63 455 68 L 448 158 L 330 158 L 340 71 Z",
    testi: [{ t: "Coppa", x: 395, y: 118 }],
  },
  {
    codice: "VIT-SPALLA",
    nome: "Spalla di vitello",
    d: "M 330 158 L 448 158 L 436 250 L 425 290 C 395 280 370 280 346 290 L 320 255 L 298 246 L 330 158 Z",
    testi: [{ t: "Spalla", x: 378, y: 210 }],
  },
  {
    codice: "VIT-PETTO",
    nome: "Petto di vitello",
    d: "M 298 246 L 320 255 L 346 290 L 362 355 C 330 355 310 340 296 315 C 288 302 278 295 276 280 C 274 270 270 262 266 256 L 298 246 Z",
    testi: [{ t: "Petto", x: 318, y: 305, rotate: 55 }],
  },
  {
    codice: "VIT-CARRE",
    nome: "Carrè di vitello",
    d: "M 455 68 C 500 73 535 76 575 77 L 565 242 L 436 250 L 448 158 L 455 68 Z",
    testi: [{ t: "Carrè", x: 505, y: 160 }],
  },
  {
    codice: "VIT-PANCIA",
    nome: "Pancia di vitello",
    d: "M 436 250 L 565 242 L 688 230 L 703 196 L 711 224 L 733 272 L 748 292 C 725 288 705 300 680 315 C 655 330 625 348 600 348 C 565 348 525 335 485 333 C 455 332 430 340 412 345 L 425 290 L 436 250 Z",
    testi: [{ t: "Pancia", x: 560, y: 300 }],
  },
  {
    codice: "VIT-LOMBO",
    nome: "Lombo di vitello",
    d: "M 575 77 C 620 76 660 73 698 72 C 696 115 698 155 703 196 L 688 230 L 565 242 L 575 77 Z",
    testi: [{ t: "Lombo", x: 630, y: 155 }],
  },
  {
    codice: "VIT-SCAMONE",
    nome: "Scamone di vitello",
    d: "M 698 72 C 745 64 780 61 812 64 L 800 195 L 703 196 C 698 160 696 115 698 72 Z",
    testi: [{ t: "Scamone", x: 752, y: 135 }],
  },
  {
    codice: "VIT-NOCE",
    nome: "Noce di vitello",
    d: "M 703 196 L 800 195 L 785 305 L 748 292 C 733 272 721 249 711 224 L 703 196 Z",
    testi: [{ t: "Noce", x: 755, y: 250 }],
  },
  {
    codice: "VIT-FESA",
    nome: "Fesa di vitello",
    d: "M 812 64 C 848 68 872 88 885 130 L 860 145 L 835 190 L 800 195 L 812 64 Z",
    testi: [{ t: "Fesa", x: 835, y: 145 }],
  },
  {
    codice: "VIT-SOTTOF",
    nome: "Sottofesa di vitello",
    d: "M 800 195 L 835 190 L 820 255 L 790 270 L 800 195 Z",
    testi: [
      { t: "Sotto", x: 808, y: 222, size: 13 },
      { t: "fesa", x: 808, y: 238, size: 13 },
    ],
  },
  {
    codice: "VIT-PESCE",
    nome: "Pesce di vitello",
    d: "M 790 270 L 820 255 L 862 265 C 858 290 856 305 856 316 C 836 320 818 328 800 340 L 790 270 Z",
    testi: [{ t: "Pesce", x: 825, y: 300, size: 13 }],
  },
  {
    codice: "VIT-GIRELLO",
    nome: "Girello di vitello",
    d: "M 885 130 C 885 175 872 225 862 265 L 820 255 L 835 190 L 860 145 Z",
    testi: [{ t: "Girello", x: 858, y: 200, rotate: -78 }],
  },
  {
    codice: "VIT-GER-ANT",
    nome: "Garretto anteriore di vitello",
    d: "M 346 290 C 375 278 408 278 440 290 L 427 351 L 415 390 L 402 448 L 403 505 L 355 505 L 375 450 L 368 392 L 359 332 Z",
    testi: [
      { t: "Garretto", x: 395, y: 400, size: 13 },
      { t: "anteriore", x: 395, y: 418, size: 13 },
    ],
  },
  {
    codice: "VIT-GER-POST",
    nome: "Garretto posteriore di vitello",
    d: "M 800 340 C 818 328 836 320 856 316 L 864 345 L 872 365 L 868 416 L 868 468 L 838 448 L 823 376 L 802 342 Z",
    testi: [
      { t: "Garretto", x: 842, y: 400, rotate: -82, size: 13 },
      { t: "posteriore", x: 856, y: 400, rotate: -82, size: 13 },
    ],
  },
];

/**
 * Sagoma non selezionabile, nell'ordine di disegno dell'SVG:
 * zampe interne, corpo, testa, zampa anteriore, quarto posteriore e coda.
 */
const TRACCE_VITELLO = [
  {
    classe: "profilo-contorno",
    d: "M 412 332 L 415 395 C 415 415 412 435 418 455 L 424 475 C 424 485 418 495 415 505 C 415 512 405 516 385 516 C 378 516 376 510 380 502 C 388 488 395 470 395 450 L 390 380 L 412 332 Z",
  },
  {
    classe: "profilo-contorno",
    d: "M 732 290 L 758 360 C 765 385 765 415 755 445 C 748 468 735 485 725 498 C 720 506 725 514 738 514 C 755 514 768 508 770 498 L 780 490 C 782 465 792 435 802 410 L 814 380 L 775 290 L 732 290 Z",
  },
  {
    classe: "profilo-corpo",
    d: "M 322 72 C 345 72 370 63 398 63 C 435 63 475 73 535 76 C 595 79 650 76 698 72 C 688 135 695 215 732 275 C 740 285 745 290 748 292 C 725 288 705 300 680 315 C 655 330 625 348 600 348 C 565 348 525 335 485 333 C 455 332 430 340 412 345 L 425 290 C 395 280 370 280 346 290 L 362 355 C 330 355 310 340 296 315 C 288 302 278 295 276 280 C 274 270 270 262 266 256 C 305 205 325 140 322 72 Z",
  },
  {
    classe: "profilo-contorno",
    d: "M 148 62 C 128 42 102 35 94 48 C 88 58 98 78 118 90 L 135 95 Z",
  },
  {
    classe: "profilo-contorno-linea",
    d: "M 102 53 C 112 52 125 60 132 72",
  },
  {
    classe: "profilo-contorno",
    d: "M 230 56 C 218 42 202 33 188 34 C 175 35 162 48 152 60 C 142 70 132 82 132 98 C 132 112 124 125 112 136 C 102 145 93 152 94 166 C 95 178 102 186 112 190 C 122 196 135 198 148 194 C 165 204 185 204 202 200 C 222 200 245 222 266 256 C 305 205 325 140 322 72 C 305 72 285 68 265 62 Z",
  },
  {
    classe: "profilo-contorno",
    d: "M 240 60 C 262 38 292 28 304 42 C 312 52 302 78 278 92 C 264 98 250 96 240 94",
  },
  {
    classe: "profilo-contorno-linea",
    d: "M 294 48 C 282 46 266 56 254 74",
  },
  {
    classe: "profilo-dettaglio",
    d: "M 178 100 C 185 96 196 97 204 100 C 200 108 190 114 182 111 C 176 109 175 103 178 100 Z",
  },
  {
    classe: "profilo-dettaglio",
    d: "M 111 168 C 115 165 121 161 122 157 C 126 160 126 168 120 172 C 115 175 110 172 111 168 Z",
  },
  {
    classe: "profilo-contorno-linea",
    d: "M 106 186 C 120 187 136 190 153 185",
  },
  {
    classe: "profilo-contorno",
    d: "M 346 290 C 375 278 408 278 440 290 C 435 325 425 358 415 390 C 410 408 402 425 402 448 L 403 498 C 398 503 392 507 392 512 C 392 522 378 528 356 528 C 346 528 344 522 350 512 C 362 495 375 478 375 450 C 375 430 368 412 368 392 C 368 362 358 325 346 290 Z",
  },
  {
    classe: "profilo-contorno",
    d: "M 698 72 C 745 64 795 60 832 64 C 868 68 885 88 885 130 C 885 175 872 225 862 265 C 855 292 855 318 864 345 L 872 365 C 868 398 866 435 868 468 L 872 490 C 865 495 858 500 858 508 C 858 520 842 526 822 526 C 814 526 812 520 818 510 C 828 492 838 475 838 448 C 838 415 830 385 814 360 C 795 330 772 302 748 292 C 705 245 688 155 698 72 Z",
  },
  {
    classe: "profilo-contorno-linea",
    d: "M 800 340 C 818 328 836 320 856 316",
  },
  {
    classe: "profilo-contorno",
    d: "M 840 90 C 862 96 878 115 882 150 C 885 185 884 235 885 280 C 878 302 874 325 880 348 C 884 360 890 368 898 376 C 905 355 908 330 902 308 C 898 294 894 285 894 275 C 894 230 896 180 892 140 C 888 100 870 82 840 90 Z",
  },
];

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
 * Restituisce l'SVG del profilo vitello con le quindici zone di taglio.
 * @returns {SVGSVGElement}
 */
export function creaProfiloVitello() {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 1000 560");
  svg.setAttribute("class", "profilo-macelleria profilo-vitello");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "Profilo vitello per la selezione del taglio");
  svg.setAttribute("focusable", "false");

  TRACCE_VITELLO.forEach((traccia) => aggiungiTraccia(svg, traccia.d, traccia.classe));

  const zone = document.createElementNS(SVG_NS, "g");
  zone.setAttribute("class", "profilo-zone");
  ZONE_VITELLO.forEach((zona) => zone.appendChild(creaGruppoZona(zona)));
  svg.appendChild(zone);

  return svg;
}