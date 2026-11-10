import { api } from "../api/client.js";
import { $ } from "../core/dom.js";

let lottiVendita = [];
let clientiVendita = [];
let righeVendita = [];
let registrazioneInCorso = false;

function dataLocaleISO() {
  const oggi = new Date();
  return `${oggi.getFullYear()}-${String(oggi.getMonth() + 1).padStart(2, "0")}-${String(oggi.getDate()).padStart(2, "0")}`;
}

function creaOpzione(value, label) {
  const option = document.createElement("option");
  option.value = String(value);
  option.textContent = label;
  return option;
}

function formattaData(value) {
  if (!value) return "senza scadenza";
  const data = String(value).slice(0, 10);
  const parsed = new Date(`${data}T00:00:00`);
  return Number.isNaN(parsed.getTime()) ? data : parsed.toLocaleDateString("it-IT");
}

function formattaQuantitaMilli(value, unita) {
  const quantita = Number(value) / 1000;
  return `${new Intl.NumberFormat("it-IT", { minimumFractionDigits: 3, maximumFractionDigits: 3 }).format(quantita)} ${unita ?? ""}`.trim();
}

function formattaImporto(centesimi) {
  return new Intl.NumberFormat("it-IT", {
    style: "currency",
    currency: "EUR",
  }).format(centesimi / 100);
}

function lottiPerArticolo(articoloId) {
  return lottiVendita.filter((lotto) => String(lotto.articolo_id) === String(articoloId));
}

function lottoSelezionato() {
  return lottiPerArticolo($("sales-article").value)
    .find((item) => String(item.id) === $("sales-lot").value);
}

function prezzoInCentesimi(lotto) {
  const prezzo = Number(lotto?.prezzo_unitario);
  return Number.isFinite(prezzo) && prezzo >= 0 ? Math.round(prezzo * 100) : null;
}

function aggiornaPulsanteAggiungi() {
  const lotto = lottoSelezionato();
  const inputQuantita = $("sales-quantity");
  const quantita = inputQuantita.valueAsNumber;
  const disponibili = Number(lotto?.quantita_disponibile);
  const prezzo = prezzoInCentesimi(lotto);
  $("btn-add-sales-line").disabled = registrazioneInCorso
    || !lotto
    || prezzo === null
    || inputQuantita.validity.stepMismatch
    || !Number.isFinite(quantita)
    || quantita <= 0
    || quantita > disponibili;
}

function aggiornaRiepilogo() {
  const lotto = lottoSelezionato();
  const dataLotto = lotto?.data_scadenza || lotto?.data_tmc;
  const tipoData = lotto?.data_scadenza ? "Scadenza" : lotto?.data_tmc ? "TMC" : "Data";
  const tmcSuperato = lotto?.data_tmc
    && String(lotto.data_tmc).slice(0, 10) < dataLocaleISO();
  const prezzo = prezzoInCentesimi(lotto);

  $("sales-lot-summary").textContent = lotto
    ? `Disponibili: ${new Intl.NumberFormat("it-IT", { maximumFractionDigits: 3 }).format(Number(lotto.quantita_disponibile))} ${lotto.unita_misura} · ${tipoData}: ${formattaData(dataLotto)}${tmcSuperato ? " · TMC superato: richiede conferma" : ""}`
    : "";
  $("sales-price").value = prezzo === null
    ? "Prezzo non configurato"
    : `${formattaImporto(prezzo)} / ${lotto.unita_misura}`;
  $("sales-quantity").max = lotto?.quantita_disponibile ?? "";
  aggiornaPulsanteAggiungi();
}

