import { api } from "../api/client.js";
import { $ } from "../core/dom.js";

const EXPIRY_LIST_LIMIT = 50;

function dataISO(value) {
  const data = String(value ?? "").slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(data)) return null;
  const [anno, mese, giorno] = data.split("-").map(Number);
  const timestamp = Date.UTC(anno, mese - 1, giorno);
  const parsed = new Date(timestamp);
  if (
    parsed.getUTCFullYear() !== anno
    || parsed.getUTCMonth() !== mese - 1
    || parsed.getUTCDate() !== giorno
  ) return null;
  return data;
}

function oggiISO() {
  const oggi = new Date();
  return `${oggi.getFullYear()}-${String(oggi.getMonth() + 1).padStart(2, "0")}-${String(oggi.getDate()).padStart(2, "0")}`;
}

function differenzaGiorni(data, oggi) {
  return (Date.parse(`${data}T00:00:00Z`) - Date.parse(`${oggi}T00:00:00Z`)) / 86400000;
}

function dataLocale(value) {
  const data = dataISO(value);
  if (!data) return "—";
  const parsed = new Date(`${data}T00:00:00`);
  return Number.isNaN(parsed.getTime()) ? data : parsed.toLocaleDateString("it-IT");
}

function quantitaLocale(value, unita = "") {
  const numero = Number(value);
  const quantita = Number.isFinite(numero)
    ? new Intl.NumberFormat("it-IT", { maximumFractionDigits: 3 }).format(numero)
    : String(value ?? "—");
  return unita ? `${quantita} ${unita}` : quantita;
}

function aggiungiCella(riga, valore) {
  const cella = document.createElement("td");
  cella.textContent = String(valore ?? "—");
  riga.appendChild(cella);
}

function aggiungiRighe(tabellaId, righe, valori) {
  const tabella = $(tabellaId);
  tabella.replaceChildren();
  righe.forEach((elemento) => {
    const riga = document.createElement("tr");
    valori(elemento).forEach((valore) => aggiungiCella(riga, valore));
    tabella.appendChild(riga);
  });
}

function mostraLista(tabellaId, vuotoId, elementi, valori) {
  aggiungiRighe(tabellaId, elementi, valori);
  $(vuotoId).hidden = elementi.length > 0;
  $(tabellaId).closest("table").hidden = elementi.length === 0;
}

function segnalaLimite(id, totale) {
  const messaggio = $(id);
  messaggio.hidden = totale <= EXPIRY_LIST_LIMIT;
  if (!messaggio.hidden) {
    messaggio.textContent = `Mostrati i primi ${EXPIRY_LIST_LIMIT} di ${totale} risultati.`;
  }
}

function aggiornaAttenzioneOperativa(lotti, jobError) {
  const oggi = oggiISO();
  const scadenzaDueGiorni = [];
  const scadenzaSetteGiorni = [];
  const scaduti = [];
  const aZero = [];

  lotti.forEach((lotto) => {
    const quantita = Number(lotto.quantita_disponibile);
    if (Number.isFinite(quantita) && quantita === 0) aZero.push(lotto);
    const data = dataISO(lotto.data_scadenza);
    if (!data || !Number.isFinite(quantita) || quantita <= 0) return;

    const giorni = differenzaGiorni(data, oggi);
    if (giorni < 0) scaduti.push(lotto);
    else if (giorni <= 2) scadenzaDueGiorni.push(lotto);
    else if (giorni <= 7) scadenzaSetteGiorni.push(lotto);
  });

  const scadenze = [
    ...scaduti.map((lotto) => ({ lotto, stato: "Scaduto" })),
    ...scadenzaDueGiorni.map((lotto) => ({ lotto, stato: "Entro 48 ore" })),
    ...scadenzaSetteGiorni.map((lotto) => ({ lotto, stato: "Entro 7 giorni" })),
  ];
  $("stat-lotti-scaduti").textContent = scaduti.length;
  $("stat-lotti-48h").textContent = scadenzaDueGiorni.length;
  $("stat-lotti-7gg").textContent = scadenzaSetteGiorni.length;
  $("stat-lotti-zero").textContent = aZero.length;
  $("stat-jobs-error").textContent = jobError.length === 100 ? "100+" : jobError.length;

  mostraLista(
    "dashboard-expiring-tbody",
    "dashboard-expiring-empty",
    scadenze.slice(0, EXPIRY_LIST_LIMIT),
    ({ lotto, stato }) => [
      lotto.codice_lotto,
      lotto.articolo,
      quantitaLocale(lotto.quantita_disponibile, lotto.unita_misura),
      dataLocale(lotto.data_scadenza),
      stato,
    ],
  );
  mostraLista(
    "dashboard-zero-tbody",
    "dashboard-zero-empty",
    aZero.slice(0, EXPIRY_LIST_LIMIT),
    (lotto) => [lotto.codice_lotto, lotto.articolo, dataLocale(lotto.data_scadenza)],
  );
  mostraLista(
    "dashboard-errors-tbody",
    "dashboard-errors-empty",
    jobError.slice(0, EXPIRY_LIST_LIMIT),
    (job) => [job.id, job.tipo, dataLocale(job.creato_il), job.stato    ],
  );
  segnalaLimite("dashboard-expiring-truncated", scadenze.length);
  segnalaLimite("dashboard-zero-truncated", aZero.length);
  segnalaLimite("dashboard-errors-truncated", jobError.length);
}

