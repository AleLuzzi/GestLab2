import { api, apiBlob } from "../api/client.js";
import { $, esc } from "../core/dom.js";

let labelDataRequest = 0;

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

function payloadEtichetta() {
  const isAdmin = document.body.dataset.role === "admin";
  const payload = {
    lotto_id: $("et-lotto").value ? Number($("et-lotto").value) : null,
    plu: $("et-plu").value,
    prodotto: $("et-prodotto").value,
    prezzo_kg: $("et-prezzo").value,
    codice: $("et-codice").value,
    conservazione: $("et-conservazione").value,
    peso: $("et-peso").value || null,
  };
  if (isAdmin) {
    payload.ingredienti = $("et-ingredienti").value;
    payload.allergeni = [...$("et-allergeni").selectedOptions].map((option) => option.value);
  }
  return payload;
}

async function generaEtichetta() {
  $("et-error").textContent = "";
  const payload = payloadEtichetta();
  try {
    const blob = await apiBlob("/api/v1/etichetta", payload);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `etichetta_${payload.lotto_id || payload.plu || "x"}.pdf`;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) {
    $("et-error").textContent = `Impossibile generare l'etichetta: ${error.message}`;
  }
}

async function accodaEtichetta() {
  $("et-error").textContent = "";
  $("et-queue-status").textContent = "";
  try {
    const job = await api("/api/v1/etichetta/stampa", {
      method: "POST",
      body: JSON.stringify(payloadEtichetta()),
    });
    $("et-queue-status").textContent =
      `Etichetta accodata (job ${job.id}). Controlla la stampa sulla DYMO configurata.`;
    await loadPrintJobs();
  } catch (error) {
    $("et-error").textContent = `Impossibile accodare l'etichetta: ${error.message}`;
  }
}

async function loadLabelRecipeData(lottoId) {
  const requestId = ++labelDataRequest;
  const preview = $("et-ricetta-dati");
  const submit = $("btn-gen-et");
  const queue = $("btn-queue-et");
  preview.textContent = "";
  $("et-ingredienti").value = "";
  $("et-allergeni").selectedIndex = -1;
  if (!lottoId) {
    submit.disabled = false;
    queue.disabled = false;
    return;
  }
  submit.disabled = true;
  queue.disabled = true;

  try {
    const lotto = await api(`/api/v1/tracciabilita/lotti/${lottoId}`);
    if (requestId !== labelDataRequest || $("et-lotto").value !== String(lottoId)) return;
    const dati = lotto.dati_etichetta || {};
    const allergeni = dati.allergeni || [];
    preview.textContent = dati.ricetta_nome
      ? `Dati ricetta ${dati.ricetta_nome}: ingredienti ${dati.ingredienti || "non configurati"}; allergeni ${allergeni.length ? allergeni.join(", ") : "nessuno indicato"}.`
      : "Lotto senza ricetta collegata: ingredienti e allergeni non sono configurati.";
    if (document.body.dataset.role === "admin") {
      $("et-ingredienti").value = dati.ingredienti || "";
      [...$("et-allergeni").options].forEach((option) => {
        option.selected = allergeni.includes(option.value);
      });
    }
  } catch (error) {
    if (requestId !== labelDataRequest || $("et-lotto").value !== String(lottoId)) return;
    preview.textContent = `Impossibile caricare i dati della ricetta: ${error.message}`;
  } finally {
    if (requestId === labelDataRequest) {
      submit.disabled = false;
      queue.disabled = false;
    }
  }
}

export async function loadLabelLots() {
  const select = $("et-lotto");
  try {
    const lots = await api("/api/v1/tracciabilita/lotti");
    const options = [new Option("Etichetta manuale (senza lotto)", "")];
    lots.forEach((lotto) => {
      const option = new Option(
        `${lotto.codice_lotto} · ${lotto.articolo}`,
        String(lotto.id),
      );
      options.push(option);
    });
    const selected = select.value;
    select.replaceChildren(...options);
    select.value = options.some((option) => option.value === selected) ? selected : "";
    const isLotLabel = Boolean(select.value);
    $("et-plu").disabled = isLotLabel;
    $("et-prodotto").disabled = isLotLabel;
    $("et-prezzo").disabled = isLotLabel;
    $("et-codice").disabled = isLotLabel;
    await loadLabelRecipeData(select.value);
  } catch (error) {
    $("et-error").textContent = `Impossibile caricare i lotti: ${error.message}`;
  }
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
  $("btn-queue-et").addEventListener("click", accodaEtichetta);
  $("et-lotto").addEventListener("change", (event) => {
    const isLotLabel = Boolean($("et-lotto").value);
    $("et-plu").disabled = isLotLabel;
    $("et-prodotto").disabled = isLotLabel;
    $("et-prezzo").disabled = isLotLabel;
    $("et-codice").disabled = isLotLabel;
    loadLabelRecipeData(event.target.value);
  });
  $("btn-refresh-jobs").addEventListener("click", loadPrintJobs);
  addDdtRiga();
  addScoRiga();
}
