/** Feedback nome taglio: hover/etichetta in SVG, conferma testuale dopo il clic (come ingresso merce). */

/**
 * @param {string} nome
 * @returns {string}
 */
export function testoConfermaTaglio(nome) {
  return `Selezionato: ${nome}. Inserisci la quantità.`;
}

/**
 * Enter e Spazio attivano la zona come i pulsanti articolo (`<button type="button">`).
 * @param {SVGPathElement} hit
 * @param {() => void} onActivate
 */
export function collegaAttivazioneZona(hit, onActivate) {
  if (!hit || typeof onActivate !== "function") {
    return;
  }
  hit.addEventListener("click", onActivate);
  hit.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onActivate();
    }
  });
}

/**
 * @param {SVGElement} svg
 * @param {HTMLElement} feedbackEl
 */
export function collegaFeedbackTaglioProfilo(svg, feedbackEl) {
  if (!svg || !feedbackEl) {
    return;
  }
  svg.querySelectorAll(".profilo-zona:not(.profilo-zona--disattiva) .profilo-zona-hit").forEach((hit) => {
    collegaAttivazioneZona(hit, () => {
      const gruppo = hit.closest(".profilo-zona");
      const nome = gruppo?.getAttribute("data-nome")?.trim();
      if (nome) {
        feedbackEl.textContent = testoConfermaTaglio(nome);
      }
    });
  });
}