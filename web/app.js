// GestLab SaaS — frontend console (vanilla JS, nessuna dipendenza build).
// Consuma l'API FastAPI di `saas/main.py`. Il token JWT è salvato in
// memoria (non in localStorage) per ridurre la superficie di attacco.

const API = ""; // stesso origin del backend (static files serviti da FastAPI)

let accessToken = null;
let refreshToken = null;
let currentUser = null;

// ------------------------------------------------------------------ #
//  Utility
// ------------------------------------------------------------------ #
async function api(path, options = {}) {
  const headers = options.headers || {};
  headers["Content-Type"] = "application/json";
  if (accessToken) headers["Authorization"] = "Bearer " + accessToken;

  const res = await fetch(API + path, { ...options, headers });
  if (res.status === 401 && accessToken) {
    // tentativo di refresh una sola volta
    const ok = await tryRefresh();
    if (ok) return api(path, options);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch (_) {}
    throw new Error(detail);
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res;
}

async function tryRefresh() {
  if (!refreshToken) return false;
  try {
    const data = await fetch(API + "/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    }).then((r) => r.json());
    if (data.access_token) {
      accessToken = data.access_token;
      refreshToken = data.refresh_token;
      return true;
    }
  } catch (_) {}
  return false;
}

function $(id) { return document.getElementById(id); }
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "<", ">": ">", "'": "&quot;", "'": "&#39;" }[c]));
}
// Decodifica una stringa base64url (RFC 7515) senza padding, come quella
// emessa da PyJWT. `atob` richiede lunghezza multipla di 4 → riaggiunge '='.
function b64url_decode(str) {
  const b64 = str.replace(/-/g, "+").replace(/_/g, "/");
  const pad = b64.length % 4;
  return atob(pad ? b64 + "=".repeat(4 - pad) : b64);
}

// ------------------------------------------------------------------ #
//  Auth / vista
// ------------------------------------------------------------------ #
function showLogin() {
  accessToken = refreshToken = currentUser = null;
  $("view-login").style.display = "flex";
  $("view-app").style.display = "none";
}

function showApp() {
  $("view-login").style.display = "none";
  $("view-app").style.display = "flex";
  $("user-email").textContent = currentUser?.email || "";
  $("user-role").textContent = currentUser?.role || "";
  // Mostra/nasconde le voci admin
  const isAdmin = currentUser?.role === "admin";
  document.querySelectorAll(".admin-only").forEach((el) => {
    el.style.display = isAdmin ? "block" : "none";
  });
  switchView("dashboard");
}

function switchView(view) {
  document.querySelectorAll(".nav-item").forEach((b) =>
    b.classList.toggle("active", b.dataset.view === view));
  document.querySelectorAll(".panel").forEach((p) =>
    p.classList.toggle("active", p.id === "view-" + view));
  if (view === "dashboard") loadDashboard();
  if (view === "dipendenti") loadDipendenti();
  if (view === "lotti") loadLotti();
  if (view === "menu") loadMenu();
  if (view === "printjobs") loadPrintJobs();
}

