import { api } from "../api/client.js";
import { accodaRicevuta, scaricaDdt } from "./report.js?v=20261128-2";
import { $ } from "../core/dom.js";
import { registraScanner } from "../core/scanner.js?v=20261121-5";

let lottiVendita = [];
let listinoVendita = [];
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

function prezzoAnagrafica(lotto) {
  const grezzo = lotto?.prezzo_unitario;
  if (grezzo === null || grezzo === undefined || grezzo === "") return null;
  const prezzo = Number(grezzo);
  return Number.isFinite(prezzo) && prezzo >= 0 ? prezzo : null;
}

function prezzoDigitatoCentesimi() {
  const input = $("sales-price");
  if (input.disabled || input.validity.badInput || input.validity.stepMismatch || input.validity.rangeUnderflow) {
    return null;
  }
  const prezzo = input.valueAsNumber;
  if (!Number.isFinite(prezzo) || prezzo <= 0) return null;
  return Math.round(prezzo * 100);
}

function applicaPrezzoLotto(lotto) {
  const input = $("sales-price");
  const nota = $("sales-price-note");
  if (!lotto) {
    input.value = "";
    input.disabled = true;
    $("sales-price-label").textContent = "Prezzo unitario";
    nota.hidden = true;
    nota.textContent = "";
    return;
  }
  input.disabled = false;
  const unita = lotto.unita_misura ? ` (€ / ${lotto.unita_misura})` : " (€)";
  $("sales-price-label").textContent = `Prezzo unitario${unita}`;
  const catalogo = prezzoAnagrafica(lotto);
  if (catalogo === null || catalogo === 0) {
    input.value = "";
    nota.hidden = false;
    nota.textContent = catalogo === 0
      ? "In anagrafica il prezzo è 0,00 €. Inserisci il prezzo di questa vendita."
      : "Prezzo non in anagrafica. Inserisci il prezzo di questa vendita.";
    return;
  }
  input.value = catalogo.toFixed(2);
  nota.hidden = true;
  nota.textContent = "";
}

function aggiornaPulsanteAggiungi() {
  const lotto = lottoSelezionato();
  const inputQuantita = $("sales-quantity");
  const quantita = inputQuantita.valueAsNumber;
  const disponibili = Number(lotto?.quantita_disponibile);
  const prezzo = prezzoDigitatoCentesimi();
  const errore = $("sales-selection-error");
  const quantitaSuperaDisponibilita = Boolean(lotto)
    && Number.isFinite(quantita)
    && quantita > 0
    && quantita > disponibili;

  $("btn-add-sales-line").disabled = registrazioneInCorso
    || !lotto
    || prezzo === null
    || inputQuantita.validity.stepMismatch
    || !Number.isFinite(quantita)
    || quantita <= 0
    || quantita > disponibili;

  if (quantitaSuperaDisponibilita) {
    const unita = lotto.unita_misura ?? "";
    const disponibilita = new Intl.NumberFormat("it-IT", { maximumFractionDigits: 3 }).format(disponibili);
    errore.textContent = `La quantità supera la disponibilità del lotto (massimo ${disponibilita} ${unita}).`.trim();
    return;
  }
  if (inputQuantita.validity.stepMismatch && Number.isFinite(quantita) && quantita > 0) {
    errore.textContent = "Inserisci una quantità valida, con al massimo 3 decimali.";
    return;
  }
  if (lotto && prezzo !== null && Number.isFinite(quantita) && quantita > 0 && quantita <= disponibili) {
    errore.textContent = "";
  }
}

function aggiornaRiepilogo() {
  const lotto = lottoSelezionato();
  if (!lotto) {
    $("sales-lot-summary").textContent = $("sales-article").value
      ? "Nessun lotto disponibile per questo articolo"
      : "";
    applicaPrezzoLotto(null);
    $("sales-quantity").max = "";
    aggiornaPulsanteAggiungi();
    return;
  }
  const dataLotto = lotto?.data_scadenza || lotto?.data_tmc;
  const tipoData = lotto?.data_scadenza ? "Scadenza" : lotto?.data_tmc ? "TMC" : "Data";
  const tmcSuperato = lotto?.data_tmc
    && String(lotto.data_tmc).slice(0, 10) < dataLocaleISO();

  $("sales-lot-summary").textContent = lotto
    ? `Disponibili: ${new Intl.NumberFormat("it-IT", { maximumFractionDigits: 3 }).format(Number(lotto.quantita_disponibile))} ${lotto.unita_misura} · ${tipoData}: ${formattaData(dataLotto)}${tmcSuperato ? " · TMC superato: richiede conferma" : ""}`
    : "";
  applicaPrezzoLotto(lotto);
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
  const soloDisponibili = $("sales-only-available").checked;
  const articoli = new Map();
  listinoVendita.forEach((articolo) => {
    if (soloDisponibili && !articolo.disponibile) return;
    articoli.set(String(articolo.id), {
      nome: articolo.nome,
      categoria: articolo.categoria?.trim() || "",
    });
  });
  return articoli;
}

