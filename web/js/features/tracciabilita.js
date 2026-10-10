import { api } from "../api/client.js";
import { $, esc } from "../core/dom.js";

let articoli = [];
let lotti = [];
let lottiCaricati = false;

function dataLocaleISO() {
  const oggi = new Date();
  return `${oggi.getFullYear()}-${String(oggi.getMonth() + 1).padStart(2, "0")}-${String(oggi.getDate()).padStart(2, "0")}`;
}

function formattaData(value) {
  if (!value) return "—";
  const data = String(value).slice(0, 10);
  const parsed = new Date(`${data}T00:00:00`);
  return Number.isNaN(parsed.getTime()) ? data : parsed.toLocaleDateString("it-IT");
}

function formattaQuantita(value, unita = "") {
  const numero = Number(value);
  const quantita = Number.isFinite(numero)
    ? new Intl.NumberFormat("it-IT", { maximumFractionDigits: 3 }).format(numero)
    : String(value ?? "—");
  return unita ? `${quantita} ${unita}` : quantita;
}

function impostaMessaggio(id, messaggio = "", successo = false) {
  const elemento = $(id);
  elemento.textContent = messaggio;
  elemento.classList.toggle("success", successo);
}

function creaOpzione(value, label) {
  const option = document.createElement("option");
  option.value = String(value);
  option.textContent = label;
  return option;
}

function articoliAttivi() {
  return articoli.filter((articolo) => articolo.attivo);
}

function riempiSelectArticoli(select) {
  const selected = select.value;
  select.replaceChildren(creaOpzione("", "Seleziona articolo"));
  articoliAttivi().forEach((articolo) => {
    select.appendChild(creaOpzione(
      articolo.id,
      `${articolo.nome}${articolo.codice ? ` · ${articolo.codice}` : ""} (${articolo.unita_misura})`,
    ));
  });
  select.value = selected;
}

function riempiSelectLotti(select) {
  const selected = select.value;
  select.replaceChildren(creaOpzione("", "Seleziona lotto"));
  lotti.filter((lotto) => Number(lotto.quantita_disponibile) > 0).forEach((lotto) => {
    select.appendChild(creaOpzione(
      lotto.id,
      `${lotto.codice_lotto} · ${lotto.articolo} — disponibili ${formattaQuantita(lotto.quantita_disponibile, lotto.unita_misura)}`,
    ));
  });
  select.value = selected;
}

function aggiornaSelettoriRighe() {
  document.querySelectorAll('.trace-line select[data-field="articolo_id"]').forEach(riempiSelectArticoli);
  document.querySelectorAll('.trace-line select[data-field="lotto_id"]').forEach(riempiSelectLotti);
}

function creaRiga(containerId, fields, selectOptions, removeLabel) {
  const row = document.createElement("div");
  row.className = "trace-line";
  if (containerId === "trace-work-scraps") row.classList.add("trace-line-scrap");

  fields.forEach((field) => {
    const label = document.createElement("label");
    label.textContent = field.label;
    const input = document.createElement(field.options ? "select" : "input");
    input.dataset.field = field.name;
    input.required = field.required !== false;
    if (field.options) {
      field.options.forEach((option) => input.appendChild(creaOpzione(option.value, option.label)));
    } else {
      input.type = field.type || "number";
      input.min = field.min || "0.001";
      input.step = field.step || "0.001";
      input.inputMode = "decimal";
    }
    label.appendChild(input);
    row.appendChild(label);
  });

  if (selectOptions) {
    const select = row.querySelector("select[data-field]");
    if (select) selectOptions(select);
  }

  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "btn danger";
  remove.textContent = "Rimuovi";
  remove.setAttribute("aria-label", removeLabel);
  remove.addEventListener("click", () => row.remove());
  row.appendChild(remove);
  $(containerId).appendChild(row);
  return row;
}

