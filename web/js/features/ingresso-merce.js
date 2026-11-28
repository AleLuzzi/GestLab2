import { api } from "../api/client.js";
import { $ } from "../core/dom.js";
import { registraScanner } from "../core/scanner.js?v=20261121-5";
import { testoConfermaTaglio } from "../catalogo-disegno/profilo-interazione.js";
import {
  categoriaUsaProfiloDisegno,
  quartoBovinoPerCodice,
  renderArticoliConDisegno,
} from "./ingresso-articoli-disegno.js";

let fornitori = [];
let articoli = [];
let righeIngresso = [];
let categoriaSelezionata = null;
let articoliSelezionati = new Set();
let datiCaricati = false;
let caricamentoDati = null;
let prossimoIdRiga = 1;
const MESSAGGIO_DOCUMENTO_DUPLICATO =
  "Esiste già un ingresso con la stessa data, lo stesso fornitore e lo stesso numero documento.";
const ORDINE_CATEGORIE_INGRESSO = [
  "Bovino",
  "Vitello",
  "Suino",
  "Condimento",
  "Preparato",
];
/** @type {"anteriore"|"posteriore"} */
let quartoBovino = "anteriore";

function dataLocaleISO() {
  const oggi = new Date();
  const mese = String(oggi.getMonth() + 1).padStart(2, "0");
  const giorno = String(oggi.getDate()).padStart(2, "0");
  return `${oggi.getFullYear()}-${mese}-${giorno}`;
}

function nomeFornitoreSelezionato() {
  const select = $("ingress-fornitore");
  return select.selectedIndex > 0 ? select.options[select.selectedIndex].textContent : "-";
}

function mostraStep(numero) {
  const pannello = $("view-ingresso-merce");
  pannello.querySelectorAll(".ingresso-step").forEach((step) => {
    const attivo = Number(step.dataset.step) === numero;
    step.hidden = !attivo;
    step.classList.toggle("active", attivo);
  });
  pannello.querySelectorAll("[data-step-indicator]").forEach((indicator) => {
    const attivo = Number(indicator.dataset.stepIndicator) === numero;
    indicator.classList.toggle("active", attivo);
    if (attivo) indicator.setAttribute("aria-current", "step");
    else indicator.removeAttribute("aria-current");
  });
  $("ingress-error").textContent = "";
  $("ingress-error").classList.remove("success");
}

function aggiornaRiepilogo() {
  const data = $("ingress-data").value;
  const quantitaPerUnita = righeIngresso.reduce((totale, riga) => {
    totale.set(riga.unitaMisura, (totale.get(riga.unitaMisura) || 0) + riga.quantita);
    return totale;
  }, new Map());
  const conteggio = righeIngresso.length;

  $("summary-data").textContent = data
    ? new Date(`${data}T00:00:00`).toLocaleDateString("it-IT")
    : "-";
  $("summary-fornitore").textContent = nomeFornitoreSelezionato();
  $("summary-ddt").textContent = $("ingress-ddt").value.trim() || "-";
  $("summary-conteggio").textContent = String(conteggio);
  $("summary-quantita").textContent = quantitaPerUnita.size
    ? [...quantitaPerUnita].map(([unita, quantita]) =>
      `${new Intl.NumberFormat("it-IT", { maximumFractionDigits: 3 }).format(quantita)} ${unita}`,
    ).join(" · ")
    : "0";
  $("ingress-conteggio").textContent = `${conteggio} ${conteggio === 1 ? "articolo" : "articoli"}`;

  const container = $("ingress-riepilogo-righe");
  container.replaceChildren();
  if (conteggio === 0) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "Nessun articolo aggiunto. Torna agli articoli per iniziare.";
    container.appendChild(empty);
    return;
  }

  righeIngresso.forEach((riga) => {
    const item = document.createElement("div");
    item.className = "ingresso-line";

    const description = document.createElement("div");
    description.className = "ingresso-line-description";
    const name = document.createElement("strong");
    name.textContent = riga.articolo;
    const details = document.createElement("span");
    const metadati = [
      riga.categoria,
      riga.lottoFornitore && `Lotto fornitore: ${riga.lottoFornitore}`,
      riga.origine && `Origine: ${riga.origine}`,
      riga.dataScadenza && `Scadenza: ${new Date(`${riga.dataScadenza}T00:00:00`).toLocaleDateString("it-IT")}`,
      riga.dataTmc && `TMC: ${new Date(`${riga.dataTmc}T00:00:00`).toLocaleDateString("it-IT")}`,
      riga.temperaturaIngresso !== null && `Temperatura: ${riga.temperaturaIngresso} °C`,
      riga.noteLotto && `Note: ${riga.noteLotto}`,
    ].filter(Boolean);
    details.textContent = metadati.join(" · ");
    description.append(name, details);

    const weight = document.createElement("strong");
    weight.className = "ingresso-line-weight";
    weight.textContent = `${new Intl.NumberFormat("it-IT", {
      maximumFractionDigits: 3,
    }).format(riga.quantita)} ${riga.unitaMisura}`;

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "btn danger ingresso-remove-line";
    remove.textContent = "Rimuovi";
    remove.setAttribute("aria-label", `Rimuovi ${riga.articolo} dal riepilogo`);
    remove.addEventListener("click", () => {
      righeIngresso = righeIngresso.filter((itemRow) => itemRow.id !== riga.id);
      $("ingress-error").textContent = "";
      $("ingress-error").classList.remove("success");
      aggiornaRiepilogo();
    });

    item.append(description, weight, remove);
    container.appendChild(item);
  });
}

