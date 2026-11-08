import { api, apiGetBlob } from "../api/client.js";
import { $, esc } from "../core/dom.js";

let articoli = [];
let lotti = [];
let lottiDisponibili = [];
let dipendenti = [];
let ricette = [];
let lottiCaricati = false;
let cronologiaDettaglio = [];
let dettaglioCorrente = null;

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
  const lottiFefo = lottiFefoPerArticolo();

  select.replaceChildren(creaOpzione("", "Seleziona lotto (FEFO)"));
  lottiFefo.forEach((lotto) => {
    const dataTipo = lotto.data_scadenza ? "Scadenza" : lotto.data_tmc ? "TMC" : "";
    const dataValore = lotto.data_scadenza || lotto.data_tmc;
    const scadenza = dataValore
      ? ` · ${dataTipo}: ${formattaData(dataValore)}${lotto.data_tmc && String(lotto.data_tmc).slice(0, 10) < dataLocaleISO() ? " (superato, richiede conferma)" : ""}`
      : " · senza scadenza";
    select.appendChild(creaOpzione(
      lotto.id,
      `${lotto.codice_lotto} · ${lotto.articolo}${lotto.categoria ? ` · ${lotto.categoria}` : ""} — disponibili ${formattaQuantita(lotto.quantita_disponibile, lotto.unita_misura)}${scadenza}`,
    ));
  });
  select.value = lottiFefo.some((lotto) => String(lotto.id) === selected)
    ? selected
    : String(lottiFefo[0]?.id ?? "");
}

function lottiFefoPerArticolo(articoloId = null) {
  const articoliInput = new Set(
    articoli
      .filter((articolo) => articolo.utilizzabile_come_input)
      .map((articolo) => String(articolo.id)),
  );
  return lottiDisponibili
    .filter((lotto) => {
      const scadenza = lotto.data_scadenza ? String(lotto.data_scadenza).slice(0, 10) : "";
      return Number(lotto.quantita_disponibile) > 0
        && articoliInput.has(String(lotto.articolo_id))
        && (articoloId === null || String(lotto.articolo_id) === String(articoloId))
        && (!scadenza || scadenza >= dataLocaleISO());
    })
    .sort((a, b) => {
      const dataA = String(a.data_scadenza || a.data_tmc || "").slice(0, 10);
      const dataB = String(b.data_scadenza || b.data_tmc || "").slice(0, 10);
      if (!dataA && dataB) return 1;
      if (dataA && !dataB) return -1;
      return dataA.localeCompare(dataB)
        || String(a.data_creazione ?? "").localeCompare(String(b.data_creazione ?? ""))
        || Number(a.id) - Number(b.id);
    });
}

function riempiSelectDipendenti(select) {
  const selected = select.value;
  select.replaceChildren(creaOpzione("", "Seleziona operatore"));
  dipendenti.forEach((dipendente) => {
    const nome = [dipendente.nome, dipendente.cognome].filter(Boolean).join(" ");
    select.appendChild(creaOpzione(dipendente.id, nome));
  });
  select.value = selected;
}

function aggiornaSelettoriRighe() {
  document.querySelectorAll('.trace-line select[data-field="articolo_id"]').forEach(riempiSelectArticoli);
  document.querySelectorAll('.trace-line select[data-field="lotto_id"]').forEach(riempiSelectLotti);
  riempiSelectDipendenti($("trace-work-operator"));
}