function aggiungiRigaIngresso() {
  creaRiga(
    "trace-ingress-lines",
    [
      {
        name: "articolo_id",
        label: "Articolo",
        options: [{ value: "", label: "Seleziona articolo" }],
      },
      { name: "quantita", label: "Quantità" },
    ],
    (select) => riempiSelectArticoli(select),
    "Rimuovi riga ingresso",
  );
}

function aggiungiRigaInput() {
  creaRiga(
    "trace-work-inputs",
    [
      {
        name: "lotto_id",
        label: "Lotto da consumare",
        options: [{ value: "", label: "Seleziona lotto" }],
      },
      { name: "quantita", label: "Quantità da consumare" },
    ],
    riempiSelectLotti,
    "Rimuovi lotto input",
  );
}

function aggiungiRigaOutput() {
  creaRiga(
    "trace-work-outputs",
    [
      {
        name: "articolo_id",
        label: "Articolo prodotto",
        options: [{ value: "", label: "Seleziona articolo" }],
      },
      { name: "quantita", label: "Quantità prodotta" },
    ],
    (select) => riempiSelectArticoli(select),
    "Rimuovi prodotto output",
  );
}

function aggiungiRigaScarto() {
  creaRiga(
    "trace-work-scraps",
    [
      { name: "descrizione", label: "Descrizione", type: "text" },
      { name: "quantita", label: "Quantità" },
      {
        name: "unita_misura",
        label: "Unità",
        options: [{ value: "kg", label: "kg" }, { value: "pz", label: "pz" }],
      },
    ],
    null,
    "Rimuovi scarto",
  );
  const descrizione = $("trace-work-scraps").lastElementChild.querySelector('[data-field="descrizione"]');
  descrizione.maxLength = 120;
  descrizione.minLength = 1;
}

function leggiRighe(containerId, fields) {
  return [...$(containerId).querySelectorAll(".trace-line")].map((row) => {
    const result = {};
    fields.forEach((field) => {
      const value = row.querySelector(`[data-field="${field}"]`).value.trim();
      result[field] = field === "descrizione" || field === "unita_misura"
        ? value
        : field === "articolo_id" || field === "lotto_id" ? Number(value) : value;
    });
    return result;
  });
}

function renderArticoli() {
  const tbody = $("trace-articles-tbody");
  tbody.innerHTML = articoli.length
    ? articoli.map((articolo) => `
      <tr>
        <td>${esc(articolo.codice || "—")}</td>
        <td>${esc(articolo.nome)}</td>
        <td>${esc(articolo.categoria || "—")}</td>
        <td>${esc(articolo.unita_misura)}</td>
        <td>${articolo.attivo ? "Attivo" : "Disattivato"}</td>
      </tr>`).join("")
    : '<tr><td colspan="5" class="empty">Nessun articolo. Aggiungine uno per registrare ingressi e lavorazioni.</td></tr>';
}

function renderLotti() {
  const query = $("trace-search").value.trim().toLocaleLowerCase("it");
  const visibili = lotti.filter((lotto) => [
    lotto.codice_lotto,
    lotto.articolo,
    lotto.tipo_lotto,
  ].some((value) => String(value ?? "").toLocaleLowerCase("it").includes(query)));
  const tbody = $("trace-lots-tbody");
  tbody.innerHTML = visibili.length
    ? visibili.map((lotto) => `
      <tr>
        <td><strong>${esc(lotto.codice_lotto)}</strong></td>
        <td>${esc(lotto.articolo)}</td>
        <td><span class="trace-type trace-type-${esc(lotto.tipo_lotto)}">${lotto.tipo_lotto === "A" ? "Acquisto" : "Produzione"}</span></td>
        <td>${esc(formattaData(lotto.data_creazione))}</td>
        <td>${esc(formattaQuantita(lotto.quantita_disponibile, lotto.unita_misura))}</td>
        <td><button class="btn ghost trace-detail-button" type="button" data-lotto-id="${Number(lotto.id)}">Traccia</button></td>
      </tr>`).join("")
    : '<tr><td colspan="6" class="empty">Nessun lotto corrisponde ai filtri.</td></tr>';

  tbody.querySelectorAll("[data-lotto-id]").forEach((button) => {
    button.addEventListener("click", () => mostraDettaglioLotto(button.dataset.lottoId));
  });
}

