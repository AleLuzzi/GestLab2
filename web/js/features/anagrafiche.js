import { api } from "../api/client.js";
import { $, esc } from "../core/dom.js";

async function renderTable(tbodyId, endpoint, columns, emptyLabel, colSpan) {
  const tbody = $(tbodyId);
  try {
    const list = await api(endpoint);
    tbody.innerHTML = list.length
      ? list.map((item) => `<tr>${columns(item)}</tr>`).join("")
      : `<tr><td colspan="${colSpan}" class="empty">${emptyLabel}</td></tr>`;
  } catch (error) {
    tbody.innerHTML = `<tr><td colspan="${colSpan}" class="empty">${esc(error.message)}</td></tr>`;
  }
}

async function loadOptions(selectId, endpoint, labelKey, emptyLabel, missingLabel, errorLabel, selectedId = "") {
  const select = $(selectId);
  if (!select) return;

  try {
    const list = await api(endpoint);
    select.innerHTML = "";
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = list.length ? emptyLabel : missingLabel;
    select.appendChild(placeholder);

    list.forEach((item) => {
      const option = document.createElement("option");
      option.value = String(item.id);
      option.textContent = item[labelKey];
      option.selected = String(selectedId) === String(item.id);
      select.appendChild(option);
    });
    if (selectedId === "") select.value = "";
  } catch (_) {
    select.innerHTML = `<option value="">${errorLabel}</option>`;
  }
}

async function saveResource({ id, endpoint, payload, formId, errorId, reload }) {
  $(errorId).textContent = "";
  try {
    await api(id ? `${endpoint}/${id}` : endpoint, {
      method: id ? "PUT" : "POST",
      body: JSON.stringify(payload),
    });
    $(formId).style.display = "none";
    await reload();
  } catch (error) {
    $(errorId).textContent = error.message;
  }
}

async function deleteResource(endpoint, id, label, reload) {
  if (!confirm(`Eliminare ${label} #${id}?`)) return;
  try {
    await api(`${endpoint}/${id}`, { method: "DELETE" });
    await reload();
  } catch (error) {
    alert(error.message);
  }
}

export const loadDipendenti = () => renderTable("dip-tbody", "/api/v1/dipendenti", (item) => `
  <td>${esc(item.id)}</td><td>${esc(item.nome)}</td><td>${esc(item.email)}</td>
  <td>${esc(item.reparto_nome ?? "")}</td><td class="row-actions">
    <button class="btn ghost" data-action="edit-dip" data-id="${esc(item.id)}">Modifica</button>
    <button class="btn danger" data-action="delete-dip" data-id="${esc(item.id)}">Elimina</button>
  </td>`, "Nessun dipendente", 5);

export const loadTagli = () => renderTable("tagli-tbody", "/api/v1/tagli", (item) => `
  <td>${esc(item.id)}</td><td>${esc(item.taglio)}</td><td>${esc(item.merceologia_nome ?? "")}</td>
  <td class="row-actions">
    <button class="btn ghost" data-action="edit-taglio" data-id="${esc(item.id)}">Modifica</button>
    <button class="btn danger" data-action="delete-taglio" data-id="${esc(item.id)}">Elimina</button>
  </td>`, "Nessun taglio", 4);

export const loadMerceologie = () => renderTable("merc-tbody", "/api/v1/merceologie", (item) => `
  <td>${esc(item.id)}</td><td>${esc(item.merceologia)}</td><td>${esc(item.reparto_nome ?? "")}</td>
  <td>${esc(item.flag1_inv ? "Sì" : "No")}</td><td>${esc(item.flag2_taglio ? "Sì" : "No")}</td>
  <td>${esc(item.flag3_ing_base ? "Sì" : "No")}</td><td class="row-actions">
    <button class="btn ghost" data-action="edit-merceologia" data-id="${esc(item.id)}">Modifica</button>
    <button class="btn danger" data-action="delete-merceologia" data-id="${esc(item.id)}">Elimina</button>
  </td>`, "Nessuna merceologia", 7);

export const loadReparti = () => renderTable("reparti-tbody", "/api/v1/reparti", (item) => `
  <td>${esc(item.id)}</td><td>${esc(item.reparto)}</td><td>${esc(item.flag1_dip ? "Sì" : "No")}</td>
  <td>${esc(item.flag2_prod ? "Sì" : "No")}</td><td class="row-actions">
    <button class="btn ghost" data-action="edit-reparto" data-id="${esc(item.id)}">Modifica</button>
    <button class="btn danger" data-action="delete-reparto" data-id="${esc(item.id)}">Elimina</button>
  </td>`, "Nessun reparto", 5);

