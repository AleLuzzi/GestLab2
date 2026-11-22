/** Profili bovino: quarto anteriore (14 zone) e posteriore (12). Mezzena e filetto restano pulsanti. */

import { creaGruppoZona } from "./zona-util.js";

const SVG_NS = "http://www.w3.org/2000/svg";

/** Testa, quarto posteriore e zampa: sagoma, non selezionabili. */
const SAGOME_BOVINO_ANTERIORE = [
  "M 265 80 C 245 70 225 55 210 35 C 205 25 190 20 185 30 C 185 45 195 55 205 65 C 190 65 170 60 160 70 C 150 80 145 95 135 110 C 115 135 90 165 75 190 C 68 202 72 215 85 220 C 95 225 105 235 120 235 C 140 235 160 225 180 230 C 200 235 215 240 225 240 L 265 80 Z",
  "M 588 100 C 660 100 720 90 770 85 C 830 80 875 90 890 130 C 905 170 915 250 920 350 C 920 380 910 410 905 430 L 900 320 C 895 380 885 460 875 520 L 890 540 L 845 540 L 845 520 C 850 460 855 390 835 340 C 815 390 795 460 785 520 L 800 540 L 755 540 L 755 520 C 765 450 775 380 755 320 C 710 335 650 360 590 370 L 588 100 Z",
  "M 350 390 C 360 430 365 480 355 515 L 340 530 L 375 530 L 385 515 L 385 450 L 395 515 L 380 540 L 420 540 L 435 515 C 430 480 425 440 425 405 L 380 410 Z",
];