function appendTesto(parent, tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  element.textContent = text;
  parent.appendChild(element);
  return element;
}

function renderDettaglio(dettaglio) {
  const container = $("trace-detail");
  container.replaceChildren();
  container.hidden = false;

  const header = document.createElement("div");
  header.className = "trace-detail-head";
  const heading = document.createElement("div");
  appendTesto(heading, "p", "eyebrow", "Genealogia del lotto");
  appendTesto(heading, "h3", "", dettaglio.codice_lotto);
  appendTesto(heading, "p", "trace-help", `${dettaglio.articolo} · ${formattaData(dettaglio.data_creazione)}`);
  header.appendChild(heading);
  const close = document.createElement("button");
  close.type = "button";
  close.className = "btn ghost";
  close.textContent = "Chiudi";
  close.addEventListener("click", () => { container.hidden = true; });
  header.appendChild(close);
  container.appendChild(header);

  const facts = document.createElement("div");
  facts.className = "trace-facts";
  [
    ["Tipo", dettaglio.tipo_lotto === "A" ? "Ingresso" : "Produzione"],
    ["Quantità iniziale", formattaQuantita(dettaglio.quantita_iniziale, dettaglio.unita_misura)],
    ["Disponibile", formattaQuantita(dettaglio.quantita_disponibile, dettaglio.unita_misura)],
  ].forEach(([label, value]) => {
    const fact = document.createElement("div");
    appendTesto(fact, "span", "", label);
    appendTesto(fact, "strong", "", value);
    facts.appendChild(fact);
  });
  container.appendChild(facts);

  if (dettaglio.documento_ingresso) {
    const ingresso = dettaglio.documento_ingresso;
    const origin = document.createElement("div");
    origin.className = "trace-detail-block";
    appendTesto(origin, "h4", "", "Documento di ingresso");
    appendTesto(origin, "p", "", `${formattaData(ingresso.data)} · DDT ${ingresso.numero_ddt || "—"} · ${ingresso.fornitore}`);
    container.appendChild(origin);
  }

  const lavorazione = dettaglio.lavorazione;
  if (lavorazione) {
    const work = document.createElement("div");
    work.className = "trace-detail-block";
    appendTesto(work, "h4", "", `Lavorazione · ${formattaData(lavorazione.data)}`);
    appendTesto(work, "p", "trace-help", [lavorazione.descrizione, lavorazione.operatore].filter(Boolean).join(" · ") || "Nessuna descrizione");
    [
      ["Input consumati", lavorazione.input, (row) => `${row.codice_lotto} · ${row.articolo} — ${formattaQuantita(row.quantita)}`],
      ["Output prodotti", lavorazione.output, (row) => `${row.codice_lotto} · ${row.articolo} — ${formattaQuantita(row.quantita)}`],
      ["Scarti", lavorazione.scarti, (row) => `${row.descrizione} — ${formattaQuantita(row.quantita, row.unita_misura)}`],
    ].forEach(([title, rows, getText]) => {
      appendTesto(work, "h5", "", title);
      const list = document.createElement("ul");
      if (rows.length) rows.forEach((row) => appendTesto(list, "li", "", getText(row)));
      else appendTesto(list, "li", "trace-muted", "Nessun dato");
      work.appendChild(list);
    });
    container.appendChild(work);
  }

  const movements = document.createElement("div");
  movements.className = "trace-detail-block";
  appendTesto(movements, "h4", "", "Movimenti");
  const list = document.createElement("ul");
  if (dettaglio.movimenti.length) {
    dettaglio.movimenti.forEach((movimento) => {
      appendTesto(
        list,
        "li",
        "",
        `${movimento.tipo} · ${formattaQuantita(movimento.quantita_delta, dettaglio.unita_misura)} · ${formattaData(movimento.creato_il)}`,
      );
    });
  } else {
    appendTesto(list, "li", "trace-muted", "Nessun movimento registrato.");
  }
  movements.appendChild(list);
  container.appendChild(movements);
  container.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function mostraDettaglioLotto(lottoId) {
  impostaMessaggio("trace-lots-error");
  try {
    const dettaglio = await api(`/api/v1/tracciabilita/lotti/${encodeURIComponent(lottoId)}`);
    renderDettaglio(dettaglio);
  } catch (error) {
    impostaMessaggio("trace-lots-error", `Impossibile caricare il dettaglio: ${error.message}`);
  }
}

export async function loadTracciabilita() {
  impostaMessaggio("trace-lots-error");
  impostaMessaggio("trace-articles-error");
  const soloDisponibili = $("trace-only-available").checked;
  const risultati = await Promise.allSettled([
    api("/api/v1/articoli"),
    api(`/api/v1/tracciabilita/lotti${soloDisponibili ? "?solo_disponibili=true" : ""}`),
  ]);

  if (risultati[0].status === "fulfilled") {
    articoli = risultati[0].value;
    renderArticoli();
  } else {
    articoli = [];
    impostaMessaggio("trace-articles-error", `Impossibile caricare gli articoli: ${risultati[0].reason?.message || risultati[0].reason}`);
    $("trace-articles-tbody").innerHTML = '<tr><td colspan="5" class="empty">Errore nel caricamento degli articoli.</td></tr>';
  }
  if (risultati[1].status === "fulfilled") {
    lotti = risultati[1].value;
    lottiCaricati = true;
    renderLotti();
  } else {
    lotti = [];
    lottiCaricati = false;
    impostaMessaggio("trace-lots-error", `Impossibile caricare i lotti: ${risultati[1].reason?.message || risultati[1].reason}`);
    $("trace-lots-tbody").innerHTML = '<tr><td colspan="6" class="empty">Errore nel caricamento dei lotti.</td></tr>';
  }
  aggiornaSelettoriRighe();
}

function attivaTab(nome) {
  document.querySelectorAll("[data-trace-tab]").forEach((button) => {
    const active = button.dataset.traceTab === nome;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", String(active));
  });
  document.querySelectorAll("[data-trace-section]").forEach((section) => {
    const active = section.dataset.traceSection === nome;
    section.hidden = !active;
    section.classList.toggle("active", active);
  });
  if (nome === "lavorazione" && !lottiCaricati) loadTracciabilita();
}

function configuraFormArticolo() {
  $("btn-trace-new-article").addEventListener("click", () => {
    $("trace-article-form").hidden = false;
    $("trace-article-name").focus();
  });
  $("btn-trace-cancel-article").addEventListener("click", () => {
    $("trace-article-form").reset();
    $("trace-article-form").hidden = true;
    impostaMessaggio("trace-article-form-error");
  });
  $("trace-article-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    impostaMessaggio("trace-article-form-error");
    const button = event.currentTarget.querySelector('[type="submit"]');
    button.disabled = true;
    try {
      await api("/api/v1/articoli", {
        method: "POST",
        body: JSON.stringify({
          nome: $("trace-article-name").value.trim(),
          codice: $("trace-article-code").value.trim() || null,
          categoria: $("trace-article-category").value.trim() || null,
          unita_misura: $("trace-article-unit").value,
        }),
      });
      $("trace-article-form").reset();
      $("trace-article-form").hidden = true;
      await loadTracciabilita();
    } catch (error) {
      impostaMessaggio("trace-article-form-error", `Impossibile salvare l'articolo: ${error.message}`);
    } finally {
      button.disabled = false;
    }
  });
}

