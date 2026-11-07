import { api } from "../api/client.js";
import { $ } from "../core/dom.js";

let lottiVendita = [];

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

function formattaQuantita(value, unita) {
  const quantita = Number(value);
  const formattata = Number.isFinite(quantita)
    ? new Intl.NumberFormat("it-IT", { maximumFractionDigits: 3 }).format(quantita)
    : String(value ?? "—");
  return `${formattata} ${unita ?? ""}`.trim();
}

function lottiPerArticolo(articoloId) {
  return lottiVendita.filter((lotto) => String(lotto.articolo_id) === String(articoloId));
}

function aggiornaRiepilogo() {
  const lotto = lottiPerArticolo($("sales-article").value)
    .find((item) => String(item.id) === $("sales-lot").value);
  const dataLotto = lotto?.data_scadenza || lotto?.data_tmc;
  const tipoData = lotto?.data_scadenza ? "Scadenza" : lotto?.data_tmc ? "TMC" : "Data";
  const tmcSuperato = lotto?.data_tmc
    && String(lotto.data_tmc).slice(0, 10) < dataLocaleISO();
  $("sales-lot-summary").textContent = lotto
    ? `Disponibili: ${formattaQuantita(lotto.quantita_disponibile, lotto.unita_misura)} · ${tipoData}: ${formattaData(dataLotto)}${tmcSuperato ? " · TMC superato: richiede conferma" : ""}`
    : "";
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
      `${precedenza}${lotto.codice_lotto} · disponibili ${formattaQuantita(lotto.quantita_disponibile, lotto.unita_misura)} · ${tipoData} ${formattaData(dataLotto)}`,
    ));
  });

  const lottoSelezionato = lotti.some((lotto) => String(lotto.id) === lottoPreferito)
    ? lottoPreferito
    : String(lotti[0]?.id ?? "");
  selettoreLotto.value = lottoSelezionato;
  selettoreLotto.disabled = lotti.length === 0;
  aggiornaRiepilogo();
}

function aggiornaArticoli(articoloPreferito = "") {
  const selettoreArticolo = $("sales-article");
  const articoli = new Map();
  lottiVendita.forEach((lotto) => {
    if (!articoli.has(String(lotto.articolo_id))) {
      articoli.set(String(lotto.articolo_id), lotto.articolo);
    }
  });

  selettoreArticolo.replaceChildren(creaOpzione("", articoli.size ? "Seleziona articolo" : "Nessun articolo disponibile"));
  articoli.forEach((nome, id) => selettoreArticolo.appendChild(creaOpzione(id, nome)));

  const selezione = articoli.has(articoloPreferito)
    ? articoloPreferito
    : String(articoli.keys().next().value ?? "");
  selettoreArticolo.value = selezione;
  selettoreArticolo.disabled = articoli.size === 0;
  aggiornaLotti(selezione);
}

export async function loadVendite() {
  const articoloSelezionato = $("sales-article").value;
  const lottoSelezionato = $("sales-lot").value;
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
      aggiornaLotti(articoloSelezionato, lottoSelezionato);
    }
  } catch (error) {
    lottiVendita = [];
    aggiornaArticoli();
    $("sales-selection-error").textContent = `Impossibile caricare i lotti disponibili: ${error.message}`;
  }
}

export function initVendite() {
  $("sales-article").addEventListener("change", (event) => {
    aggiornaLotti(event.target.value);
  });
  $("sales-lot").addEventListener("change", aggiornaRiepilogo);
  $("btn-refresh-sales-lots").addEventListener("click", loadVendite);
}