export const ZONE_BOVINO_ANTERIORE = [
  {
    codice: "BOV-COLLO",
    nome: "Collo bovino",
    d: "M 265 80 L 323 78 C 325 110 323 135 320 160 C 310 205 290 250 265 280 C 250 260 235 248 225 240 C 245 190 258 135 265 80 Z",
    testi: [{ t: "Collo", x: 280, y: 185 }],
  },
  {
    codice: "BOV-REALE",
    nome: "Reale bovino",
    d: "M 323 78 C 370 82 415 92 462 98 L 468 152 L 320 160 C 323 135 325 110 323 78 Z",
    testi: [{ t: "Reale", x: 395, y: 130 }],
  },
  {
    codice: "BOV-SOTTOSPAL",
    nome: "Sottospalla bovina",
    d: "M 320 160 L 373 157 C 350 195 335 230 328 270 C 305 278 288 290 278 305 C 272 295 268 288 265 280 C 290 250 310 205 320 160 Z",
    testi: [{ t: "Sottospalla", x: 325, y: 220, rotate: -65 }],
  },
  {
    codice: "BOV-FESONE",
    nome: "Fesone di spalla bovino",
    d: "M 407 155 L 468 152 L 483 300 L 453 302 C 452 282 450 265 448 250 C 442 215 430 185 407 155 Z",
    testi: [
      { t: "Fesone di", x: 458, y: 200, rotate: 75 },
      { t: "spalla", x: 442, y: 205, rotate: 75 },
    ],
  },
  {
    codice: "BOV-CAPPELLO",
    nome: "Cappello del prete bovino",
    d: "M 373 157 L 407 155 C 430 185 442 215 448 250 C 405 252 365 258 328 270 C 335 230 350 195 373 157 Z",
    testi: [
      { t: "Cappello", x: 390, y: 215 },
      { t: "del prete", x: 390, y: 232 },
    ],
  },
  {
    codice: "BOV-FUSELLO",
    nome: "Girello di spalla bovino",
    d: "M 328 270 C 365 258 405 252 448 250 C 450 265 452 282 453 302 C 410 305 370 310 340 320 C 332 302 328 285 328 270 Z",
    testi: [
      { t: "Girello", x: 392, y: 282 },
      { t: "di spalla", x: 392, y: 298 },
    ],
  },
  {
    codice: "BOV-TRAVERSIN",
    nome: "Copertina di sotto bovina",
    d: "M 340 320 C 370 310 410 305 453 302 C 452 322 450 338 446 352 C 415 355 385 360 364 366 C 354 352 346 336 340 320 Z",
    testi: [
      { t: "Copertina", x: 400, y: 330 },
      { t: "di sotto", x: 400, y: 346 },
    ],
  },
  {
    codice: "BOV-BRIONE",
    nome: "Brione bovino",
    d: "M 364 366 C 385 360 415 355 446 352 L 440 378 L 378 392 C 373 383 368 375 364 366 Z",
    testi: [{ t: "Brione", x: 408, y: 375 }],
  },
  {
    codice: "BOV-PETTO",
    nome: "Petto bovino",
    d: "M 278 305 C 288 290 305 278 328 270 C 328 285 332 302 340 320 C 348 342 362 368 378 392 C 335 392 295 365 278 305 Z",
    testi: [{ t: "Petto", x: 315, y: 340, rotate: 55 }],
  },
  {
    codice: "BOV-FIOCCO",
    nome: "Fiocco bovino",
    d: "M 453 302 L 483 300 L 478 370 L 440 378 L 446 352 C 450 338 452 322 453 302 Z",
    testi: [{ t: "Fiocco", x: 468, y: 340, rotate: -85 }],
  },
  {
    codice: "BOV-BIANCO",
    nome: "Biancostato bovino",
    d: "M 462 98 C 505 103 548 103 588 100 L 593 292 L 483 300 L 468 152 L 462 98 Z",
    testi: [{ t: "Biancostato", x: 532, y: 205 }],
  },
  {
    codice: "BOV-PANCIA",
    nome: "Pancia bovina",
    d: "M 483 300 L 593 292 L 590 370 C 550 362 515 362 478 370 L 483 300 Z",
    testi: [{ t: "Pancia", x: 538, y: 338 }],
  },
  {
    codice: "BOV-SCALFO",
    nome: "Scalfo bovino",
    d: "M 378 392 L 440 378 L 435 412 L 385 420 L 378 392 Z",
    testi: [{ t: "Scalfo", x: 410, y: 405 }],
  },
  {
    codice: "BOV-GER-ANT",
    nome: "Geretto anteriore bovino",
    d: "M 385 420 L 435 412 L 432 452 L 390 456 L 385 420 Z",
    testi: [
      { t: "Geretto", x: 412, y: 435, size: 11 },
      { t: "anteriore", x: 412, y: 447, size: 11 },
    ],
  },
];