function configuraFormIngresso() {
  $("trace-ingress-date").value = dataLocaleISO();
  aggiungiRigaIngresso();
  $("btn-trace-add-ingress-line").addEventListener("click", aggiungiRigaIngresso);
  $("trace-ingress-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    impostaMessaggio("trace-ingress-error");
    const righe = leggiRighe("trace-ingress-lines", ["articolo_id", "quantita"]);
    if (!righe.length) {
      impostaMessaggio("trace-ingress-error", "Aggiungi almeno un articolo all'ingresso.");
      return;
    }
    const button = form.querySelector('[type="submit"]');
    button.disabled = true;
    try {
      const result = await api("/api/v1/tracciabilita/ingressi", {
        method: "POST",
        body: JSON.stringify({
          data: $("trace-ingress-date").value,
          numero_ddt: $("trace-ingress-ddt").value.trim(),
          fornitore: $("trace-ingress-supplier").value.trim(),
          righe,
        }),
      });
      const codici = result.lotti.map((lotto) => lotto.codice_lotto).join(", ");
      impostaMessaggio("trace-ingress-error", `Ingresso registrato. Lotti creati: ${codici}`, true);
      form.reset();
      $("trace-ingress-date").value = dataLocaleISO();
      $("trace-ingress-lines").replaceChildren();
      await loadTracciabilita();
      aggiungiRigaIngresso();
    } catch (error) {
      impostaMessaggio("trace-ingress-error", `Impossibile registrare l'ingresso: ${error.message}`);
    } finally {
      button.disabled = false;
    }
  });
}

