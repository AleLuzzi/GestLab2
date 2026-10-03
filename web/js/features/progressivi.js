import { api } from "../api/client.js";
import { $, esc } from "../core/dom.js";

let progressiviCorrenti = null;

export async function loadProgressivi() {
  const tbody = $("progressivi-tbody");
  const nuovoButton = $("btn-nuovo-progressivi");
  $("progressivi-error").textContent = "";

  try {
    const records = await api("/api/v1/progressivi");
    progressiviCorrenti = records[0] ?? null;
    nuovoButton.style.display = progressiviCorrenti ? "none" : "";
    tbody.innerHTML = progressiviCorrenti
      ? `<tr>
          <td>${esc(progressiviCorrenti.prog_acq ?? "")}</td>
          <td>${esc(progressiviCorrenti.prog_ven ?? "")}</td>
          <td class="row-actions">
            <button class="btn ghost" data-progressivi-action="edit">Modifica</button>
            <button class="btn danger" data-progressivi-action="delete">Elimina</button>
          </td>
        </tr>`
      : '<tr><td colspan="3" class="empty">Progressivi non configurati</td></tr>';
  } catch (error) {
    progressiviCorrenti = null;
    nuovoButton.style.display = "none";
    tbody.innerHTML = '<tr><td colspan="3" class="empty">Impossibile caricare i progressivi</td></tr>';
    $("progressivi-error").textContent = error.message;
  }
}

function mostraForm(record = null) {
  progressiviCorrenti = record;
  $("progressivi-form-title").textContent = record ? "Modifica progressivi" : "Configura progressivi";
  $("progressivi-acq").value = record?.prog_acq ?? 0;
  $("progressivi-ven").value = record?.prog_ven ?? 0;
  $("progressivi-form").style.display = "block";
  $("progressivi-error").textContent = "";
}

async function salvaProgressivi(event) {
  event.preventDefault();
  const form = $("progressivi-form");
  if (!form.reportValidity()) return;

  const payload = {
    prog_acq: Number($("progressivi-acq").value),
    prog_ven: Number($("progressivi-ven").value),
  };
  $("progressivi-error").textContent = "";

  try {
    await api("/api/v1/progressivi", {
      method: progressiviCorrenti ? "PUT" : "POST",
      body: JSON.stringify(payload),
    });
    form.style.display = "none";
    await loadProgressivi();
  } catch (error) {
    $("progressivi-error").textContent = error.message;
  }
}

async function eliminaProgressivi() {
  if (!confirm("Eliminare i progressivi del tenant?")) return;
  $("progressivi-error").textContent = "";

  try {
    await api("/api/v1/progressivi", { method: "DELETE" });
    $("progressivi-form").style.display = "none";
    await loadProgressivi();
  } catch (error) {
    $("progressivi-error").textContent = error.message;
  }
}

export function initProgressivi() {
  $("btn-nuovo-progressivi").addEventListener("click", () => mostraForm());
  $("progressivi-form").addEventListener("submit", salvaProgressivi);
  $("btn-cancel-progressivi").addEventListener("click", () => {
    $("progressivi-form").style.display = "none";
    $("progressivi-error").textContent = "";
  });
  $("progressivi-tbody").addEventListener("click", (event) => {
    if (!(event.target instanceof Element)) return;
    const action = event.target.closest("[data-progressivi-action]")?.dataset.progressiviAction;
    if (action === "edit") mostraForm(progressiviCorrenti);
    if (action === "delete") eliminaProgressivi();
  });
}