export const loadFornitori = () => renderTable("fornitori-tbody", "/api/v1/fornitori", (item) => `
  <td>${esc(item.id)}</td><td>${esc(item.azienda)}</td><td>${esc(item.flag1_ing_merce ? "Sì" : "No")}</td>
  <td>${esc(item.flag2_inventario ? "Sì" : "No")}</td><td class="row-actions">
    <button class="btn ghost" data-action="edit-fornitore" data-id="${esc(item.id)}">Modifica</button>
    <button class="btn danger" data-action="delete-fornitore" data-id="${esc(item.id)}">Elimina</button>
  </td>`, "Nessun fornitore", 5);

async function editDip(id) {
  try {
    const item = (await api("/api/v1/dipendenti")).find((row) => row.id === id);
    if (!item) return;
    $("dip-id").value = item.id;
    $("dip-nome").value = item.nome;
    $("dip-email").value = item.email;
    $("dip-form-title").textContent = `Modifica dipendente #${item.id}`;
    $("dip-error").textContent = "";
    await loadOptions("dip-reparto", "/api/v1/reparti", "reparto", "Seleziona reparto", "Nessun reparto disponibile", "Errore caricamento reparti", item.reparto ?? "");
    $("dip-form").style.display = "block";
  } catch (error) { $("dip-error").textContent = error.message; }
}

function nuovaDip() {
  $("dip-id").value = "";
  $("dip-nome").value = "";
  $("dip-email").value = "";
  $("dip-form-title").textContent = "Nuovo dipendente";
  $("dip-error").textContent = "";
  loadOptions("dip-reparto", "/api/v1/reparti", "reparto", "Seleziona reparto", "Nessun reparto disponibile", "Errore caricamento reparti")
    .then(() => { $("dip-form").style.display = "block"; });
}

function salvaDip() {
  const id = $("dip-id").value;
  const reparto = $("dip-reparto").value;
  return saveResource({ id, endpoint: "/api/v1/dipendenti", formId: "dip-form", errorId: "dip-error", reload: loadDipendenti,
    payload: { nome: $("dip-nome").value, email: $("dip-email").value, reparto: reparto === "" ? null : Number(reparto) } });
}

async function editTaglio(id) {
  try {
    const item = (await api("/api/v1/tagli")).find((row) => row.id === id);
    if (!item) return;
    $("tagli-id").value = item.id;
    $("tagli-nome").value = item.taglio;
    $("tagli-form-title").textContent = `Modifica taglio #${item.id}`;
    $("tagli-error").textContent = "";
    await loadOptions("tagli-merceologia", "/api/v1/merceologie", "merceologia", "Seleziona merceologia", "Nessuna merceologia disponibile", "Errore caricamento merceologie", item.id_merceologia ?? "");
    $("tagli-form").style.display = "block";
  } catch (error) { $("tagli-error").textContent = error.message; }
}

function nuovoTaglio() {
  $("tagli-id").value = "";
  $("tagli-nome").value = "";
  $("tagli-form-title").textContent = "Nuovo taglio";
  $("tagli-error").textContent = "";
  loadOptions("tagli-merceologia", "/api/v1/merceologie", "merceologia", "Seleziona merceologia", "Nessuna merceologia disponibile", "Errore caricamento merceologie")
    .then(() => { $("tagli-form").style.display = "block"; });
}

function salvaTaglio() {
  const id = $("tagli-id").value;
  const merceologia = $("tagli-merceologia").value;
  return saveResource({ id, endpoint: "/api/v1/tagli", formId: "tagli-form", errorId: "tagli-error", reload: loadTagli,
    payload: { taglio: $("tagli-nome").value, id_merceologia: merceologia === "" ? null : Number(merceologia) } });
}

async function editMerc(id) {
  try {
    const item = (await api("/api/v1/merceologie")).find((row) => row.id === id);
    if (!item) return;
    $("merc-id").value = item.id;
    $("merc-nome").value = item.merceologia;
    $("merc-form-title").textContent = `Modifica merceologia #${item.id}`;
    $("merc-error").textContent = "";
    await loadOptions("merc-reparto", "/api/v1/reparti", "reparto", "Seleziona reparto", "Nessun reparto disponibile", "Errore caricamento reparti", item.reparto ?? "");
    $("merc-form").style.display = "block";
  } catch (error) { $("merc-error").textContent = error.message; }
}

function nuovaMerc() {
  $("merc-id").value = "";
  $("merc-nome").value = "";
  $("merc-form-title").textContent = "Nuova merceologia";
  $("merc-error").textContent = "";
  loadOptions("merc-reparto", "/api/v1/reparti", "reparto", "Seleziona reparto", "Nessun reparto disponibile", "Errore caricamento reparti")
    .then(() => { $("merc-form").style.display = "block"; });
}

function salvaMerc() {
  const id = $("merc-id").value;
  const reparto = $("merc-reparto").value;
  return saveResource({ id, endpoint: "/api/v1/merceologie", formId: "merc-form", errorId: "merc-error", reload: loadMerceologie,
    payload: { merceologia: $("merc-nome").value, reparto: reparto === "" ? null : Number(reparto) } });
}