function renderFornitori() {
  const select = $("ingress-fornitore");
  select.replaceChildren();
  select.disabled = fornitori.length === 0;
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = fornitori.length ? "Seleziona fornitore" : "Nessun fornitore abilitato";
  select.appendChild(placeholder);

  fornitori.forEach((fornitore) => {
    const option = document.createElement("option");
    option.value = String(fornitore.soggetto_id);
    option.textContent = fornitore.azienda;
    select.appendChild(option);
  });
}

function articoliAttivi() {
  return articoli.filter((articolo) => articolo.attivo);
}

function categorieArticoli() {
  const categorie = [...new Set(articoliAttivi().map((articolo) =>
    articolo.categoria?.trim() || "Senza categoria"))];
  const dopoOrdineNoto = ORDINE_CATEGORIE_INGRESSO.length;
  return categorie.sort((a, b) => {
    const indiceA = ORDINE_CATEGORIE_INGRESSO.indexOf(a);
    const indiceB = ORDINE_CATEGORIE_INGRESSO.indexOf(b);
    const pesoA = indiceA === -1 ? dopoOrdineNoto : indiceA;
    const pesoB = indiceB === -1 ? dopoOrdineNoto : indiceB;
    if (pesoA !== pesoB) {
      return pesoA - pesoB;
    }
    return a.localeCompare(b, "it");
  });
}

function renderCategorie() {
  const container = $("ingress-categorie");
  container.replaceChildren();
  const categorie = categorieArticoli();

  if (categorie.length === 0) {
    $("ingress-articoli-feedback").textContent = "Non ci sono articoli attivi disponibili.";
    return;
  }

  categorie.forEach((categoria) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "categoria-button";
    button.textContent = categoria;
    button.setAttribute("aria-pressed", String(categoria === categoriaSelezionata));
    button.addEventListener("click", () => selezionaCategoria(categoria));
    container.appendChild(button);
  });
}

function messaggioFeedbackSelezioneArticoli() {
  if (articoliSelezionati.size === 1) {
    const id = [...articoliSelezionati][0];
    const articolo = articoliAttivi().find((item) => String(item.id) === id);
    if (articolo) {
      return testoConfermaTaglio(articolo.nome);
    }
  }
  if (categoriaSelezionata && categoriaUsaProfiloDisegno(categoriaSelezionata)) {
    return "Seleziona un taglio sul profilo o tra i pezzi fuori profilo.";
  }
  return "Seleziona un articolo da aggiungere.";
}

function cambiaQuartoBovino(quarto) {
  if (quarto === quartoBovino) {
    return;
  }
  quartoBovino = quarto;
  articoliSelezionati.clear();
  renderArticoli();
}

function toggleSelezioneArticolo(id) {
  if (articoliSelezionati.has(id)) {
    articoliSelezionati.delete(id);
  } else {
    articoliSelezionati.clear();
    articoliSelezionati.add(id);
  }
  renderArticoli();
  $("ingress-articoli-feedback").textContent = messaggioFeedbackSelezioneArticoli();
}