export async function loadDashboard() {
  $("dashboard-error").textContent = "";
  try {
    const [dip, reparti, fornitori, merceologie, lotti, jobs, jobError] = await Promise.all([
      api("/api/v1/dipendenti"),
      api("/api/v1/reparti"),
      api("/api/v1/fornitori"),
      api("/api/v1/merceologie"),
      api("/api/v1/tracciabilita/lotti"),
      api("/api/v1/print-jobs"),
      api("/api/v1/print-jobs?stato=error"),
    ]);
    $("stat-dip").textContent = Array.isArray(dip) ? dip.length : 0;
    $("stat-reparti").textContent = Array.isArray(reparti) ? reparti.length : 0;
    $("stat-fornitori").textContent = Array.isArray(fornitori) ? fornitori.length : 0;
    $("stat-merc").textContent = Array.isArray(merceologie) ? merceologie.length : 0;
    $("stat-lotti").textContent = Array.isArray(lotti) ? lotti.length : 0;
    $("stat-jobs").textContent = Array.isArray(jobs) ? jobs.length : 0;
    aggiornaAttenzioneOperativa(
      Array.isArray(lotti) ? lotti : [],
      Array.isArray(jobError) ? jobError : [],
    );
  } catch (error) {
    ["stat-dip", "stat-reparti", "stat-fornitori", "stat-merc", "stat-lotti", "stat-jobs"]
      .forEach((id) => { $(id).textContent = "—"; });
    [
      "stat-lotti-scaduti",
      "stat-lotti-48h",
      "stat-lotti-7gg",
      "stat-lotti-zero",
      "stat-jobs-error",
    ].forEach((id) => { $(id).textContent = "—"; });
    mostraLista("dashboard-expiring-tbody", "dashboard-expiring-empty", [], () => []);
    mostraLista("dashboard-zero-tbody", "dashboard-zero-empty", [], () => []);
    mostraLista("dashboard-errors-tbody", "dashboard-errors-empty", [], () => []);
    [
      "dashboard-expiring-empty",
      "dashboard-zero-empty",
      "dashboard-errors-empty",
      "dashboard-expiring-truncated",
      "dashboard-zero-truncated",
      "dashboard-errors-truncated",
    ].forEach((id) => { $(id).hidden = true; });
    $("dashboard-error").textContent = `Impossibile caricare la dashboard: ${error.message}`;
  }
}

async function doEanLookup() {
  const code = $("ean-input").value.trim();
  $("ean-result").textContent = "";
  if (!code) return;

  try {
    const product = await api("/api/v1/articoli/ean/" + encodeURIComponent(code));
    $("ean-result").textContent = JSON.stringify(product, null, 2);
  } catch (error) {
    $("ean-result").textContent = "Errore: " + error.message;
  }
}

export function initDashboard() {
  $("btn-ean").addEventListener("click", doEanLookup);
  $("ean-input").addEventListener("keydown", (event) => {
    if (event.key === "Enter") doEanLookup();
  });
}
