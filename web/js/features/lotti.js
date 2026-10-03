import { api } from "../api/client.js";
import { $, esc } from "../core/dom.js";

export async function loadLotti() {
  try {
    const list = await api("/api/v1/lotti/aperti");
    $("lotti-tbody").innerHTML = list.length
      ? list.map((lot) => `
        <tr>
          <td>${esc(lot.number ?? lot.progressivo_acq)}</td>
          <td>${esc(lot.fornit ?? lot.fornitore)}</td>
          <td>${esc(lot.name ?? lot.prodotto)}</td>
          <td>${esc(lot.peso ?? lot.residuo)}</td>
        </tr>`).join("")
      : '<tr><td colspan="4" class="empty">Nessun lotto aperto</td></tr>';
  } catch (error) {
    $("lotti-tbody").innerHTML = `<tr><td colspan="4" class="empty">${esc(error.message)}</td></tr>`;
  }
}
