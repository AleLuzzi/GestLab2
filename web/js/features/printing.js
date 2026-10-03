import { api, apiBlob } from "../api/client.js";
import { $, esc } from "../core/dom.js";

function switchTab(tab) {
  document.querySelectorAll(".tab-btn").forEach((button) =>
    button.classList.toggle("active", button.dataset.tab === tab));
  document.querySelectorAll(".tab-panel").forEach((panel) =>
    panel.classList.toggle("active", panel.id === "tab-" + tab));
}

function addDdtRiga() {
  const row = document.createElement("div");
  row.className = "row ddt-riga";
  row.innerHTML = `
    <label>Prodotto <input class="ddt-prodotto" /></label>
    <label>Taglio <input class="ddt-taglio" /></label>
    <label>Qtà <input class="ddt-qta" /></label>
    <label>Peso <input class="ddt-peso" /></label>
  `;
  $("ddt-righe").appendChild(row);
}

async function generaDdt() {
  const righe = [...document.querySelectorAll(".ddt-riga")].map((row) => ({
    prodotto: row.querySelector(".ddt-prodotto").value,
    taglio: row.querySelector(".ddt-taglio").value,
    quantita: row.querySelector(".ddt-qta").value,
    peso: row.querySelector(".ddt-peso").value,
  }));
  const payload = {
    numero: $("ddt-numero").value,
    data: $("ddt-data").value,
    fornitore: $("ddt-fornitore").value,
    righe,
  };
  await downloadPost("/api/v1/ddt", payload, "ddt_" + (payload.numero || "x") + ".pdf");
}

function addScoRiga() {
  const row = document.createElement("div");
  row.className = "row sco-riga";
  row.innerHTML = `
    <label>Descrizione <input class="sco-desc" /></label>
    <label>Prezzo <input class="sco-prezzo" /></label>
    <label>Qtà <input class="sco-qta" /></label>
  `;
  $("sco-righe").appendChild(row);
}

async function generaScontrino() {
  const righe = [...document.querySelectorAll(".sco-riga")].map((row) => ({
    descrizione: row.querySelector(".sco-desc").value,
    prezzo: row.querySelector(".sco-prezzo").value,
    qta: row.querySelector(".sco-qta").value,
  }));
  const payload = {
    testata: $("sco-testata").value,
    righe,
    totale: $("sco-totale").value,
    iva: $("sco-iva").value,
  };
  await downloadPost("/api/v1/scontrino", payload, "scontrino.bin");
}

async function generaEtichetta() {
  const payload = {
    plu: $("et-plu").value,
    prodotto: $("et-prodotto").value,
    prezzo_kg: $("et-prezzo").value,
    ingredienti: $("et-ingredienti").value,
    codice: $("et-codice").value,
  };
  await downloadPost("/api/v1/etichetta", payload, "etichetta_" + (payload.plu || "x") + ".pdf");
}

async function downloadPost(path, body, filename) {
  let blob;
  try {
    blob = await apiBlob(path, body);
  } catch (error) {
    alert("Errore: " + error.message);
    return;
  }

  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export async function loadPrintJobs() {
  try {
    const jobs = await api("/api/v1/print-jobs");
    $("jobs-tbody").innerHTML = jobs.length
      ? jobs.map((job) => `
        <tr>
          <td>${esc(job.id)}</td>
          <td>${esc(job.tipo)}</td>
          <td><span class="role-badge">${esc(job.stato)}</span></td>
          <td>${esc(job.creato_il)}</td>
          <td><code>${esc(job.payload)}</code></td>
        </tr>`).join("")
      : '<tr><td colspan="5" class="empty">Nessun job di stampa</td></tr>';
  } catch (error) {
    $("jobs-tbody").innerHTML = `<tr><td colspan="5" class="empty">${esc(error.message)}</td></tr>`;
  }
}

export function initPrinting() {
  document.querySelectorAll(".tab-btn").forEach((button) =>
    button.addEventListener("click", () => switchTab(button.dataset.tab)));
  $("btn-add-riga").addEventListener("click", addDdtRiga);
  $("btn-gen-ddt").addEventListener("click", generaDdt);
  $("btn-add-sco").addEventListener("click", addScoRiga);
  $("btn-gen-sco").addEventListener("click", generaScontrino);
  $("btn-gen-et").addEventListener("click", generaEtichetta);
  $("btn-refresh-jobs").addEventListener("click", loadPrintJobs);
  addDdtRiga();
  addScoRiga();
}