function aggiornaArticoli(articoloPreferito = $("sales-article").value, autoSelezionaPrimo = true) {
  const selettoreArticolo = $("sales-article");
  const articoli = articoliDisponibili();
  const ricerca = $("sales-search").value.trim().toLocaleLowerCase("it-IT");
  const filtrati = [...articoli.entries()].filter(([, articolo]) =>
    `${articolo.nome} ${articolo.categoria}`.toLocaleLowerCase("it-IT").includes(ricerca));

  selettoreArticolo.replaceChildren(creaOpzione("", filtrati.length ? "Seleziona articolo" : "Nessun articolo trovato"));
  filtrati.forEach(([id, articolo]) => {
    const etichetta = articolo.categoria
      ? `${articolo.nome} · ${articolo.categoria}`
      : articolo.nome;
    selettoreArticolo.appendChild(creaOpzione(id, etichetta));
  });

  const preferitoValido = filtrati.some(([id]) => id === String(articoloPreferito))
    ? String(articoloPreferito)
    : "";
  const selezione = autoSelezionaPrimo
    ? (preferitoValido || String(filtrati[0]?.[0] ?? ""))
    : preferitoValido;
  selettoreArticolo.value = selezione;
  selettoreArticolo.disabled = filtrati.length === 0;
  aggiornaLotti(selezione);
}