function riempiSelectRicette() {
  const select = $("trace-work-recipe");
  const selected = select.value;
  select.replaceChildren(creaOpzione("", "Lavorazione manuale"));
  ricette
    .filter((ricetta) => ricetta.attiva)
    .forEach((ricetta) => select.appendChild(creaOpzione(ricetta.id, ricetta.nome)));
  select.value = selected;
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
      if (input.type === "number") {
        input.min = field.min || "0.001";
        input.step = field.step || "0.001";
        input.inputMode = "decimal";
      }
      if (field.value !== undefined) input.value = field.value;
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

function arrotondaQuantita(value) {
  return Math.max(0.001, Math.round(value * 1000) / 1000);
}

function selezionaRicetta(ricetta, targetQuantity) {
  const inputContainer = $("trace-work-inputs");
  const outputContainer = $("trace-work-outputs");
  inputContainer.replaceChildren();
  outputContainer.replaceChildren();
  $("trace-work-confirm-weights").checked = false;

  const quantitaProdotto = Number(targetQuantity);
  const mancanti = [];
  ricetta.ingredienti.forEach((ingrediente) => {
    const quantitaAttesa = ingrediente.tipo_quantita === "percentuale"
      ? quantitaProdotto * Number(ingrediente.valore) / 100
      : quantitaProdotto * Number(ingrediente.valore);
    let daAllocare = arrotondaQuantita(quantitaAttesa);
    const lotti = lottiFefoPerArticolo(ingrediente.articolo_id);
    lotti.forEach((lotto) => {
      if (daAllocare <= 0) return;
      const allocata = Math.min(daAllocare, Number(lotto.quantita_disponibile));
      const quantita = Math.round(allocata * 1000) / 1000;
      if (quantita <= 0) return;
      const descrizione = `${ingrediente.articolo_nome}${ingrediente.obbligatorio ? "" : " (facoltativo)"} · previsto ${formattaQuantita(quantitaAttesa, ingrediente.unita_misura)}`;
      const row = creaRiga(
        "trace-work-inputs",
        [
          {
            name: "lotto_id",
            label: `Lotto FEFO — ${descrizione}`,
            options: [{ value: "", label: "Seleziona lotto" }],
          },
          {
            name: "quantita",
            label: `Quantità reale (${ingrediente.unita_misura})`,
            value: quantita.toFixed(3),
          },
        ],
        riempiSelectLotti,
        "Rimuovi lotto input",
      );
      row.querySelector('[data-field="lotto_id"]').value = String(lotto.id);
      daAllocare = Math.max(0, Math.round((daAllocare - quantita) * 1000) / 1000);
    });
    if (daAllocare > 0) {
      mancanti.push(`${ingrediente.articolo_nome}: ${formattaQuantita(daAllocare, ingrediente.unita_misura)}`);
    }
  });

  const outputRow = creaRiga(
    "trace-work-outputs",
    [
      {
        name: "articolo_id",
        label: `Prodotto — ${ricetta.articolo_nome}`,
        options: [{ value: "", label: "Seleziona articolo" }],
      },
      { name: "quantita", label: `Quantità reale (${ricetta.unita_misura})`, value: quantitaProdotto.toFixed(3) },
      {
        name: "tipo_data",
        label: "Tipo di data",
        required: false,
        options: [
          { value: "", label: "Nessuna data" },
          { value: "scadenza", label: "Scadenza" },
          { value: "tmc", label: "TMC" },
        ],
      },
      { name: "data", label: "Data", type: "date", required: false },
      { name: "origine", label: "Origine dichiarata", type: "text", required: false },
    ],
    (select) => riempiSelectArticoli(select),
    "Rimuovi prodotto output",
  );
  outputRow.querySelector('[data-field="articolo_id"]').value = String(ricetta.articolo_id);

  const aiuto = [
    "Le quantità precompilate sono stime della ricetta: correggi input e prodotto con i pesi reali prima di confermare.",
    mancanti.length ? `Disponibilità FEFO insufficiente per: ${mancanti.join("; ")}.` : "",
    ricetta.ingredienti.some((ingrediente) => !ingrediente.obbligatorio)
      ? "Gli ingredienti facoltativi non usati vanno rimossi."
      : "",
  ].filter(Boolean).join(" ");
  const help = $("trace-work-recipe-help");
  help.textContent = aiuto;
  help.hidden = !aiuto;
}

function applicaRicettaSelezionata() {
  const ricetta = ricette.find((item) => String(item.id) === $("trace-work-recipe").value);
  if (!ricetta) return;
  if (String(ricetta.unita_misura).toLocaleLowerCase("it") !== "kg") {
    impostaMessaggio(
      "trace-work-error",
      "La precompilazione ricetta richiede un articolo prodotto espresso in kg; puoi continuare inserendo manualmente i pesi.",
    );
    return;
  }
  const target = Number($("trace-work-target-quantity").value);
  if (!Number.isFinite(target) || target <= 0) {
    impostaMessaggio("trace-work-error", "Inserisci una quantità prodotto prevista maggiore di zero.");
    $("trace-work-target-quantity").focus();
    return;
  }
  impostaMessaggio("trace-work-error");
  selezionaRicetta(ricetta, target);
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
      {
        name: "tipo_data",
        label: "Tipo di data",
        required: false,
        options: [
          { value: "", label: "Nessuna data" },
          { value: "scadenza", label: "Scadenza" },
          { value: "tmc", label: "TMC" },
        ],
      },
      { name: "data", label: "Data", type: "date", required: false },
      { name: "origine", label: "Origine dichiarata", type: "text", required: false },
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

function creaFatti(entries) {
  const facts = document.createElement("div");
  facts.className = "trace-facts";
  entries.forEach(([label, value]) => {
    const fact = document.createElement("div");
    appendTesto(fact, "span", "", label);
    appendTesto(fact, "strong", "", value);
    facts.appendChild(fact);
  });
  return facts;
}

function creaFormRettifica(dettaglio) {
  if (!["admin", "operatore"].includes(document.body.dataset.role)) return null;

  const form = document.createElement("form");
  form.className = "form-card trace-detail-block";
  appendTesto(form, "h4", "", "Rettifica giacenza");
  appendTesto(
    form,
    "p",
    "trace-help",
    "Inserisci un delta positivo o negativo; la giacenza non può diventare negativa.",
  );

  const deltaLabel = document.createElement("label");
  deltaLabel.textContent = `Delta (${dettaglio.unita_misura})`;
  const deltaInput = document.createElement("input");
  deltaInput.type = "number";
  deltaInput.step = "0.001";
  deltaInput.required = true;
  deltaInput.inputMode = "decimal";
  deltaInput.placeholder = "-0.250";
  deltaLabel.appendChild(deltaInput);
  form.appendChild(deltaLabel);

  const motivoLabel = document.createElement("label");
  motivoLabel.textContent = "Motivo";
  const motivoSelect = document.createElement("select");
  motivoSelect.required = true;
  [
    ["inventario", "Inventario"],
    ["calo", "Calo"],
    ["reso", "Reso"],
    ["errore", "Errore"],
  ].forEach(([value, label]) => motivoSelect.appendChild(creaOpzione(value, label)));
  motivoLabel.appendChild(motivoSelect);
  form.appendChild(motivoLabel);

  const feedback = appendTesto(form, "p", "trace-help", "");
  feedback.setAttribute("role", "status");
  feedback.setAttribute("aria-live", "polite");
  const actions = document.createElement("div");
  actions.className = "row";
  const submit = document.createElement("button");
  submit.type = "submit";
  submit.className = "btn primary";
  submit.textContent = "Registra rettifica";
  actions.appendChild(submit);
  form.appendChild(actions);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    feedback.textContent = "";
    if (!deltaInput.value || Number(deltaInput.value) === 0) {
      feedback.textContent = "Inserisci un delta diverso da zero.";
      return;
    }

    submit.disabled = true;
    try {
      await api(
        `/api/v1/tracciabilita/lotti/${encodeURIComponent(dettaglio.id)}/rettifiche`,
        {
          method: "POST",
          body: JSON.stringify({
            delta: deltaInput.value,
            motivo: motivoSelect.value,
          }),
        },
      );
      await loadTracciabilita();
      await mostraDettaglioLotto(dettaglio.id);
    } catch (error) {
      feedback.textContent = `Impossibile registrare la rettifica: ${error.message}`;
    } finally {
      submit.disabled = false;
    }
  });
  return form;
}

