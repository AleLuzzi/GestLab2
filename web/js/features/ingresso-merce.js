import { $ } from "../core/dom.js";

function updateIngressoMerceSummary() {
  const fornitore = $("ingress-fornitore");
  const data = $("ingress-data");
  const quantita = Number($("ingress-qta").value || 0);
  const unitario = Number($("ingress-prezzo").value || 0);

  $("summary-fornitore").textContent = fornitore.value
    ? fornitore.options[fornitore.selectedIndex].text
    : "-";
  $("summary-data").textContent = data.value
    ? new Date(data.value + "T00:00:00").toLocaleDateString("it-IT")
    : "-";
  $("summary-ddt").textContent = $("ingress-ddt").value || "-";
  $("summary-prodotto").textContent = $("ingress-prodotto").value || "-";
  $("summary-totale").textContent = new Intl.NumberFormat("it-IT", {
    style: "currency",
    currency: "EUR",
  }).format(quantita * unitario);
}

function resetIngressoMerce() {
  $("ingress-fornitore").value = "";
  $("ingress-data").value = "";
  $("ingress-ddt").value = "";
  $("ingress-prodotto").value = "";
  $("ingress-qta").value = 1;
  $("ingress-peso").value = 0;
  $("ingress-prezzo").value = 0;
  $("ingress-iva").value = 22;
  $("ingress-error").textContent = "";
  updateIngressoMerceSummary();
}

export function openIngressoMerce() {
  document.querySelectorAll(".panel").forEach((panel) => panel.classList.remove("active"));
  $("view-ingresso-merce").classList.add("active");
  document.querySelectorAll(".nav-item").forEach((button) => button.classList.remove("active"));
  updateIngressoMerceSummary();
}

export function initIngressoMerce() {
  $("btn-reset-ingresso").addEventListener("click", resetIngressoMerce);
  $("btn-salva-ingresso").addEventListener("click", () => {
    const prodotto = $("ingress-prodotto").value.trim();
    const fornitore = $("ingress-fornitore").value;
    if (!fornitore || !prodotto) {
      $("ingress-error").textContent = "Seleziona fornitore e inserisci il prodotto.";
      return;
    }
    $("ingress-error").textContent = "Movimento di ingresso registrato in memoria.";
    updateIngressoMerceSummary();
  });

  [
    "ingress-fornitore", "ingress-data", "ingress-ddt", "ingress-prodotto",
    "ingress-qta", "ingress-peso", "ingress-prezzo", "ingress-iva",
  ].forEach((id) => {
    const element = $(id);
    element.addEventListener("input", updateIngressoMerceSummary);
    element.addEventListener("change", updateIngressoMerceSummary);
  });
}