export const ZONE_BOVINO_POSTERIORE = [
  {
    codice: "BOV-COSTATA",
    nome: "Costata bovina",
    d: "M 462 98 C 505 103 548 103 588 100 L 593 292 L 483 300 L 468 152 L 462 98 Z",
    testi: [{ t: "Costata", x: 532, y: 205 }],
  },
  {
    codice: "BOV-CONTROF",
    nome: "Controfiletto bovino",
    d: "M 588 100 C 610 100 630 98 648 96 C 655 135 658 170 658 200 C 658 235 656 265 653 292 L 593 292 L 588 100 Z",
    testi: [{ t: "Controfiletto", x: 628, y: 195, rotate: -90 }],
  },
  {
    codice: "BOV-SCAMONE",
    nome: "Scamone bovino",
    d: "M 648 96 C 690 92 730 88 765 86 C 750 120 738 160 732 196 L 658 200 C 658 170 655 135 648 96 Z",
    testi: [{ t: "Scamone", x: 700, y: 145 }],
  },
  {
    codice: "BOV-FIANCH",
    nome: "Fianchetto bovino",
    d: "M 483 300 L 593 292 L 590 370 C 550 362 515 362 478 370 L 483 300 Z",
    testi: [{ t: "Fianchetto", x: 535, y: 338 }],
  },
  {
    codice: "BOV-NOCE",
    nome: "Noce bovina",
    d: "M 658 200 L 732 196 C 728 225 730 250 735 270 C 740 290 748 305 758 318 C 720 300 685 293 653 292 C 656 265 658 235 658 200 Z",
    testi: [{ t: "Noce", x: 695, y: 255 }],
  },
  {
    codice: "BOV-FESA",
    nome: "Fesa bovina",
    d: "M 765 86 C 790 84 815 84 835 88 C 825 105 825 125 835 142 C 845 155 855 162 862 168 C 850 192 844 218 843 240 L 735 270 C 730 250 728 225 732 196 C 738 160 750 120 765 86 Z",
    testi: [{ t: "Fesa", x: 795, y: 185 }],
  },
  {
    codice: "BOV-SOTTOF",
    nome: "Sottofesa bovina",
    d: "M 735 270 L 843 240 C 843 268 850 295 865 315 L 856 332 C 825 325 795 330 770 342 C 765 332 762 324 758 318 C 748 305 740 290 735 270 Z",
    testi: [{ t: "Sottofesa", x: 798, y: 295 }],
  },
  {
    codice: "BOV-CODONE",
    nome: "Codone bovino",
    d: "M 835 88 C 855 92 872 102 882 122 C 888 138 890 158 890 178 C 880 175 870 172 862 168 C 855 162 845 155 835 142 C 825 125 825 105 835 88 Z",
    testi: [{ t: "Codone", x: 852, y: 135, rotate: 48, size: 12 }],
  },
  {
    codice: "BOV-GIRELLO",
    nome: "Girello bovino",
    d: "M 862 168 C 870 172 880 175 890 178 C 890 225 882 275 865 315 C 850 295 843 268 843 240 C 844 218 850 192 862 168 Z",
    testi: [{ t: "Girello", x: 872, y: 230, rotate: -85 }],
  },
  {
    codice: "BOV-PESCE",
    nome: "Pesce bovino",
    d: "M 770 342 C 795 330 825 325 856 332 C 854 352 856 370 862 386 C 840 398 818 405 802 408 C 790 386 778 364 770 342 Z",
    testi: [{ t: "Pesce", x: 820, y: 368 }],
  },
  {
    codice: "BOV-GER-POST",
    nome: "Geretto posteriore bovino",
    d: "M 860 340 L 865 440 C 865 475 860 505 850 520 L 845 540 L 890 540 L 875 520 C 885 475 885 435 880 395 L 862 386 Z",
    testi: [
      { t: "Geretto", x: 866, y: 448, rotate: -88, size: 11 },
      { t: "posteriore", x: 878, y: 448, rotate: -88, size: 11 },
    ],
  },
  {
    codice: "BOV-CODA",
    nome: "Coda bovina",
    d: "M 882 122 C 895 140 905 180 910 240 C 915 300 912 355 918 385 L 910 395 L 908 415 L 898 425 L 892 395 L 888 370 C 892 315 894 245 890 178 C 890 158 888 138 882 122 Z",
    testi: [{ t: "Coda", x: 904, y: 355, rotate: -88 }],
  },
];

