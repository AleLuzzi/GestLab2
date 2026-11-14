import { api } from "../api/client.js";
import { $ } from "../core/dom.js";

function formattaQuantita(value, unita) {
  const quantita = Number(value);
  const testo = Number.isFinite(quantita)
    ? new Intl.NumberFormat("it-IT", { minimumFractionDigits: 3, maximumFractionDigits: 3 }).format(quantita)
    : "0,000";
  return `${testo} ${unita ?? ""}`.trim();
}

function formattaPrezzo(value, unita) {
  const prezzo = Number(value);
  if (!Number.isFinite(prezzo)) return "Prezzo non configurato";
  const importo = new Intl.NumberFormat("it-IT", {
    style: "currency",
    currency: "EUR",
  }).format(prezzo);
  return `${importo} / ${unita}`;
}

function cella(testo, className = "") {
  const cell = document.createElement("td");
  if (className) cell.className = className;
  cell.textContent = testo;
  return cell;
}

function renderListino(articoli) {
  const box = $("menu-content");
  box.replaceChildren();
  if (!articoli.length) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = $("menu-only-available").checked
      ? "Nessun articolo attivo ha un lotto disponibile."
      : "Nessun articolo attivo.";
    box.appendChild(empty);
    return;
  }

  const gruppi = new Map();
  articoli.forEach((articolo) => {
    const categoria = articolo.categoria?.trim() || "Senza categoria";
    if (!gruppi.has(categoria)) gruppi.set(categoria, []);
    gruppi.get(categoria).push(articolo);
  });

  gruppi.forEach((voci, categoria) => {
    const section = document.createElement("section");
    section.className = "listino-group";
    const title = document.createElement("h3");
    title.textContent = categoria;
    const wrap = document.createElement("div");
    wrap.className = "sales-cart-table-wrap";
    const table = document.createElement("table");
    table.className = "table";
    const head = document.createElement("thead");
    const headRow = document.createElement("tr");
    ["Articolo", "Prezzo", "Giacenza vendibile", "Lotti"].forEach((label) => {
      const th = document.createElement("th");
      th.textContent = label;
      headRow.appendChild(th);
    });
    head.appendChild(headRow);
    const body = document.createElement("tbody");
    voci.forEach((articolo) => {
      const row = document.createElement("tr");
      row.append(
        cella(articolo.nome),
        cella(formattaPrezzo(articolo.prezzo_unitario, articolo.unita_misura)),
        cella(
          articolo.disponibile
            ? formattaQuantita(articolo.quantita_disponibile, articolo.unita_misura)
            : "Nessun lotto disponibile",
          articolo.disponibile ? "" : "listino-unavailable",
        ),
        cella(articolo.disponibile ? String(articolo.lotti_disponibili) : "0"),
      );
      body.appendChild(row);
    });
    table.append(head, body);
    wrap.appendChild(table);
    section.append(title, wrap);
    box.appendChild(section);
  });
}

export async function loadMenu() {
  const box = $("menu-content");
  box.replaceChildren();
  const loading = document.createElement("p");
  loading.className = "empty";
  loading.textContent = "Caricamento…";
  box.appendChild(loading);

  const soloDisponibili = $("menu-only-available").checked;
  try {
    const data = await api(
      `/api/v1/menu?solo_disponibili=${soloDisponibili ? "true" : "false"}`,
    );
    if (!Array.isArray(data)) {
      throw new Error("La risposta del listino non è valida.");
    }
    renderListino(data);
  } catch (error) {
    box.replaceChildren();
    const message = document.createElement("p");
    message.className = "empty";
    message.textContent = `Impossibile caricare il listino: ${error.message}`;
    box.appendChild(message);
  }
}

export function initMenu() {
  $("menu-only-available").addEventListener("change", loadMenu);
}
