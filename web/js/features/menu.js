import { api } from "../api/client.js";
import { $, esc } from "../core/dom.js";

export async function loadMenu() {
  const box = $("menu-content");
  box.innerHTML = '<p class="empty">Caricamento…</p>';

  try {
    const data = await api("/api/v1/menu");
    let groups;
    if (Array.isArray(data)) {
      groups = { Prodotti: data };
    } else {
      groups = {};
      for (const key of ["primi", "secondi", "contorni"]) {
        if (Array.isArray(data[key])) groups[key] = data[key];
      }
      if (Object.keys(groups).length === 0) groups = data;
    }

    const labels = { primi: "Primi", secondi: "Secondi", contorni: "Contorni" };
    box.innerHTML = Object.entries(groups).map(([key, items]) => `
      <h3>${esc(labels[key] || key)}</h3>
      <ul>${items.map((item) => `<li>${esc(item.prodotto || item.name)} — <span class="text-dim">${esc(item.plu || "")}</span></li>`).join("")}</ul>
    `).join("");
  } catch (error) {
    box.innerHTML = `<p class="empty">Errore: ${esc(error.message)}</p>`;
  }
}
