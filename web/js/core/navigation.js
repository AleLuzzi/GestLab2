import { $ } from "./dom.js";
import {
  loadArticoli, loadDipendenti, loadFornitori, loadMerceologie, loadReparti,
} from "../features/anagrafiche.js?v=20261128-4";
import { loadDashboard } from "../features/dashboard.js?v=20261121-5";
import { openIngressoMerce } from "../features/ingresso-merce.js?v=20261128-2";
import { loadMenu } from "../features/menu.js?v=20261114-3";
import { loadLabelLots, loadPrintJobs } from "../features/printing.js";
import { loadDatiOsa } from "../features/admin.js?v=20261121-1";
import { loadProgressivi } from "../features/progressivi.js";
import { loadTracciabilita } from "../features/tracciabilita.js";
import { loadReport } from "../features/report.js?v=20261128-2";
import { loadVendite } from "../features/vendite.js?v=20261128-5";

function showLanding() {
  document.querySelectorAll(".panel").forEach((panel) => panel.classList.remove("active"));
  $("view-landing").classList.add("active");
  document.querySelectorAll(".nav-item").forEach((button) =>
    button.classList.toggle("active", button.dataset.view === "home"));
}

function openConfigurazioni() {
  document.querySelectorAll(".panel").forEach((panel) => panel.classList.remove("active"));
  $("view-configurazioni").classList.add("active");
  document.querySelectorAll(".nav-item").forEach((button) => button.classList.remove("active"));
}

function switchView(view) {
  if (view === "home") {
    showLanding();
    return;
  }

  document.querySelectorAll(".panel").forEach((panel) => panel.classList.remove("active"));
  const target = $("view-" + view);
  if (target) target.classList.add("active");
  document.querySelectorAll(".nav-item").forEach((button) =>
    button.classList.toggle("active", button.dataset.view === view));

  const loaders = {
    dashboard: loadDashboard,
    "ingresso-merce": openIngressoMerce,
    articoli: loadArticoli,
    dipendenti: loadDipendenti,
    merceologie: loadMerceologie,
    reparti: loadReparti,
    fornitori: loadFornitori,
    progressivi: loadProgressivi,
    menu: loadMenu,
    printjobs: loadPrintJobs,
    stampa: loadLabelLots,
    admin: loadDatiOsa,
    tracciabilita: loadTracciabilita,
    vendite: loadVendite,
    report: loadReport,
  };
  loaders[view]?.();
}

export function initNavigation() {
  $("btn-ingresso-merce").addEventListener("click", openIngressoMerce);
  $("btn-configurazioni").addEventListener("click", openConfigurazioni);
  $("btn-back-home").addEventListener("click", showLanding);
  $("btn-back-from-ingresso").addEventListener("click", showLanding);
  $("btn-back-progressivi").addEventListener("click", () => switchView("configurazioni"));
  $("btn-back-dipendenti").addEventListener("click", () => switchView("configurazioni"));
  ["articoli", "merceologie", "reparti", "fornitori", "admin"].forEach((view) => {
    $(`btn-back-${view}`).addEventListener("click", () => switchView("configurazioni"));
  });
  document.querySelectorAll(".nav-item").forEach((button) =>
    button.addEventListener("click", () => switchView(button.dataset.view)));
  document.querySelectorAll(".config-card[data-view]").forEach((card) =>
    card.addEventListener("click", () => switchView(card.dataset.view)));
  document.querySelectorAll(".landing-action[data-view]").forEach((button) =>
    button.addEventListener("click", () => switchView(button.dataset.view)));
  return showLanding;
}