function renderArticoli() {
  const container = $("ingress-articoli");
  container.replaceChildren();
  if (!categoriaSelezionata) {
    container.className = "articoli-list";
    $("ingress-articoli-feedback").textContent = "Seleziona una categoria per vedere gli articoli.";
    return;
  }

  const disponibili = articoliAttivi().filter((articolo) =>
    (articolo.categoria?.trim() || "Senza categoria") === categoriaSelezionata);
  if (disponibili.length === 0) {
    container.className = "articoli-list";
    $("ingress-articoli-feedback").textContent = "Nessun articolo attivo in questa categoria.";
    return;
  }

  if (categoriaUsaProfiloDisegno(categoriaSelezionata)) {
    renderArticoliConDisegno(container, {
      categoria: categoriaSelezionata,
      articoliDisponibili: disponibili,
      articoliSelezionati,
      onToggleArticolo: toggleSelezioneArticolo,
      quartoBovino,
      onQuartoBovinoChange: cambiaQuartoBovino,
    });
    $("ingress-articoli-feedback").textContent = messaggioFeedbackSelezioneArticoli();
    return;
  }

  container.className = "articoli-list";
  $("ingress-articoli-feedback").textContent = messaggioFeedbackSelezioneArticoli();
  disponibili.forEach((articolo) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "articolo-button";
    button.textContent = `${articolo.nome} (${articolo.unita_misura})`;
    button.setAttribute("aria-pressed", String(articoliSelezionati.has(String(articolo.id))));
    button.addEventListener("click", () => toggleSelezioneArticolo(String(articolo.id)));
    container.appendChild(button);
  });
}

function selezionaCategoria(categoria) {
  categoriaSelezionata = categoria;
  quartoBovino = "anteriore";
  articoliSelezionati.clear();
  $("ingress-articoli-feedback").textContent = "";
  renderCategorie();
  renderArticoli();
}

async function caricaDatiIngresso() {
  if (datiCaricati) return;
  if (caricamentoDati) return caricamentoDati;

  $("ingress-load-error").textContent = "";
  caricamentoDati = Promise.allSettled([
    api("/api/v1/fornitori"),
    api("/api/v1/articoli"),
  ]).then((results) => {
    const endpoints = ["fornitori", "articoli"];
    const errors = [];
    results.forEach((result, index) => {
      if (result.status === "rejected") {
        const detail = result.reason?.message || String(result.reason || "errore sconosciuto");
        errors.push(`Impossibile caricare ${endpoints[index]}: ${detail}`);
      }
    });
    if (errors.length) $("ingress-load-error").textContent = errors.join(" ");

    if (results[0].status === "fulfilled") {
      fornitori = results[0].value.filter((fornitore) => Number(fornitore.flag1_ing_merce) === 1);
      renderFornitori();
    } else {
      const select = $("ingress-fornitore");
      select.replaceChildren();
      const option = document.createElement("option");
      option.value = "";
      option.textContent = "Errore nel caricamento fornitori";
      select.appendChild(option);
      select.disabled = true;
    }
    if (results[1].status === "fulfilled") articoli = results[1].value;

    if (results[1].status === "fulfilled") {
      renderCategorie();
      renderArticoli();
    }
    datiCaricati = results.every((result) => result.status === "fulfilled");
  }).finally(() => {
    caricamentoDati = null;
  });
  return caricamentoDati;
}

function azzeraCampiArticoloIngresso() {
  categoriaSelezionata = null;
  quartoBovino = "anteriore";
  articoliSelezionati.clear();
  $("ingress-quantita").value = "";
  $("ingress-lotto-fornitore").value = "";
  $("ingress-origine").value = "";
  $("ingress-note-lotto").value = "";
  $("ingress-tipo-data").value = "";
  $("ingress-data-lotto").value = "";
  $("ingress-temperatura").value = "";
  renderCategorie();
  renderArticoli();
}

