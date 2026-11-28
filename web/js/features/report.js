import { api, apiGetBlob } from "../api/client.js";
import { $ } from "../core/dom.js";

function formattaData(value) {
  if (!value) return "senza scadenza";
  const data = String(value).slice(0, 10);
  const parsed = new Date(`${data}T00:00:00`);
  return Number.isNaN(parsed.getTime()) ? data : parsed.toLocaleDateString("it-IT");
}

export async function accodaRicevuta(venditaId, button = null) {
  if (button) button.disabled = true;
  try {
    return await api(`/api/v1/vendite/${venditaId}/ricevuta`, { method: "POST" });
  } finally {
    if (button) button.disabled = false;
  }
}

export async function scaricaDdt(venditaId, button = null, numero = venditaId) {
  if (button) button.disabled = true;
  try {
    const blob = await apiGetBlob(`/api/v1/vendite/${venditaId}/ddt.pdf`);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `ddt_${numero}.pdf`;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  } finally {
    if (button) button.disabled = false;
  }
}

async function loadDdtHistory() {
  const tbody = $("sales-history-body");
  const status = $("sales-history-status");
  tbody.replaceChildren();
  status.textContent = "";
  try {
    const documenti = await api("/api/v1/vendite/ddt");
    if (!Array.isArray(documenti)) {
      throw new Error("La risposta dello storico DDT non è valida.");
    }
    if (!documenti.length) {
      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.colSpan = 5;
      cell.className = "empty";
      cell.textContent = "Nessun DDT registrato";
      row.appendChild(cell);
      tbody.appendChild(row);
      return;
    }
    documenti.forEach((documento) => {
      const row = document.createElement("tr");
      [
        `DDT ${documento.numero}`,
        formattaData(documento.data_vendita),
        documento.cliente || "Cliente non disponibile",
        String(documento.numero_righe),
      ].forEach((value) => {
        const cell = document.createElement("td");
        cell.textContent = value;
        row.appendChild(cell);
      });
      const actionCell = document.createElement("td");
      const button = document.createElement("button");
      button.type = "button";
      button.className = "btn ghost sales-ddt-download";
      button.dataset.ddtId = String(documento.id);
      button.dataset.ddtNumber = String(documento.numero);
      button.textContent = "Scarica / ristampa";
      actionCell.appendChild(button);
      row.appendChild(actionCell);
      tbody.appendChild(row);
    });
  } catch (error) {
    status.textContent = `Impossibile caricare lo storico DDT: ${error.message}`;
  }
}

async function loadRicevuteHistory() {
  const tbody = $("sales-receipt-history-body");
  const status = $("sales-receipt-history-status");
  tbody.replaceChildren();
  status.textContent = "";
  try {
    const documenti = await api("/api/v1/vendite/ricevute");
    if (!Array.isArray(documenti)) {
      throw new Error("La risposta dello storico ricevute non è valida.");
    }
    if (!documenti.length) {
      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.colSpan = 5;
      cell.className = "empty";
      cell.textContent = "Nessuna ricevuta registrata";
      row.appendChild(cell);
      tbody.appendChild(row);
      return;
    }
    documenti.forEach((documento) => {
      const row = document.createElement("tr");
      [
        `Ricevuta ${documento.numero}`,
        formattaData(documento.data_vendita),
        documento.cliente || "Banco",
        String(documento.numero_righe),
      ].forEach((value) => {
        const cell = document.createElement("td");
        cell.textContent = value;
        row.appendChild(cell);
      });
      const actionCell = document.createElement("td");
      const button = document.createElement("button");
      button.type = "button";
      button.className = "btn ghost sales-receipt-print";
      button.dataset.receiptId = String(documento.id);
      button.dataset.receiptNumber = String(documento.numero);
      button.textContent = "Ristampa";
      actionCell.appendChild(button);
      row.appendChild(actionCell);
      tbody.appendChild(row);
    });
  } catch (error) {
    status.textContent = `Impossibile caricare lo storico ricevute: ${error.message}`;
  }
}

export async function loadReport() {
  await Promise.all([loadDdtHistory(), loadRicevuteHistory()]);
}

export function initReport() {
  $("sales-receipt-history-body").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-receipt-id]");
    if (!button) return;
    $("sales-receipt-history-status").textContent = "";
    try {
      await accodaRicevuta(button.dataset.receiptId, button);
      $("sales-receipt-history-status").textContent =
        `Ricevuta #${button.dataset.receiptNumber} inviata di nuovo al Local Print Agent.`;
    } catch (error) {
      $("sales-receipt-history-status").textContent = `Impossibile accodare la ricevuta: ${error.message}`;
    }
  });
  $("sales-history-body").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-ddt-id]");
    if (!button) return;
    $("sales-history-status").textContent = "";
    try {
      await scaricaDdt(button.dataset.ddtId, button, button.dataset.ddtNumber);
      $("sales-history-status").textContent = "DDT pronto per la stampa.";
    } catch (error) {
      $("sales-history-status").textContent = `Impossibile generare il DDT: ${error.message}`;
    }
  });
}