function aggiornaLotti(articoloId, lottoPreferito = "") {
  const selettoreLotto = $("sales-lot");
  const lotti = lottiPerArticolo(articoloId);
  selettoreLotto.replaceChildren(creaOpzione("", lotti.length ? "Seleziona lotto" : "Nessun lotto disponibile"));

  lotti.forEach((lotto, index) => {
    const dataLotto = lotto.data_scadenza || lotto.data_tmc;
    const tipoData = lotto.data_scadenza ? "scadenza" : lotto.data_tmc ? "TMC" : "data";
    const precedenza = index === 0 ? "FEFO · " : "";
    selettoreLotto.appendChild(creaOpzione(
      lotto.id,
      `${precedenza}${lotto.codice_lotto} · disponibili ${new Intl.NumberFormat("it-IT", { maximumFractionDigits: 3 }).format(Number(lotto.quantita_disponibile))} ${lotto.unita_misura} · ${tipoData} ${formattaData(dataLotto)}`,
    ));
  });

  const lottoSelezionatoId = lotti.some((lotto) => String(lotto.id) === String(lottoPreferito))
    ? String(lottoPreferito)
    : String(lotti[0]?.id ?? "");
  selettoreLotto.value = lottoSelezionatoId;
  selettoreLotto.disabled = lotti.length === 0;
  aggiornaRiepilogo();
}

function articoliDisponibili() {
  const articoli = new Map();
  lottiVendita.forEach((lotto) => {
    if (!articoli.has(String(lotto.articolo_id))) {
      articoli.set(String(lotto.articolo_id), lotto.articolo);
    }
  });
  return articoli;
}

function aggiornaArticoli(articoloPreferito = $("sales-article").value) {
  const selettoreArticolo = $("sales-article");
  const articoli = articoliDisponibili();
  const ricerca = $("sales-search").value.trim().toLocaleLowerCase("it-IT");
  const filtrati = [...articoli.entries()].filter(([, nome]) =>
    String(nome).toLocaleLowerCase("it-IT").includes(ricerca));

  selettoreArticolo.replaceChildren(creaOpzione("", filtrati.length ? "Seleziona articolo" : "Nessun articolo trovato"));
  filtrati.forEach(([id, nome]) => selettoreArticolo.appendChild(creaOpzione(id, nome)));

  const selezione = filtrati.some(([id]) => id === String(articoloPreferito))
    ? String(articoloPreferito)
    : String(filtrati[0]?.[0] ?? "");
  selettoreArticolo.value = selezione;
  selettoreArticolo.disabled = filtrati.length === 0;
  aggiornaLotti(selezione);
}

function aggiornaClienti() {
  const selettore = $("sales-customer");
  const selezionePrecedente = selettore.value;
  const clienti = clientiVendita.filter((soggetto) => soggetto.attivo && soggetto.ruolo_cliente);
  selettore.replaceChildren(creaOpzione("", "Banco / cliente non indicato"));
  clienti.forEach((cliente) => selettore.appendChild(creaOpzione(cliente.id, cliente.denominazione)));
  if (clienti.some((cliente) => String(cliente.id) === selezionePrecedente)) {
    selettore.value = selezionePrecedente;
  }
}

function aggiornaTotale() {
  const totale = righeVendita.reduce((sum, riga) => sum + riga.importoCentesimi, 0);
  $("sales-total").textContent = formattaImporto(totale);
  $("btn-register-sales").disabled = registrazioneInCorso || righeVendita.length === 0;
}

