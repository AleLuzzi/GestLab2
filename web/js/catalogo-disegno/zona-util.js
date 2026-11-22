/** Utility zone profilo: forma visiva e hit area separata (minimo «un dito» sul banco). */

const SVG_NS = "http://www.w3.org/2000/svg";

/** Larghezza minima bbox hit nel viewBox 480×300 (~44px con max-width 560px). */
export const DITO_MIN_VIEWBOX = 40;

/** Espansione verso l'esterno della forma visiva (i codici restano distinti anche in sovrapposizione). */
export const MARGINE_HIT_VIEWBOX = 12;

function puntiDaPath(d) {
  const numeri = d.match(/-?\d+(?:\.\d+)?/g);
  if (!numeri || numeri.length < 6) {
    return null;
  }
  const punti = [];
  for (let i = 0; i + 1 < numeri.length; i += 2) {
    punti.push({ x: Number(numeri[i]), y: Number(numeri[i + 1]) });
  }
  return punti;
}

function bboxPunti(punti) {
  const xs = punti.map((p) => p.x);
  const ys = punti.map((p) => p.y);
  return {
    minX: Math.min(...xs),
    maxX: Math.max(...xs),
    minY: Math.min(...ys),
    maxY: Math.max(...ys),
  };
}

function pathDaPunti(punti) {
  if (!punti.length) {
    return "";
  }
  const resto = punti
    .slice(1)
    .map((p) => `L ${p.x} ${p.y}`)
    .join(" ");
  return `M ${punti[0].x} ${punti[0].y} ${resto} Z`;
}

function centroideDaPath(d) {
  const punti = puntiDaPath(d);
  if (!punti?.length) {
    return { x: 0, y: 0 };
  }
  const n = punti.length;
  return {
    x: punti.reduce((s, p) => s + p.x, 0) / n,
    y: punti.reduce((s, p) => s + p.y, 0) / n,
  };
}

/**
 * Calcola il path dell'area cliccabile, più ampio della forma disegnata.
 * @param {string} d path della forma visiva (quadrilatero M/L/Z)
 * @returns {string}
 */
export function pathHitDaForma(d) {
  const punti = puntiDaPath(d);
  if (!punti) {
    return d;
  }

  const cx = punti.reduce((s, p) => s + p.x, 0) / punti.length;
  const cy = punti.reduce((s, p) => s + p.y, 0) / punti.length;

  let hit = punti.map((p) => {
    const dx = p.x - cx;
    const dy = p.y - cy;
    const len = Math.hypot(dx, dy) || 1;
    return {
      x: p.x + (dx / len) * MARGINE_HIT_VIEWBOX,
      y: p.y + (dy / len) * MARGINE_HIT_VIEWBOX,
    };
  });

  let { minX, maxX, minY, maxY } = bboxPunti(hit);
  let w = maxX - minX;
  let h = maxY - minY;
  const scaleX = w > 0 && w < DITO_MIN_VIEWBOX ? DITO_MIN_VIEWBOX / w : 1;
  const scaleY = h > 0 && h < DITO_MIN_VIEWBOX ? DITO_MIN_VIEWBOX / h : 1;

  if (scaleX !== 1 || scaleY !== 1) {
    hit = hit.map((p) => ({
      x: cx + (p.x - cx) * scaleX,
      y: cy + (p.y - cy) * scaleY,
    }));
  }

  return pathDaPunti(hit);
}

/**
 * @param {SVGGElement} gruppo
 * @param {{ t: string, x: number, y: number, rotate?: number, size?: number }} testo
 */
function aggiungiTestoZona(gruppo, { t, x, y, rotate, size }) {
  const etichetta = document.createElementNS(SVG_NS, "text");
  etichetta.setAttribute("class", "profilo-zona-etichetta");
  etichetta.setAttribute("x", String(x));
  etichetta.setAttribute("y", String(y));
  etichetta.setAttribute("text-anchor", "middle");
  etichetta.setAttribute("aria-hidden", "true");
  if (rotate != null) {
    etichetta.setAttribute("transform", `rotate(${rotate} ${x} ${y})`);
  }
  if (size != null) {
    etichetta.style.fontSize = `${size}px`;
  }
  etichetta.textContent = t;
  gruppo.appendChild(etichetta);
}

/**
 * @param {{
 *   codice: string,
 *   nome: string,
 *   etichetta?: string,
 *   d: string | string[],
 *   testi?: { t: string, x: number, y: number, rotate?: number, size?: number }[],
 * }} zona
 * `etichetta` è il testo sul disegno; se assente coincide con `nome`.
 * `testi` sostituisce il testo automatico al centro della forma.
 * @returns {SVGGElement}
 */
export function creaGruppoZona({ codice, nome, etichetta, d, testi }) {
  const testoEtichetta = etichetta ?? nome;
  const forme = Array.isArray(d) ? d : [d];
  const gruppo = document.createElementNS(SVG_NS, "g");
  gruppo.setAttribute("class", "profilo-zona");
  gruppo.setAttribute("data-codice", codice);
  gruppo.setAttribute("data-nome", nome);

  forme.forEach((formaD) => {
    const forma = document.createElementNS(SVG_NS, "path");
    forma.setAttribute("d", formaD);
    forma.setAttribute("class", "profilo-zona-forma");
    gruppo.appendChild(forma);

    const hit = document.createElementNS(SVG_NS, "path");
    hit.setAttribute("d", pathHitDaForma(formaD));
    hit.setAttribute("class", "profilo-zona-hit");
    hit.setAttribute("tabindex", "0");
    hit.setAttribute("role", "button");
    hit.setAttribute("aria-label", nome);
    hit.setAttribute("aria-pressed", "false");
    gruppo.appendChild(hit);

    if (testi) {
      return;
    }

    const { x, y } = centroideDaPath(formaD);
    aggiungiTestoZona(gruppo, { t: testoEtichetta, x, y });
    gruppo.lastChild.setAttribute("dominant-baseline", "middle");
  });

  testi?.forEach((testo) => aggiungiTestoZona(gruppo, testo));

  const titolo = document.createElementNS(SVG_NS, "title");
  titolo.textContent = nome;
  gruppo.appendChild(titolo);

  return gruppo;
}