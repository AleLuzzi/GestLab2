import { $ } from "./dom.js";
import {
  loadDipendenti, loadFornitori, loadMerceologie, loadReparti, loadTagli,
} from "../features/anagrafiche.js";
import { loadDashboard } from "../features/dashboard.js";
import { openIngressoMerce } from "../features/ingresso-merce.js";
import { loadLotti } from "../features/lotti.js";
import { loadMenu } from "../features/menu.js";
import { loadPrintJobs } from "../features/printing.js";
import { loadProgressivi } from "../features/progressivi.js";

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
    dipendenti: loadDipendenti,
    tagli: loadTagli,
    merceologie: loadMerceologie,
    reparti: loadReparti,
    fornitori: loadFornitori,
    progressivi: loadProgressivi,
    lotti: loadLotti,
    menu: loadMenu,
    printjobs: loadPrintJobs,
  };
  loaders[view]?.();
}

export function initNavigation() {
  $("btn-ingresso-merce").addEventListener("click", openIngressoMerce);
  $("btn-configurazioni").addEventListener("click", openConfigurazioni);
  $("btn-back-home").addEventListener("click", showLanding);
  $("btn-back-from-ingresso").addEventListener("click", showLanding);
  $("btn-back-progressivi").addEventListener("click", () => switchView("configurazioni"));
  document.querySelectorAll(".nav-item").forEach((button) =>
    button.addEventListener("click", () => switchView(button.dataset.view)));
  document.querySelectorAll(".config-card").forEach((card) =>
    card.addEventListener("click", () => switchView(card.dataset.view)));
  return showLanding;
}