function renderCarrello() {
  const tbody = $("sales-cart-body");
  tbody.replaceChildren();

  if (!righeVendita.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 5;
    cell.className = "empty";
    cell.textContent = "Nessun articolo aggiunto";
    row.appendChild(cell);
    tbody.appendChild(row);
    aggiornaTotale();
    return;
  }

  righeVendita.forEach((riga, index) => {
    const row = document.createElement("tr");
    const articolo = document.createElement("td");
    articolo.textContent = `${riga.articolo} · lotto ${riga.codiceLotto}`;
    const quantita = document.createElement("td");
    quantita.textContent = formattaQuantitaMilli(riga.quantitaMilli, riga.unita);
    const prezzo = document.createElement("td");
    prezzo.textContent = `${formattaImporto(riga.prezzoCentesimi)} / ${riga.unita}`;
    const importo = document.createElement("td");
    importo.textContent = formattaImporto(riga.importoCentesimi);
    const azioni = document.createElement("td");
    const rimuovi = document.createElement("button");
    rimuovi.type = "button";
    rimuovi.className = "btn danger sales-line-remove";
    rimuovi.dataset.index = String(index);
    rimuovi.textContent = "Rimuovi";
    rimuovi.setAttribute("aria-label", `Rimuovi ${riga.articolo}`);
    azioni.appendChild(rimuovi);
    row.append(articolo, quantita, prezzo, importo, azioni);
    tbody.appendChild(row);
  });
  aggiornaTotale();
}

function aggiungiRiga() {
  const lotto = lottoSelezionato();
  const inputQuantita = $("sales-quantity");
  const quantita = inputQuantita.valueAsNumber;
  const prezzoCentesimi = prezzoInCentesimi(lotto);
  const errore = $("sales-selection-error");
  errore.textContent = "";

  if (!lotto || prezzoCentesimi === null) {
    errore.textContent = "Seleziona un lotto con prezzo commerciale configurato.";
    return;
  }
  if (!Number.isFinite(quantita)
    || quantita <= 0
    || inputQuantita.validity.stepMismatch
    || quantita > Number(lotto.quantita_disponibile)) {
    errore.textContent = "Inserisci una quantità valida, non superiore alla disponibilità del lotto.";
    return;
  }

  if (lotto.data_tmc
    && String(lotto.data_tmc).slice(0, 10) < dataLocaleISO()
    && !window.confirm("Il TMC del lotto è superato. Vuoi confermare la vendita?")) {
    return;
  }

  const quantitaMilli = Math.round(quantita * 1000);
  righeVendita.push({
    articolo: lotto.articolo,
    articoloId: Number(lotto.articolo_id),
    codiceLotto: lotto.codice_lotto,
    lottoId: Number(lotto.id),
    quantitaMilli,
    prezzoCentesimi,
    importoCentesimi: Math.round((quantitaMilli * prezzoCentesimi) / 1000),
    unita: lotto.unita_misura,
  });
  $("sales-quantity").value = "";
  $("sales-checkout-status").textContent = "";
  $("sales-checkout-error").textContent = "";
  renderCarrello();
  aggiornaPulsanteAggiungi();
}

function quantitaApi(quantitaMilli) {
  return `${Math.floor(quantitaMilli / 1000)}.${String(quantitaMilli % 1000).padStart(3, "0")}`;
}