function configuraFormLavorazione() {
  $("trace-work-date").value = dataLocaleISO();
  aggiungiRigaInput();
  aggiungiRigaOutput();
  $("btn-trace-add-input").addEventListener("click", aggiungiRigaInput);
  $("btn-trace-add-output").addEventListener("click", aggiungiRigaOutput);
  $("btn-trace-add-scrap").addEventListener("click", aggiungiRigaScarto);
  $("trace-work-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    impostaMessaggio("trace-work-error");
    const input = leggiRighe("trace-work-inputs", ["lotto_id", "quantita"]);
    const output = leggiRighe("trace-work-outputs", ["articolo_id", "quantita"]);
    const scarti = leggiRighe("trace-work-scraps", ["descrizione", "quantita", "unita_misura"]);
    if (!input.length || !output.length) {
      impostaMessaggio("trace-work-error", "La lavorazione richiede almeno un lotto in ingresso e un prodotto in uscita.");
      return;
    }
    const button = form.querySelector('[type="submit"]');
    button.disabled = true;
    try {
      const result = await api("/api/v1/tracciabilita/lavorazioni", {
        method: "POST",
        body: JSON.stringify({
          data: $("trace-work-date").value,
          descrizione: $("trace-work-description").value.trim(),
          operatore: $("trace-work-operator").value.trim() || null,
          input,
          output,
          scarti,
        }),
      });
      const codici = result.lotti.map((lotto) => lotto.codice_lotto).join(", ");
      impostaMessaggio("trace-work-error", `Lavorazione registrata. Lotti prodotti: ${codici}`, true);
      form.reset();
      $("trace-work-date").value = dataLocaleISO();
      $("trace-work-inputs").replaceChildren();
      $("trace-work-outputs").replaceChildren();
      $("trace-work-scraps").replaceChildren();
      await loadTracciabilita();
      aggiungiRigaInput();
      aggiungiRigaOutput();
    } catch (error) {
      impostaMessaggio("trace-work-error", `Impossibile registrare la lavorazione: ${error.message}`);
    } finally {
      button.disabled = false;
    }
  });
}

export function initTracciabilita() {
  document.querySelectorAll("[data-trace-tab]").forEach((button) => {
    button.addEventListener("click", () => attivaTab(button.dataset.traceTab));
  });
  $("trace-search").addEventListener("input", renderLotti);
  $("trace-only-available").addEventListener("change", loadTracciabilita);
  $("btn-trace-refresh").addEventListener("click", loadTracciabilita);
  configuraFormArticolo();
  configuraFormIngresso();
  configuraFormLavorazione();
}