function aggiungiRighe() {
  const inputQuantita = $("ingress-quantita");
  const quantita = inputQuantita.valueAsNumber;
  if (!categoriaSelezionata) {
    $("ingress-articoli-feedback").textContent = "Seleziona prima una categoria.";
    return;
  }
  if (articoliSelezionati.size === 0) {
    $("ingress-articoli-feedback").textContent = "Seleziona almeno un articolo.";
    return;
  }
  if (!Number.isFinite(quantita) || !inputQuantita.checkValidity()) {
    $("ingress-articoli-feedback").textContent =
      "Inserisci una quantità valida, da 0,001 a 999.999.999,999, con massimo 3 decimali.";
    inputQuantita.focus();
    return;
  }

  const inputTemperatura = $("ingress-temperatura");
  if (!inputTemperatura.checkValidity()) {
    $("ingress-articoli-feedback").textContent =
      "Inserisci una temperatura compresa tra -100 e 100 °C, con massimo 2 decimali.";
    inputTemperatura.focus();
    return;
  }
  const lottoFornitore = $("ingress-lotto-fornitore").value.trim();
  const origine = $("ingress-origine").value.trim();
  const noteLotto = $("ingress-note-lotto").value.trim();
  const tipoData = $("ingress-tipo-data").value;
  const dataLotto = $("ingress-data-lotto").value;
  if (tipoData && !dataLotto) {
    $("ingress-articoli-feedback").textContent = "Inserisci la data indicata dal fornitore.";
    $("ingress-data-lotto").focus();
    return;
  }
  const temperaturaIngresso = inputTemperatura.value === ""
    ? null
    : Number(inputTemperatura.value).toFixed(2);

  const selezionati = articoliAttivi().filter((articolo) =>
    articoliSelezionati.has(String(articolo.id)));
  selezionati.forEach((articolo) => {
    righeIngresso.push({
      id: prossimoIdRiga++,
      articoloId: articolo.id,
      articolo: articolo.nome,
      categoria: articolo.categoria?.trim() || "Senza categoria",
      unitaMisura: articolo.unita_misura,
      quantita,
      lottoFornitore: lottoFornitore || null,
      origine: origine || null,
      noteLotto: noteLotto || null,
      dataScadenza: tipoData === "scadenza" ? dataLotto : null,
      dataTmc: tipoData === "tmc" ? dataLotto : null,
      temperaturaIngresso,
    });
  });
  const messaggioAggiunta = `${selezionati.length} ${selezionati.length === 1 ? "articolo aggiunto" : "articoli aggiunti"} al riepilogo.`;
  azzeraCampiArticoloIngresso();
  $("ingress-error").textContent = "";
  $("ingress-error").classList.remove("success");
  aggiornaRiepilogo();
  $("ingress-articoli-feedback").textContent = messaggioAggiunta;
}

function pulisciErroreIntestazione() {
  $("ingress-header-error").textContent = "";
}

async function documentoGiaRegistrato() {
  const params = new URLSearchParams({
    data: $("ingress-data").value,
    fornitore_id: $("ingress-fornitore").value,
    numero_ddt: $("ingress-ddt").value.trim(),
  });
  const risposta = await api(`/api/v1/tracciabilita/ingressi/duplicato?${params}`);
  return Boolean(risposta.duplicato);
}

function azzeraIngresso() {
  $("ingress-fornitore").value = "";
  $("ingress-data").value = dataLocaleISO();
  $("ingress-ddt").value = "";
  azzeraCampiArticoloIngresso();
  righeIngresso = [];
  prossimoIdRiga = 1;
  $("btn-salva-ingresso").disabled = false;
  $("ingress-success").textContent = "";
  $("ingress-success").classList.remove("success");
  $("ingress-error").textContent = "";
  $("ingress-articoli-feedback").textContent = "";
  pulisciErroreIntestazione();
  mostraStep(1);
  aggiornaRiepilogo();
}

export function openIngressoMerce() {
  document.querySelectorAll(".panel").forEach((panel) => panel.classList.remove("active"));
  $("view-ingresso-merce").classList.add("active");
  document.querySelectorAll(".nav-item").forEach((button) =>
    button.classList.toggle("active", button.dataset.view === "ingresso-merce"));
  if (!$("ingress-data").value) $("ingress-data").value = dataLocaleISO();
  aggiornaRiepilogo();
  caricaDatiIngresso();
}

async function selezionaArticoloDaScanner(codice) {
  await caricaDatiIngresso();
  let articolo = articoliAttivi().find((item) => String(item.ean || "") === codice);
  if (!articolo) {
    try {
      const remoto = await api("/api/v1/articoli/ean/" + encodeURIComponent(codice));
      articolo = articoliAttivi().find((item) => String(item.id) === String(remoto.id));
    } catch (error) {
      articolo = null;
    }
  }
  mostraStep(2);
  if (!articolo) {
    $("ingress-articoli-feedback").textContent = "Nessun articolo attivo con questo codice a barre.";
    return;
  }
  categoriaSelezionata = articolo.categoria?.trim() || "Senza categoria";
  if (categoriaSelezionata === "Bovino") {
    const quarto = quartoBovinoPerCodice(articolo.codice);
    if (quarto) {
      quartoBovino = quarto;
    }
  } else {
    quartoBovino = "anteriore";
  }
  articoliSelezionati.clear();
  articoliSelezionati.add(String(articolo.id));
  renderCategorie();
  renderArticoli();
  $("ingress-articoli-feedback").textContent = testoConfermaTaglio(articolo.nome);
  $("ingress-quantita").focus();
}