async function registraVendita() {
  if (registrazioneInCorso || righeVendita.length === 0) return;
  registrazioneInCorso = true;
  $("btn-register-sales").disabled = true;
  $("btn-add-sales-line").disabled = true;
  $("sales-checkout-error").textContent = "";
  $("sales-checkout-status").className = "sales-checkout-status";
  $("sales-checkout-status").textContent = "Registrazione vendita…";

  const righe = righeVendita.map((riga) => ({
    lotto_id: riga.lottoId,
    articolo_id: riga.articoloId,
    quantita: quantitaApi(riga.quantitaMilli),
    unita_misura: riga.unita,
    prezzo_unitario: (riga.prezzoCentesimi / 100).toFixed(2),
    iva_percentuale: "0.00",
  }));
  const totale = righeVendita.reduce((sum, riga) => sum + riga.importoCentesimi, 0);
  const clienteId = $("sales-customer").value;
  let vendita;

  try {
    vendita = await api("/api/v1/vendite/complete", {
      method: "POST",
      body: JSON.stringify({
        data: dataLocaleISO(),
        cliente_id: clienteId ? Number(clienteId) : null,
        tipo_documento: "RICEVUTA",
        righe,
      }),
    });
  } catch (error) {
    $("sales-checkout-status").className = "error";
    $("sales-checkout-status").textContent = "";
    $("sales-checkout-error").textContent = `Vendita non registrata: ${error.message}`;
    registrazioneInCorso = false;
    aggiornaTotale();
    aggiornaPulsanteAggiungi();
    return;
  }

  const righeScontrino = righeVendita.map((riga) => ({
    descrizione: `${riga.articolo} · lotto ${riga.codiceLotto}`,
    prezzo: `${formattaImporto(riga.prezzoCentesimi)} / ${riga.unita}`,
    qta: formattaQuantitaMilli(riga.quantitaMilli, riga.unita),
  }));
  righeVendita = [];
  renderCarrello();

  try {
    await api("/api/v1/print-jobs", {
      method: "POST",
      body: JSON.stringify({
        tipo: "scontrino",
        payload: JSON.stringify({
          testata: `GestLab · RICEVUTA NON FISCALE #${vendita.numero}\nDocumento non fiscale — non sostituisce lo scontrino del registratore telematico`,
          righe: righeScontrino,
          totale: formattaImporto(totale),
          iva: "0,00 €",
        }),
      }),
    });
    $("sales-checkout-status").className = "error success";
    $("sales-checkout-status").textContent = `Vendita #${vendita.numero} registrata. Ricevuta inviata alla coda di stampa.`;
  } catch (error) {
    $("sales-checkout-status").className = "error";
    $("sales-checkout-status").textContent = `Vendita #${vendita.numero} registrata, ma la stampa non è stata accodata: ${error.message}. Puoi controllare la Coda stampa.`;
  } finally {
    registrazioneInCorso = false;
    aggiornaTotale();
    aggiornaPulsanteAggiungi();
    await loadVendite();
  }
}

export async function loadVendite() {
  const articoloSelezionato = $("sales-article").value;
  const lottoSelezionatoId = $("sales-lot").value;
  $("sales-selection-error").textContent = "";
  $("sales-article").disabled = true;
  $("sales-lot").disabled = true;

  try {
    const lotti = await api("/api/v1/vendite/lotti-disponibili");
    if (!Array.isArray(lotti)) {
      throw new Error("La risposta dei lotti disponibili non è valida.");
    }
    lottiVendita = lotti;
    aggiornaArticoli(articoloSelezionato);
    if (articoloSelezionato === $("sales-article").value) {
      aggiornaLotti(articoloSelezionato, lottoSelezionatoId);
    }
  } catch (error) {
    lottiVendita = [];
    aggiornaArticoli();
    $("sales-selection-error").textContent = `Impossibile caricare i lotti disponibili: ${error.message}`;
    return;
  }

  try {
    const soggetti = await api("/api/v1/soggetti");
    clientiVendita = Array.isArray(soggetti) ? soggetti : [];
    aggiornaClienti();
  } catch (error) {
    clientiVendita = [];
    aggiornaClienti();
    $("sales-selection-error").textContent = `Impossibile caricare i clienti; puoi comunque registrare una vendita al banco. ${error.message}`;
  }
}

export function initVendite() {
  $("sales-search").addEventListener("input", () => aggiornaArticoli());
  $("sales-article").addEventListener("change", (event) => {
    aggiornaLotti(event.target.value);
  });
  $("sales-lot").addEventListener("change", aggiornaRiepilogo);
  $("sales-quantity").addEventListener("input", aggiornaPulsanteAggiungi);
  $("btn-add-sales-line").addEventListener("click", aggiungiRiga);
  $("btn-refresh-sales-lots").addEventListener("click", loadVendite);
  $("sales-cart-body").addEventListener("click", (event) => {
    const button = event.target.closest("[data-index]");
    if (!button) return;
    righeVendita.splice(Number(button.dataset.index), 1);
    renderCarrello();
  });
  $("btn-register-sales").addEventListener("click", registraVendita);
}