/** Testa, tracce del quarto anteriore e zampe: sagoma, non selezionabili. */
const SAGOME_BOVINO_POSTERIORE = [
  "M 265 80 C 245 70 225 55 210 35 C 205 25 190 20 185 30 C 185 45 195 55 205 65 C 190 65 170 60 160 70 C 150 80 145 95 135 110 C 115 135 90 165 75 190 C 68 202 72 215 85 220 C 95 225 105 235 120 235 C 140 235 160 225 180 230 C 200 235 215 240 225 240 L 265 80 Z",
  "M 265 80 L 323 78 C 325 110 323 135 320 160 C 310 205 290 250 265 280 C 250 260 235 248 225 240 C 245 190 258 135 265 80 Z",
  "M 323 78 C 370 82 415 92 462 98 L 468 152 L 320 160 C 323 135 325 110 323 78 Z",
  "M 320 160 L 373 157 C 350 195 335 230 328 270 C 305 278 288 290 278 305 C 272 295 268 288 265 280 C 290 250 310 205 320 160 Z",
  "M 373 157 L 407 155 C 430 185 442 215 448 250 C 405 252 365 258 328 270 C 335 230 350 195 373 157 Z",
  "M 407 155 L 468 152 L 483 300 L 453 302 C 452 282 450 265 448 250 C 442 215 430 185 407 155 Z",
  "M 328 270 C 365 258 405 252 448 250 C 450 265 452 282 453 302 C 410 305 370 310 340 320 C 332 302 328 285 328 270 Z",
  "M 278 305 C 288 290 305 278 328 270 C 328 285 332 302 340 320 C 348 342 362 368 378 392 C 335 392 295 365 278 305 Z",
  "M 340 320 C 370 310 410 305 453 302 C 452 322 450 338 446 352 C 415 355 385 360 364 366 C 354 352 346 336 340 320 Z",
  "M 364 366 C 385 360 415 355 446 352 L 440 378 L 378 392 C 373 383 368 375 364 366 Z",
  "M 453 302 L 483 300 L 478 370 L 440 378 L 446 352 C 450 338 452 322 453 302 Z",
  "M 378 392 L 440 378 L 435 412 L 385 420 Z",
  "M 385 420 L 435 412 L 432 452 L 390 456 Z",
  "M 350 390 C 360 430 365 480 355 515 L 340 530 L 375 530 L 385 515 L 385 450 L 395 515 L 380 540 L 420 540 L 435 515 C 430 480 425 440 425 405 L 380 410 Z",
  "M 590 370 C 640 355 700 325 755 320 C 775 380 765 450 755 520 L 755 540 L 800 540 L 785 520 C 795 460 815 390 835 340 L 860 340 L 865 440 C 865 475 860 505 850 520 L 845 540 L 890 540 L 875 520 C 885 475 885 435 880 395 L 810 315 L 745 310 Z",
];

/**
 * @param {SVGSVGElement} svg
 * @param {string} d
 */
function aggiungiSagoma(svg, d) {
  const path = document.createElementNS(SVG_NS, "path");
  path.setAttribute("d", d);
  path.setAttribute("class", "profilo-contorno");
  path.setAttribute("aria-hidden", "true");
  svg.appendChild(path);
}

/** @returns {SVGSVGElement} */
export function creaProfiloBovinoAnteriore() {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 1000 560");
  svg.setAttribute("class", "profilo-macelleria profilo-bovino profilo-bovino--anteriore");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "Quarto anteriore bovino per la selezione del taglio");
  svg.setAttribute("focusable", "false");

  SAGOME_BOVINO_ANTERIORE.forEach((d) => aggiungiSagoma(svg, d));

  const zone = document.createElementNS(SVG_NS, "g");
  zone.setAttribute("class", "profilo-zone");
  ZONE_BOVINO_ANTERIORE.forEach((zona) => zone.appendChild(creaGruppoZona(zona)));
  svg.appendChild(zone);

  return svg;
}

/** @returns {SVGSVGElement} */
export function creaProfiloBovinoPosteriore() {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 1000 560");
  svg.setAttribute("class", "profilo-macelleria profilo-bovino profilo-bovino--posteriore");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", "Quarto posteriore bovino per la selezione del taglio");
  svg.setAttribute("focusable", "false");

  SAGOME_BOVINO_POSTERIORE.forEach((d) => aggiungiSagoma(svg, d));

  const zone = document.createElementNS(SVG_NS, "g");
  zone.setAttribute("class", "profilo-zone");
  ZONE_BOVINO_POSTERIORE.forEach((zona) =>
    zone.appendChild(creaGruppoZona({ ...zona, hitSullaForma: true })),
  );
  svg.appendChild(zone);

  return svg;
}