function renderDettaglio(dettaglio) {
  dettaglioCorrente = dettaglio;
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
  const actions = document.createElement("div");
  actions.className = "row";
  const download = document.createElement("button");
  download.type = "button";
  download.className = "btn primary";
  download.textContent = "Scarica scheda PDF";
  download.addEventListener("click", () => scaricaSchedaLotto(dettaglio.id, download));
  actions.appendChild(download);
  const close = document.createElement("button");
  close.type = "button";
  close.className = "btn ghost";
  close.textContent = cronologiaDettaglio.length ? "Indietro" : "Chiudi";
  close.addEventListener("click", () => {
    if (cronologiaDettaglio.length) {
      renderDettaglio(cronologiaDettaglio.pop());
    } else {
      container.hidden = true;
    }
  });
  actions.appendChild(close);
  header.appendChild(actions);
  container.appendChild(header);

  container.appendChild(creaFatti([
    ["Tipo", dettaglio.tipo_lotto === "A" ? "Ingresso" : "Produzione"],
    ["Quantità iniziale", formattaQuantita(dettaglio.quantita_iniziale, dettaglio.unita_misura)],
    ["Disponibile", formattaQuantita(dettaglio.quantita_disponibile, dettaglio.unita_misura)],
  ]));
  const formRettifica = creaFormRettifica(dettaglio);
  if (formRettifica) container.appendChild(formRettifica);

  const metadata = document.createElement("div");
  metadata.className = "trace-detail-block";
  appendTesto(metadata, "h4", "", "Metadati del lotto");
  metadata.appendChild(creaFatti([
    ["Lotto fornitore", dettaglio.lotto_fornitore || "—"],
    ["Origine", dettaglio.origine || "—"],
    ["Scadenza", formattaData(dettaglio.data_scadenza)],
    ["TMC", formattaData(dettaglio.data_tmc)],
    [
      "Temperatura all'ingresso",
      dettaglio.temperatura_ingresso != null
        ? formattaQuantita(dettaglio.temperatura_ingresso, "°C")
        : "—",
    ],
  ]));
  container.appendChild(metadata);

  if (dettaglio.documento_ingresso) {
    const ingresso = dettaglio.documento_ingresso;
    const documentBlock = document.createElement("div");
    documentBlock.className = "trace-detail-block";
    appendTesto(documentBlock, "h4", "", "Documento di ingresso");
    documentBlock.appendChild(creaFatti([
      ["Data ingresso", formattaData(ingresso.data)],
      ["DDT", ingresso.numero_ddt || "—"],
      ["Fornitore", ingresso.fornitore || "—"],
    ]));
    container.appendChild(documentBlock);
  }

  if (dettaglio.note_lotto) {
    const notes = document.createElement("div");
    notes.className = "trace-detail-block";
    appendTesto(notes, "h4", "", "Note del lotto");
    appendTesto(notes, "p", "", dettaglio.note_lotto);
    container.appendChild(notes);
  }

  const lavorazione = dettaglio.lavorazione;
  if (lavorazione) {
    const work = document.createElement("div");
    work.className = "trace-detail-block";
    appendTesto(work, "h4", "", `Lavorazione · ${formattaData(lavorazione.data)}`);
    appendTesto(work, "p", "trace-help", [lavorazione.descrizione, lavorazione.operatore].filter(Boolean).join(" · ") || "Nessuna descrizione");
    [
      ["Output prodotti", lavorazione.output, (row) => `${row.codice_lotto} · ${row.articolo} — ${formattaQuantita(row.quantita)}`],
      ["Scarti", lavorazione.scarti, (row) => `${row.descrizione} — ${formattaQuantita(row.quantita, row.unita_misura)}`],
    ].forEach(([title, rows, getText]) => {
      appendTesto(work, "h5", "", title);
      const list = document.createElement("ul");
      if (rows.length) rows.forEach((row) => appendTesto(list, "li", "", getText(row)));
      else appendTesto(list, "li", "trace-muted", "Nessun dato");
      work.appendChild(list);
    });
    appendTesto(work, "h5", "", "Lotti input consumati");
    const inputList = document.createElement("ul");
    if (lavorazione.input.length) {
      lavorazione.input.forEach((row) => {
        const item = document.createElement("li");
        appendTesto(
          item,
          "span",
          "",
          `${row.codice_lotto} · ${row.articolo} — ${formattaQuantita(row.quantita)}`,
        );
        const open = document.createElement("button");
        open.type = "button";
        open.className = "btn ghost trace-lot-link";
        open.textContent = "Apri lotto";
        open.addEventListener("click", () => mostraDettaglioLotto(row.lotto_id, true));
        item.appendChild(open);
        inputList.appendChild(item);
      });
    } else {
      appendTesto(inputList, "li", "trace-muted", "Nessun lotto input registrato.");
    }
    work.appendChild(inputList);
    container.appendChild(work);
  }

  const forward = document.createElement("div");
  forward.className = "trace-detail-block";
  appendTesto(forward, "h4", "", "Genealogia in avanti");
  if (dettaglio.lavorazioni_successive.length) {
    dettaglio.lavorazioni_successive.forEach((successiva) => {
      appendTesto(forward, "h5", "", `Lavorazione · ${formattaData(successiva.data)}`);
      appendTesto(
        forward,
        "p",
        "trace-help",
        [successiva.descrizione, successiva.operatore].filter(Boolean).join(" · ") || "Nessuna descrizione",
      );
      const outputList = document.createElement("ul");
      if (successiva.output.length) {
        successiva.output.forEach((row) => {
          const item = document.createElement("li");
          appendTesto(
            item,
            "span",
            "",
            `${row.codice_lotto} · ${row.articolo} — ${formattaQuantita(row.quantita, row.unita_misura)}`,
          );
          const open = document.createElement("button");
          open.type = "button";
          open.className = "btn ghost trace-lot-link";
          open.textContent = "Apri lotto";
          open.addEventListener("click", () => mostraDettaglioLotto(row.lotto_id, true));
          item.appendChild(open);
          outputList.appendChild(item);
        });
      } else {
        appendTesto(outputList, "li", "trace-muted", "Nessun lotto prodotto registrato.");
      }
      forward.appendChild(outputList);
    });
  } else {
    appendTesto(forward, "p", "trace-muted", "Nessuna lavorazione successiva registrata.");
  }
  container.appendChild(forward);

  const movements = document.createElement("div");
  movements.className = "trace-detail-block";
  appendTesto(movements, "h4", "", "Movimenti");
  const list = document.createElement("ul");
  if (dettaglio.movimenti.length) {
    dettaglio.movimenti.forEach((movimento) => {
      const motivi = {
        inventario: "Inventario",
        calo: "Calo",
        reso: "Reso",
        errore: "Errore",
      };
      const motivo = movimento.motivo ? ` · ${motivi[movimento.motivo] || movimento.motivo}` : "";
      appendTesto(
        list,
        "li",
        "",
        `${movimento.tipo}${motivo} · ${formattaQuantita(movimento.quantita_delta, dettaglio.unita_misura)} · ${formattaData(movimento.creato_il)}`,
      );
    });
  } else {
    appendTesto(list, "li", "trace-muted", "Nessun movimento registrato.");
  }
  movements.appendChild(list);
  container.appendChild(movements);
  container.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function scaricaSchedaLotto(lottoId, button) {
  impostaMessaggio("trace-lots-error");
  button.disabled = true;
  try {
    const blob = await apiGetBlob(
      `/api/v1/tracciabilita/lotti/${encodeURIComponent(lottoId)}/scheda.pdf`,
    );
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `scheda_lotto_${lottoId}.pdf`;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) {
    impostaMessaggio("trace-lots-error", `Impossibile scaricare la scheda PDF: ${error.message}`);
  } finally {
    button.disabled = false;
  }
}

async function mostraDettaglioLotto(lottoId, daInput = false) {
  impostaMessaggio("trace-lots-error");
  try {
    const dettaglio = await api(`/api/v1/tracciabilita/lotti/${encodeURIComponent(lottoId)}`);
    if (daInput) {
      if (dettaglioCorrente) cronologiaDettaglio.push(dettaglioCorrente);
    } else {
      cronologiaDettaglio = [];
    }
    renderDettaglio(dettaglio);
  } catch (error) {
    impostaMessaggio("trace-lots-error", `Impossibile caricare il dettaglio: ${error.message}`);
  }
}

export async function loadTracciabilita() {
  impostaMessaggio("trace-work-data-error");
  impostaMessaggio("trace-lots-error");
  const soloDisponibili = $("trace-only-available").checked;
  const filtri = new URLSearchParams();
  if (soloDisponibili) filtri.set("solo_disponibili", "true");
  const dataDal = $("trace-date-from").value;
  const dataAl = $("trace-date-to").value;
  if (dataDal) filtri.set("data_dal", dataDal);
  if (dataAl) filtri.set("data_al", dataAl);
  const query = filtri.toString();
  const risultati = await Promise.allSettled([
    api("/api/v1/articoli"),
    api(`/api/v1/tracciabilita/lotti${query ? `?${query}` : ""}`),
    api("/api/v1/tracciabilita/lotti?solo_disponibili=true"),
    api("/api/v1/dipendenti"),
    api("/api/v1/ricette"),
  ]);

  const erroriDati = [];
  if (risultati[0].status === "fulfilled") {
    articoli = risultati[0].value;
  } else {
    articoli = [];
    erroriDati.push(`articoli: ${risultati[0].reason?.message || risultati[0].reason}`);
  }
  if (risultati[1].status === "fulfilled") {
    lotti = risultati[1].value;
    renderLotti();
  } else {
    lotti = [];
    impostaMessaggio("trace-lots-error", `Impossibile caricare i lotti: ${risultati[1].reason?.message || risultati[1].reason}`);
    $("trace-lots-tbody").innerHTML = '<tr><td colspan="6" class="empty">Errore nel caricamento dei lotti.</td></tr>';
  }
  if (risultati[2].status === "fulfilled") {
    lottiDisponibili = risultati[2].value;
  } else {
    lottiDisponibili = [];
    erroriDati.push(`lotti disponibili: ${risultati[2].reason?.message || risultati[2].reason}`);
  }
  if (risultati[3].status === "fulfilled") {
    dipendenti = risultati[3].value;
  } else {
    dipendenti = [];
    erroriDati.push(`dipendenti: ${risultati[3].reason?.message || risultati[3].reason}`);
  }
  if (risultati[4].status === "fulfilled") {
    ricette = risultati[4].value;
  } else {
    ricette = [];
    erroriDati.push(`ricette: ${risultati[4].reason?.message || risultati[4].reason}`);
  }
  riempiSelectRicette();
  lottiCaricati = risultati[1].status === "fulfilled"
    && risultati[2].status === "fulfilled"
    && risultati[4].status === "fulfilled";
  impostaMessaggio(
    "trace-work-data-error",
    erroriDati.length ? `Impossibile caricare i dati per le lavorazioni (${erroriDati.join("; ")}).` : "",
  );
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

function configuraFormLavorazione() {
  $("trace-work-date").value = dataLocaleISO();
  aggiungiRigaInput();
  aggiungiRigaOutput();
  $("btn-trace-add-input").addEventListener("click", aggiungiRigaInput);
  $("btn-trace-add-output").addEventListener("click", aggiungiRigaOutput);
  $("btn-trace-add-scrap").addEventListener("click", aggiungiRigaScarto);
  ["btn-trace-add-input", "btn-trace-add-output"].forEach((id) => {
    $(id).addEventListener("click", () => {
      $("trace-work-confirm-weights").checked = false;
    });
  });
  $("btn-trace-apply-recipe").addEventListener("click", applicaRicettaSelezionata);
  $("trace-work-recipe").addEventListener("change", () => {
    const ricetta = ricette.find((item) => String(item.id) === $("trace-work-recipe").value);
    const help = $("trace-work-recipe-help");
    impostaMessaggio("trace-work-error");
    if (!ricetta) {
      $("trace-work-target-quantity").value = "";
      $("trace-work-confirm-weights").checked = false;
      help.hidden = true;
      return;
    }
    $("trace-work-target-quantity").value = Number(ricetta.resa_attesa).toFixed(3);
    applicaRicettaSelezionata();
  });
  ["trace-work-inputs", "trace-work-outputs"].forEach((containerId) => {
    $(containerId).addEventListener("click", (event) => {
      if (event.target.closest(".btn.danger")) {
        $("trace-work-confirm-weights").checked = false;
      }
    });
    $(containerId).addEventListener("input", () => {
      $("trace-work-confirm-weights").checked = false;
    });
    $(containerId).addEventListener("change", () => {
      $("trace-work-confirm-weights").checked = false;
    });
  });
  $("trace-work-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    impostaMessaggio("trace-work-error");
    let input = leggiRighe("trace-work-inputs", ["lotto_id", "quantita"]);
    const outputRighe = leggiRighe(
      "trace-work-outputs",
      ["articolo_id", "quantita", "tipo_data", "data", "origine"],
    );
    const ricetta = ricette.find((item) => String(item.id) === $("trace-work-recipe").value);
    if (ricetta) {
      const ingredientiPresenti = new Set(
        input
          .map((riga) => lottiDisponibili.find((lotto) => String(lotto.id) === String(riga.lotto_id))?.articolo_id)
          .filter((articoloId) => articoloId !== undefined)
          .map(String),
      );
      const ingredientiMancanti = ricetta.ingredienti
        .filter((ingrediente) => ingrediente.obbligatorio && !ingredientiPresenti.has(String(ingrediente.articolo_id)))
        .map((ingrediente) => ingrediente.articolo_nome);
      if (ingredientiMancanti.length) {
        impostaMessaggio(
          "trace-work-error",
          `La ricetta richiede questi ingredienti: ${ingredientiMancanti.join(", ")}.`,
        );
        return;
      }
      if (!outputRighe.some((riga) => String(riga.articolo_id) === String(ricetta.articolo_id))) {
        impostaMessaggio(
          "trace-work-error",
          `Aggiungi il prodotto previsto dalla ricetta: ${ricetta.articolo_nome}.`,
        );
        return;
      }
    }
    if (outputRighe.some((riga) => riga.tipo_data && !riga.data)) {
      impostaMessaggio("trace-work-error", "Inserisci la data del tipo selezionato per ogni prodotto.");
      return;
    }
    const output = outputRighe.map(({ tipo_data, data, origine, ...riga }) => ({
      ...riga,
      origine: origine || null,
      data_scadenza: tipo_data === "scadenza" ? data : null,
      data_tmc: tipo_data === "tmc" ? data : null,
    }));
    const scarti = leggiRighe("trace-work-scraps", ["descrizione", "quantita", "unita_misura"]);
    if (!input.length || !output.length) {
      impostaMessaggio("trace-work-error", "La lavorazione richiede almeno un lotto in ingresso e un prodotto in uscita.");
      return;
    }
    const oggi = dataLocaleISO();
    const lottiTmcSuperato = new Set(
      input
        .filter((riga) => {
          const lotto = lottiDisponibili.find((item) => String(item.id) === String(riga.lotto_id));
          return lotto?.data_tmc && String(lotto.data_tmc).slice(0, 10) < oggi;
        })
        .map((riga) => String(riga.lotto_id)),
    );
    if (lottiTmcSuperato.size && !window.confirm(
      "Uno o più lotti hanno il TMC superato. Confermi esplicitamente il loro utilizzo?",
    )) return;
    input = input.map((riga) => ({
      ...riga,
      conferma_tmc_scaduto: lottiTmcSuperato.has(String(riga.lotto_id)),
    }));
    const button = form.querySelector('[type="submit"]');
    button.disabled = true;
    try {
      const result = await api("/api/v1/tracciabilita/lavorazioni", {
        method: "POST",
        body: JSON.stringify({
          data: $("trace-work-date").value,
          descrizione: $("trace-work-description").value.trim(),
          operatore_id: Number($("trace-work-operator").value),
          ricetta_id: ricetta?.id ?? null,
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
      $("trace-work-recipe-help").hidden = true;
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
  $("trace-date-from").addEventListener("change", loadTracciabilita);
  $("trace-date-to").addEventListener("change", loadTracciabilita);
  $("btn-trace-refresh").addEventListener("click", loadTracciabilita);
  configuraFormLavorazione();
}