// ------------------------------------------------------------------ #
//  Login
// ------------------------------------------------------------------ #
async function doLogin(email, password) {
  const data = await fetch(API + "/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  }).then((r) => r.json());
  if (!data.access_token) throw new Error("Credenziali non valide");
  accessToken = data.access_token;
  refreshToken = data.refresh_token;
  // Il server restituisce email/ruolo/tenant_id direttamente nella risposta:
  // il frontend NON deve decodificare il JWT (piu' robusto e sicuro).
  currentUser = {
    email: data.email,
    role: data.ruolo,
    tenant_id: data.tenant_id,
  };
  showApp();
}

// ------------------------------------------------------------------ #
//  Dashboard
// ------------------------------------------------------------------ #
async function loadDashboard() {
  try {
    const [dip, lotti, jobs] = await Promise.all([
      api("/api/v1/dipendenti"),
      api("/api/v1/lotti/aperti"),
      api("/api/v1/print-jobs"),
    ]);
    $("stat-dip").textContent = Array.isArray(dip) ? dip.length : 0;
    $("stat-lotti").textContent = Array.isArray(lotti) ? lotti.length : 0;
    $("stat-jobs").textContent = Array.isArray(jobs) ? jobs.length : 0;
  } catch (e) {
    $("stat-dip").textContent = "—";
    $("stat-lotti").textContent = "—";
    $("stat-jobs").textContent = "—";
  }
}

async function doEanLookup() {
  const code = $("ean-input").value.trim();
  $("ean-result").textContent = "";
  if (!code) return;
  try {
    const p = await api("/api/v1/prodotti/ean/" + encodeURIComponent(code));
    $("ean-result").textContent = JSON.stringify(p, null, 2);
  } catch (e) {
    $("ean-result").textContent = "Errore: " + e.message;
  }
}

// ------------------------------------------------------------------ #
//  Dipendenti
// ------------------------------------------------------------------ #
async function loadDipendenti() {
  try {
    const list = await api("/api/v1/dipendenti");
    const tbody = $("dip-tbody");
    tbody.innerHTML = list.length
      ? list.map((d) => `
        <tr>
          <td>${esc(d.id)}</td>
          <td>${esc(d.nome)}</td>
          <td>${esc(d.email)}</td>
          <td>${esc(d.reparto_nome ?? "")}</td>
          <td class="row-actions">
            <button class="btn ghost" onclick="editDip(${d.id})">Modifica</button>
            <button class="btn danger" onclick="delDip(${d.id})">Elimina</button>
          </td>
        </tr>`).join("")
      : '<tr><td colspan="5" class="empty">Nessun dipendente</td></tr>';
  } catch (e) {
    $("dip-tbody").innerHTML = `<tr><td colspan="5" class="empty">${esc(e.message)}</td></tr>`;
  }
}

function nuovaDip() {
  $("dip-id").value = "";
  $("dip-nome").value = "";
  $("dip-email").value = "";
  $("dip-reparto").value = "";
  $("dip-form-title").textContent = "Nuovo dipendente";
  $("dip-error").textContent = "";
  $("dip-form").style.display = "block";
}

function editDip(id) {
  // rileggiamo dal server per dati freschi
  api("/api/v1/dipendenti").then((list) => {
    const d = list.find((x) => x.id === id);
    if (!d) return;
    $("dip-id").value = d.id;
    $("dip-nome").value = d.nome;
    $("dip-email").value = d.email;
    $("dip-reparto").value = d.reparto ?? "";
    $("dip-form-title").textContent = "Modifica dipendente #" + d.id;
    $("dip-error").textContent = "";
    $("dip-form").style.display = "block";
  });
}

async function salvaDip() {
  $("dip-error").textContent = "";
  const id = $("dip-id").value;
  const payload = {
    nome: $("dip-nome").value,
    email: $("dip-email").value,
    reparto: $("dip-reparto").value === "" ? null : Number($("dip-reparto").value),
  };
  try {
    if (id) {
      await api("/api/v1/dipendenti/" + id, { method: "PUT", body: JSON.stringify(payload) });
    } else {
      await api("/api/v1/dipendenti", { method: "POST", body: JSON.stringify(payload) });
    }
    $("dip-form").style.display = "none";
    loadDipendenti();
  } catch (e) {
    $("dip-error").textContent = e.message;
  }
}

async function delDip(id) {
  if (!confirm("Eliminare il dipendente #" + id + "?")) return;
  try {
    await api("/api/v1/dipendenti/" + id, { method: "DELETE" });
    loadDipendenti();
  } catch (e) {
    alert(e.message);
  }
}

// ------------------------------------------------------------------ #
//  Lotti
// ------------------------------------------------------------------ #
async function loadLotti() {
  try {
    const list = await api("/api/v1/lotti/aperti");
    $("lotti-tbody").innerHTML = list.length
      ? list.map((l) => `
        <tr>
          <td>${esc(l.number ?? l.progressivo_acq)}</td>
          <td>${esc(l.fornit ?? l.fornitore)}</td>
          <td>${esc(l.name ?? l.prodotto)}</td>
          <td>${esc(l.peso ?? l.residuo)}</td>
        </tr>`).join("")
      : '<tr><td colspan="4" class="empty">Nessun lotto aperto</td></tr>';
  } catch (e) {
    $("lotti-tbody").innerHTML = `<tr><td colspan="4" class="empty">${esc(e.message)}</td></tr>`;
  }
}

// ------------------------------------------------------------------ #
//  Menu
// ------------------------------------------------------------------ #
async function loadMenu() {
  const box = $("menu-content");
  box.innerHTML = '<p class="empty">Caricamento…</p>';
  try {
    const data = await api("/api/v1/menu");
    // il service può restituire una struttura {primi, secondi, contorni} o una lista
    let groups;
    if (Array.isArray(data)) {
      groups = { "Prodotti": data };
    } else {
      groups = {};
      for (const key of ["primi", "secondi", "contorni"]) {
        if (Array.isArray(data[key])) groups[key] = data[key];
      }
      if (Object.keys(groups).length === 0) groups = data;
    }
    const labels = { primi: "Primi", secondi: "Secondi", contorni: "Contorni" };
    box.innerHTML = Object.entries(groups).map(([k, items]) => `
      <h3>${esc(labels[k] || k)}</h3>
      <ul>${items.map((it) => `<li>${esc(it.prodotto || it.name)} — <span class="text-dim">${esc(it.plu || "")}</span></li>`).join("")}</ul>
    `).join("");
  } catch (e) {
    box.innerHTML = `<p class="empty">Errore: ${esc(e.message)}</p>`;
  }
}

// ------------------------------------------------------------------ #
//  Stampa (DDT / scontrino / etichetta)
// ------------------------------------------------------------------ #
function switchTab(tab) {
  document.querySelectorAll(".tab-btn").forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
  document.querySelectorAll(".tab-panel").forEach((p) => p.classList.toggle("active", p.id === "tab-" + tab));
}

function addDdtRiga() {
  const box = $("ddt-righe");
  const div = document.createElement("div");
  div.className = "row ddt-riga";
  div.innerHTML = `
    <label>Prodotto <input class="ddt-prodotto" /></label>
    <label>Taglio <input class="ddt-taglio" /></label>
    <label>Qtà <input class="ddt-qta" /></label>
    <label>Peso <input class="ddt-peso" /></label>
  `;
  box.appendChild(div);
}

async function generaDdt() {
  const righe = [...document.querySelectorAll(".ddt-riga")].map((r) => ({
    prodotto: r.querySelector(".ddt-prodotto").value,
    taglio: r.querySelector(".ddt-taglio").value,
    quantita: r.querySelector(".ddt-qta").value,
    peso: r.querySelector(".ddt-peso").value,
  }));
  const payload = {
    numero: $("ddt-numero").value,
    data: $("ddt-data").value,
    fornitore: $("ddt-fornitore").value,
    righe,
  };
  await downloadPost("/api/v1/ddt", payload, "ddt_" + (payload.numero || "x") + ".pdf");
}

function addScoRiga() {
  const box = $("sco-righe");
  const div = document.createElement("div");
  div.className = "row sco-riga";
  div.innerHTML = `
    <label>Descrizione <input class="sco-desc" /></label>
    <label>Prezzo <input class="sco-prezzo" /></label>
    <label>Qtà <input class="sco-qta" /></label>
  `;
  box.appendChild(div);
}

async function generaScontrino() {
  const righe = [...document.querySelectorAll(".sco-riga")].map((r) => ({
    descrizione: r.querySelector(".sco-desc").value,
    prezzo: r.querySelector(".sco-prezzo").value,
    qta: r.querySelector(".sco-qta").value,
  }));
  const payload = {
    testata: $("sco-testata").value,
    righe,
    totale: $("sco-totale").value,
    iva: $("sco-iva").value,
  };
  await downloadPost("/api/v1/scontrino", payload, "scontrino.bin");
}

async function generaEtichetta() {
  const payload = {
    plu: $("et-plu").value,
    prodotto: $("et-prodotto").value,
    prezzo_kg: $("et-prezzo").value,
    ingredienti: $("et-ingredienti").value,
    codice: $("et-codice").value,
  };
  await downloadPost("/api/v1/etichetta", payload, "etichetta_" + (payload.plu || "x") + ".pdf");
}

async function downloadPost(path, body, filename) {
  const headers = { "Content-Type": "application/json" };
  if (accessToken) headers["Authorization"] = "Bearer " + accessToken;
  const res = await fetch(API + path, { method: "POST", headers, body: JSON.stringify(body) });
  if (!res.ok) {
    let d = res.statusText;
    try { d = (await res.json()).detail || d; } catch (_) {}
    alert("Errore: " + d);
    return;
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// ------------------------------------------------------------------ #
//  Coda di stampa
// ------------------------------------------------------------------ #
async function loadPrintJobs() {
  try {
    const jobs = await api("/api/v1/print-jobs");
    $("jobs-tbody").innerHTML = jobs.length
      ? jobs.map((j) => `
        <tr>
          <td>${esc(j.id)}</td>
          <td>${esc(j.tipo)}</td>
          <td><span class="role-badge">${esc(j.stato)}</span></td>
          <td>${esc(j.creato_il)}</td>
          <td><code>${esc(j.payload)}</code></td>
        </tr>`).join("")
      : '<tr><td colspan="5" class="empty">Nessun job di stampa</td></tr>';
  } catch (e) {
    $("jobs-tbody").innerHTML = `<tr><td colspan="5" class="empty">${esc(e.message)}</td></tr>`;
  }
}

// ------------------------------------------------------------------ #
//  Admin
// ------------------------------------------------------------------ #
async function creaUtente() {
  $("admin-error").textContent = "";
  try {
    await api("/api/v1/utenti", {
      method: "POST",
      body: JSON.stringify({
        email: $("usr-email").value,
        password: $("usr-password").value,
        ruolo: $("usr-ruolo").value,
      }),
    });
    $("usr-email").value = "";
    $("usr-password").value = "";
    alert("Utente creato");
  } catch (e) {
    $("admin-error").textContent = e.message;
  }
}

async function registraDispositivo() {
  $("dev-result").textContent = "";
  try {
    const data = await api("/api/v1/dispositivi", {
      method: "POST",
      body: JSON.stringify({
        nome: $("dev-nome").value,
        stampante_dymo: $("dev-dymo").value,
        stampante_termica: $("dev-term").value,
      }),
    });
    $("dev-result").textContent = JSON.stringify(data, null, 2);
  } catch (e) {
    $("dev-result").textContent = "Errore: " + e.message;
  }
}

// ------------------------------------------------------------------ #
//  Eventi
// ------------------------------------------------------------------ #
document.addEventListener("DOMContentLoaded", () => {
  // Login
  $("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    $("login-error").textContent = "";
    try {
      await doLogin($("login-email").value, $("login-password").value);
    } catch (err) {
      $("login-error").textContent = err.message;
    }
  });

  $("btn-logout").addEventListener("click", showLogin);

  // Navigazione
  document.querySelectorAll(".nav-item").forEach((b) =>
    b.addEventListener("click", () => switchView(b.dataset.view)));

  // Dashboard
  $("btn-ean").addEventListener("click", doEanLookup);
  $("ean-input").addEventListener("keydown", (e) => { if (e.key === "Enter") doEanLookup(); });

  // Dipendenti
  $("btn-nuovo-dip").addEventListener("click", nuovaDip);
  $("btn-save-dip").addEventListener("click", salvaDip);
  $("btn-cancel-dip").addEventListener("click", () => ($("dip-form").style.display = "none"));

  // Stampa tabs
  document.querySelectorAll(".tab-btn").forEach((b) =>
    b.addEventListener("click", () => switchTab(b.dataset.tab)));
  $("btn-add-riga").addEventListener("click", addDdtRiga);
  $("btn-gen-ddt").addEventListener("click", generaDdt);
  $("btn-add-sco").addEventListener("click", addScoRiga);
  $("btn-gen-sco").addEventListener("click", generaScontrino);
  $("btn-gen-et").addEventListener("click", generaEtichetta);

  // Coda stampa
  $("btn-refresh-jobs").addEventListener("click", loadPrintJobs);

  // Admin
  $("btn-crea-utente").addEventListener("click", creaUtente);
  $("btn-crea-dev").addEventListener("click", registraDispositivo);

  // Riga DDT iniziale + riga scontrino iniziale
  addDdtRiga();
  addScoRiga();

  showLogin();
});