function azzeraCampiArticoloVendita() {
  $("sales-search").value = "";
  $("sales-quantity").value = "";
  aggiornaArticoli("", false);
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

function etichettaCliente() {
  const select = $("sales-customer");
  if (!select.value) return "Banco";
  return select.options[select.selectedIndex]?.textContent || "Banco";
}

function etichettaDocumento() {
  const select = $("sales-document-type");
  return select.options[select.selectedIndex]?.textContent || select.value;
}

function formattaDataVendita(value) {
  if (!value) return "—";
  const parsed = new Date(`${String(value).slice(0, 10)}T00:00:00`);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleDateString("it-IT");
}

function aggiornaTotale() {
  const totale = righeVendita.reduce((sum, riga) => sum + riga.importoCentesimi, 0);
  $("sales-total").textContent = formattaImporto(totale);
  $("sales-summary-count").textContent = String(righeVendita.length);
  $("sales-summary-date").textContent = formattaDataVendita($("sales-date").value);
  $("sales-summary-customer").textContent = etichettaCliente();
  $("sales-summary-document").textContent = etichettaDocumento();
  $("btn-register-sales").disabled = registrazioneInCorso || righeVendita.length === 0;
}

function passoArticoliVisibile() {
  const passo = $("view-vendite").querySelector('.ingresso-step[data-step="2"]');
  return Boolean(passo && !passo.hidden);
}

function mostraStep(numero) {
  const pannello = $("view-vendite");
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
  $("sales-checkout-error").textContent = "";
  $("sales-checkout-status").textContent = "";
  $("sales-checkout-status").className = "sales-checkout-status";
  if (numero === 3) renderCarrello();
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
  const prezzoCentesimi = prezzoDigitatoCentesimi();
  const errore = $("sales-selection-error");
  errore.textContent = "";

  if (!lotto) {
    errore.textContent = "Seleziona un lotto.";
    return;
  }
  if (prezzoCentesimi === null) {
    errore.textContent = "Inserisci il prezzo unitario di questa vendita.";
    $("sales-price").focus();
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
  azzeraCampiArticoloVendita();
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
  const tipoDocumento = $("sales-document-type").value;
  const clienteId = $("sales-customer").value;
  if (tipoDocumento === "DDT" && !clienteId) {
    $("sales-checkout-error").textContent = "Per un DDT seleziona un cliente.";
    $("sales-checkout-status").textContent = "";
    return;
  }

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
  let vendita;

  try {
    vendita = await api("/api/v1/vendite/complete", {
      method: "POST",
      body: JSON.stringify({
        data: $("sales-date").value || dataLocaleISO(),
        cliente_id: clienteId ? Number(clienteId) : null,
        tipo_documento: tipoDocumento,
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

  righeVendita = [];
  let esitoClasse = "error success";
  let esitoTesto = "";

  try {
    if (tipoDocumento === "DDT") {
      try {
        await scaricaDdt(vendita.id, null, vendita.numero);
        esitoTesto = `Vendita #${vendita.numero} registrata. DDT scaricato; puoi ristamparlo da Report.`;
      } catch (error) {
        esitoClasse = "error";
        esitoTesto = `Vendita #${vendita.numero} registrata, ma il DDT non è stato generato: ${error.message}. Puoi riprovare da Report.`;
      }
    } else {
      try {
        await accodaRicevuta(vendita.id);
        esitoTesto = `Vendita #${vendita.numero} registrata. Ricevuta non fiscale inviata al Local Print Agent.`;
      } catch (error) {
        esitoClasse = "error";
        esitoTesto = `Vendita #${vendita.numero} registrata, ma la ricevuta non è stata accodata: ${error.message}. Puoi riprovare da Report.`;
      }
    }
  } finally {
    registrazioneInCorso = false;
    $("sales-date").value = dataLocaleISO();
    renderCarrello();
    mostraStep(1);
    $("sales-result").className = esitoClasse;
    $("sales-result").textContent = esitoTesto;
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
    const [lotti, articoli] = await Promise.all([
      api("/api/v1/vendite/lotti-disponibili"),
      api("/api/v1/menu?solo_disponibili=false"),
    ]);
    if (!Array.isArray(lotti) || !Array.isArray(articoli)) {
      throw new Error("La risposta del listino o dei lotti disponibili non è valida.");
    }
    lottiVendita = lotti;
    listinoVendita = articoli;
    aggiornaArticoli(articoloSelezionato);
    if (articoloSelezionato === $("sales-article").value) {
      aggiornaLotti(articoloSelezionato, lottoSelezionatoId);
    }
  } catch (error) {
    lottiVendita = [];
    listinoVendita = [];
    aggiornaArticoli();
    $("sales-selection-error").textContent = `Impossibile caricare il listino: ${error.message}`;
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

async function selezionaArticoloDaScanner(codice) {
  if (!listinoVendita.length) await loadVendite();
  let articoloId = "";
  try {
    const remoto = await api("/api/v1/articoli/ean/" + encodeURIComponent(codice));
    articoloId = String(remoto.id);
  } catch (error) {
    $("sales-selection-error").textContent = "Nessun articolo con questo codice a barre.";
    return;
  }
  const articolo = listinoVendita.find((item) => String(item.id) === articoloId);
  if (!articolo) {
    $("sales-selection-error").textContent = "Articolo trovato, ma non è nel listino di vendita.";
    return;
  }
  if ($("sales-only-available").checked && !articolo.disponibile) {
    $("sales-only-available").checked = false;
  }
  $("sales-search").value = "";
  aggiornaArticoli(articoloId);
  $("sales-selection-error").textContent = "";
  if ($("sales-price").value === "") $("sales-price").focus();
  else $("sales-quantity").focus();
}

export function initVendite() {
  $("sales-date").value = dataLocaleISO();
  registraScanner((codice) => {
    if (!$("view-vendite").classList.contains("active") || !passoArticoliVisibile()) return false;
    selezionaArticoloDaScanner(codice);
    return true;
  });
  $("btn-sales-step-1").addEventListener("click", () => {
    if ($("sales-document-type").value === "DDT" && !$("sales-customer").value) {
      $("sales-header-error").textContent = "Per un DDT seleziona un cliente.";
      $("sales-customer").focus();
      return;
    }
    $("sales-header-error").textContent = "";
    mostraStep(2);
  });
  $("btn-sales-step-2").addEventListener("click", () => {
    if (righeVendita.length === 0) {
      $("sales-selection-error").textContent = "Aggiungi almeno un articolo prima di continuare.";
      return;
    }
    $("sales-selection-error").textContent = "";
    mostraStep(3);
  });
  $("view-vendite").querySelectorAll("[data-step-back]").forEach((button) => {
    button.addEventListener("click", () => mostraStep(Number(button.dataset.stepBack)));
  });
  $("sales-search").addEventListener("input", () => aggiornaArticoli());
  $("sales-only-available").addEventListener("change", () => aggiornaArticoli());
  $("sales-article").addEventListener("change", (event) => {
    aggiornaLotti(event.target.value);
  });
  $("sales-lot").addEventListener("change", aggiornaRiepilogo);
  $("sales-quantity").addEventListener("input", aggiornaPulsanteAggiungi);
  $("sales-price").addEventListener("input", aggiornaPulsanteAggiungi);
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
