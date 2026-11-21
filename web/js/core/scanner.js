const INTERVALLO_MASSIMO_MS = 45;
const LUNGHEZZA_MINIMA = 6;

export function creaBufferScanner({
  intervalloMassimoMs = INTERVALLO_MASSIMO_MS,
  lunghezzaMinima = LUNGHEZZA_MINIMA,
} = {}) {
  let caratteri = "";
  let ultimo = 0;

  return {
    aggiungi(carattere, istante) {
      const continua = caratteri.length > 0 && istante - ultimo <= intervalloMassimoMs;
      if (caratteri && !continua) caratteri = "";
      const giaInCorso = caratteri.length >= 1 && continua;
      caratteri += carattere;
      ultimo = istante;
      return giaInCorso;
    },
    chiudi(istante) {
      const codice = caratteri;
      const rapida = codice.length >= lunghezzaMinima && istante - ultimo <= intervalloMassimoMs;
      caratteri = "";
      ultimo = 0;
      return rapida ? codice : null;
    },
  };
}

function campoTesto(elemento) {
  if (!elemento || typeof elemento.value !== "string") return null;
  const tag = elemento.tagName;
  if (tag !== "INPUT" && tag !== "TEXTAREA") return null;
  if (elemento.type === "password" || elemento.type === "email") return null;
  return elemento;
}

function ritiraCodiceDalCampo(campo, codice) {
  const input = campoTesto(campo);
  if (!input || !codice) return;
  if (input.value.endsWith(codice)) {
    input.value = input.value.slice(0, -codice.length);
  } else if (input.value.endsWith(codice[0])) {
    input.value = input.value.slice(0, -1);
  } else {
    return;
  }
  input.dispatchEvent(new Event("input", { bubbles: true }));
}

const gestori = [];

export function registraScanner(gestore) {
  gestori.push(gestore);
}

export function initScanner() {
  const buffer = creaBufferScanner();
  document.addEventListener("keydown", (event) => {
    if (event.ctrlKey || event.altKey || event.metaKey || event.isComposing) return;
    const campo = event.target;
    if (campo?.type === "password" || campo?.type === "email") return;

    if (event.key === "Enter" || event.key === "Tab") {
      const codice = buffer.chiudi(event.timeStamp);
      if (!codice) return;
      event.preventDefault();
      event.stopPropagation();
      ritiraCodiceDalCampo(campo, codice);
      for (const gestore of gestori) {
        if (gestore(codice, campo) === true) break;
      }
      return;
    }

    if (event.key.length !== 1) return;
    if (buffer.aggiungi(event.key, event.timeStamp)) event.preventDefault();
  }, true);
}
