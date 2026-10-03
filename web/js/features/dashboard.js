import { api } from "../api/client.js";
import { $ } from "../core/dom.js";

export async function loadDashboard() {
  try {
    const [dip, reparti, fornitori, merceologie, lotti, jobs] = await Promise.all([
      api("/api/v1/dipendenti"),
      api("/api/v1/reparti"),
      api("/api/v1/fornitori"),
      api("/api/v1/merceologie"),
      api("/api/v1/lotti/aperti"),
      api("/api/v1/print-jobs"),
    ]);
    $("stat-dip").textContent = Array.isArray(dip) ? dip.length : 0;
    $("stat-reparti").textContent = Array.isArray(reparti) ? reparti.length : 0;
    $("stat-fornitori").textContent = Array.isArray(fornitori) ? fornitori.length : 0;
    $("stat-merc").textContent = Array.isArray(merceologie) ? merceologie.length : 0;
    $("stat-lotti").textContent = Array.isArray(lotti) ? lotti.length : 0;
    $("stat-jobs").textContent = Array.isArray(jobs) ? jobs.length : 0;
  } catch (_) {
    ["stat-dip", "stat-reparti", "stat-fornitori", "stat-merc", "stat-lotti", "stat-jobs"]
      .forEach((id) => { $(id).textContent = "—"; });
  }
}

async function doEanLookup() {
  const code = $("ean-input").value.trim();
  $("ean-result").textContent = "";
  if (!code) return;

  try {
    const product = await api("/api/v1/prodotti/ean/" + encodeURIComponent(code));
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