function nuovoReparto() {
  $("reparti-id").value = "";
  $("reparti-nome").value = "";
  $("reparti-flag1").checked = false;
  $("reparti-flag2").checked = false;
  $("reparti-form-title").textContent = "Nuovo reparto";
  $("reparti-error").textContent = "";
  $("reparti-form").style.display = "block";
}

async function editReparto(id) {
  try {
    const item = (await api("/api/v1/reparti")).find((row) => row.id === id);
    if (!item) return;
    $("reparti-id").value = item.id;
    $("reparti-nome").value = item.reparto;
    $("reparti-flag1").checked = Boolean(item.flag1_dip);
    $("reparti-flag2").checked = Boolean(item.flag2_prod);
    $("reparti-form-title").textContent = `Modifica reparto #${item.id}`;
    $("reparti-error").textContent = "";
    $("reparti-form").style.display = "block";
  } catch (error) { $("reparti-error").textContent = error.message; }
}

function salvaReparto() {
  const id = $("reparti-id").value;
  return saveResource({ id, endpoint: "/api/v1/reparti", formId: "reparti-form", errorId: "reparti-error", reload: loadReparti,
    payload: { reparto: $("reparti-nome").value, flag1_dip: $("reparti-flag1").checked ? 1 : 0, flag2_prod: $("reparti-flag2").checked ? 1 : 0 } });
}

function nuovoFornitore() {
  $("fornitori-id").value = "";
  $("fornitori-azienda").value = "";
  $("fornitori-flag1").checked = false;
  $("fornitori-flag2").checked = false;
  $("fornitori-form-title").textContent = "Nuovo fornitore";
  $("fornitori-error").textContent = "";
  $("fornitori-form").style.display = "block";
}

async function editFornitore(id) {
  try {
    const item = (await api("/api/v1/fornitori")).find((row) => row.id === id);
    if (!item) return;
    $("fornitori-id").value = item.id;
    $("fornitori-azienda").value = item.azienda;
    $("fornitori-flag1").checked = Boolean(item.flag1_ing_merce);
    $("fornitori-flag2").checked = Boolean(item.flag2_inventario);
    $("fornitori-form-title").textContent = `Modifica fornitore #${item.id}`;
    $("fornitori-error").textContent = "";
    $("fornitori-form").style.display = "block";
  } catch (error) { $("fornitori-error").textContent = error.message; }
}

function salvaFornitore() {
  const id = $("fornitori-id").value;
  return saveResource({ id, endpoint: "/api/v1/fornitori", formId: "fornitori-form", errorId: "fornitori-error", reload: loadFornitori,
    payload: { azienda: $("fornitori-azienda").value, flag1_ing_merce: $("fornitori-flag1").checked ? 1 : 0, flag2_inventario: $("fornitori-flag2").checked ? 1 : 0 } });
}

function bindForm(newButtonId, saveButtonId, cancelButtonId, formId, createHandler, saveHandler) {
  $(newButtonId).addEventListener("click", createHandler);
  $(saveButtonId).addEventListener("click", saveHandler);
  $(cancelButtonId).addEventListener("click", () => { $(formId).style.display = "none"; });
}

export function initAnagrafiche() {
  const actions = {
    "edit-dip": editDip,
    "delete-dip": (id) => deleteResource("/api/v1/dipendenti", id, "il dipendente", loadDipendenti),
    "edit-taglio": editTaglio,
    "delete-taglio": (id) => deleteResource("/api/v1/tagli", id, "il taglio", loadTagli),
    "edit-merceologia": editMerc,
    "delete-merceologia": (id) => deleteResource("/api/v1/merceologie", id, "la merceologia", loadMerceologie),
    "edit-reparto": editReparto,
    "delete-reparto": (id) => deleteResource("/api/v1/reparti", id, "il reparto", loadReparti),
    "edit-fornitore": editFornitore,
    "delete-fornitore": (id) => deleteResource("/api/v1/fornitori", id, "il fornitore", loadFornitori),
  };
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-action]");
    const action = button && actions[button.dataset.action];
    if (action) action(Number(button.dataset.id));
  });

  bindForm("btn-nuovo-dip", "btn-save-dip", "btn-cancel-dip", "dip-form", nuovaDip, salvaDip);
  bindForm("btn-nuovo-taglio", "btn-save-taglio", "btn-cancel-taglio", "tagli-form", nuovoTaglio, salvaTaglio);
  bindForm("btn-nuovo-merc", "btn-save-merc", "btn-cancel-merc", "merc-form", nuovaMerc, salvaMerc);
  bindForm("btn-nuovo-reparto", "btn-save-reparto", "btn-cancel-reparto", "reparti-form", nuovoReparto, salvaReparto);
  bindForm("btn-nuovo-fornitore", "btn-save-fornitore", "btn-cancel-fornitore", "fornitori-form", nuovoFornitore, salvaFornitore);
}