export function initIngressoMerce() {
  registraScanner((codice) => {
    if (!$("view-ingresso-merce").classList.contains("active")) return false;
    selezionaArticoloDaScanner(codice);
    return true;
  });
  $("btn-reset-ingresso").addEventListener("click", azzeraIngresso);
  $("btn-ingresso-step-1").addEventListener("click", async () => {
    pulisciErroreIntestazione();
    if (!$("ingress-fornitore").value) {
      $("ingress-header-error").textContent = "Seleziona un fornitore prima di continuare.";
      $("ingress-fornitore").focus();
      return;
    }
    const button = $("btn-ingresso-step-1");
    button.disabled = true;
    try {
      if (await documentoGiaRegistrato()) {
        $("ingress-header-error").textContent = MESSAGGIO_DOCUMENTO_DUPLICATO;
        $("ingress-ddt").focus();
        return;
      }
      mostraStep(2);
    } catch (error) {
      $("ingress-header-error").textContent =
        `Impossibile verificare il documento: ${error.message}`;
    } finally {
      button.disabled = false;
    }
  });
  $("btn-aggiungi-ingresso").addEventListener("click", aggiungiRighe);
  $("btn-ingresso-step-2").addEventListener("click", () => {
    if (righeIngresso.length === 0) {
      $("ingress-articoli-feedback").textContent = "Aggiungi almeno un articolo prima di continuare.";
      return;
    }
    aggiornaRiepilogo();
    mostraStep(3);
  });
  $("view-ingresso-merce").querySelectorAll("[data-step-back]").forEach((button) => {
    button.addEventListener("click", () => mostraStep(Number(button.dataset.stepBack)));
  });
  $("ingress-data").addEventListener("change", () => {
    pulisciErroreIntestazione();
    aggiornaRiepilogo();
  });
  $("ingress-fornitore").addEventListener("change", () => {
    pulisciErroreIntestazione();
    aggiornaRiepilogo();
  });
  $("ingress-ddt").addEventListener("input", () => {
    pulisciErroreIntestazione();
    aggiornaRiepilogo();
  });

  $("btn-salva-ingresso").addEventListener("click", async () => {
    if (!$("ingress-fornitore").value || righeIngresso.length === 0) {
      $("ingress-error").classList.remove("success");
      $("ingress-error").textContent = "Completa l'intestazione e aggiungi almeno un articolo.";
      return;
    }
    const button = $("btn-salva-ingresso");
    button.disabled = true;
    $("ingress-error").classList.remove("success");
    $("ingress-error").textContent = "Verifica documento in corso…";
    try {
      if (await documentoGiaRegistrato()) {
        button.disabled = false;
        $("ingress-error").textContent = MESSAGGIO_DOCUMENTO_DUPLICATO;
        return;
      }
      $("ingress-error").textContent = "Salvataggio ingresso in corso…";
      const response = await api("/api/v1/tracciabilita/ingressi", {
        method: "POST",
        body: JSON.stringify({
          data: $("ingress-data").value,
          numero_ddt: $("ingress-ddt").value.trim(),
          fornitore_id: Number($("ingress-fornitore").value),
          righe: righeIngresso.map((riga) => ({
            articolo_id: Number(riga.articoloId),
            quantita: riga.quantita.toFixed(3),
            lotto_fornitore: riga.lottoFornitore,
            origine: riga.origine,
            note_lotto: riga.noteLotto,
            data_scadenza: riga.dataScadenza,
            data_tmc: riga.dataTmc,
            temperatura_ingresso: riga.temperaturaIngresso,
          })),
        }),
      });
      const codiciLotto = response.lotti.map((lotto) => lotto.codice_lotto).join(", ");
      azzeraIngresso();
      $("ingress-success").classList.add("success");
      $("ingress-success").textContent =
        `Ingresso registrato. Lotti creati: ${codiciLotto}.`;
    } catch (error) {
      button.disabled = false;
      $("ingress-error").textContent = `Impossibile salvare l'ingresso: ${error.message}`;
    }
  });
  $("ingress-data").value = dataLocaleISO();
  $("ingress-fornitore").disabled = true;
  aggiornaRiepilogo();
  renderCategorie();
  renderArticoli();
}
