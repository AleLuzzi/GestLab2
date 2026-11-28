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

function etichettaArticolo(articolo, mostraCategoria = false) {
  const codice = articolo.codice ? ` · ${articolo.codice}` : "";
  const categoria = mostraCategoria && articolo.categoria?.trim()
    ? ` · ${articolo.categoria.trim()}`
    : "";
  return `${articolo.nome}${codice} (${articolo.unita_misura})${categoria}`;
}

function riempiSelectArticoli(select) {
  const selected = select.value;
  select.replaceChildren(creaOpzione("", "Seleziona articolo"));
  articoliAttivi().forEach((articolo) => {
    select.appendChild(creaOpzione(articolo.id, etichettaArticolo(articolo)));
  });
  select.value = selected;
}

function normalizzaCategoria(value) {
  return String(value ?? "").trim().toLocaleLowerCase("it");
}

function categoriaDelLotto(lotto) {
  const diretta = String(lotto?.categoria ?? "").trim();
  if (diretta) return diretta;
  const articolo = articoli.find((item) => String(item.id) === String(lotto?.articolo_id));
  return String(articolo?.categoria ?? "").trim();
}

function etichetteCategorieInput() {
  const etichette = new Map();
  document.querySelectorAll('#trace-work-inputs select[data-field="lotto_id"]').forEach((select) => {
    if (!select.value) return;
    const lotto = lottiDisponibili.find((item) => String(item.id) === select.value);
    const categoria = categoriaDelLotto(lotto);
    if (!categoria) return;
    const chiave = normalizzaCategoria(categoria);
    if (!etichette.has(chiave)) etichette.set(chiave, categoria);
  });
  return etichette;
}

function idArticoloRicettaSelezionata() {
  const ricetta = ricette.find((item) => String(item.id) === $("trace-work-recipe").value);
  return ricetta ? String(ricetta.articolo_id) : "";
}

function articoliPropostiInOutput() {
  const categorie = etichetteCategorieInput();
  const ricettaId = idArticoloRicettaSelezionata();
  const attivi = articoliAttivi();
  if (!categorie.size) return attivi;
  return attivi.filter((articolo) => (
    categorie.has(normalizzaCategoria(articolo.categoria))
    || (ricettaId && String(articolo.id) === ricettaId)
  ));
}

function fraseCategorie(nomi) {
  if (nomi.length <= 1) return `della categoria ${nomi[0] || ""}`.trim();
  if (nomi.length === 2) return `delle categorie ${nomi[0]} e ${nomi[1]}`;
  return `delle categorie ${nomi.slice(0, -1).join(", ")} e ${nomi.at(-1)}`;
}

function aggiornaAiutoOutput() {
  const help = $("trace-work-output-help");
  if (!help) return;
  const nomi = [...etichetteCategorieInput().values()];
  if (!nomi.length) {
    help.textContent = "Seleziona un lotto in input: in output compariranno gli articoli della stessa categoria.";
    return;
  }
  const proposti = articoliPropostiInOutput();
  help.textContent = proposti.length
    ? `In output sono proposti gli articoli ${fraseCategorie(nomi)}.`
    : `Nessun articolo attivo ${fraseCategorie(nomi)}.`;
}

function riempiSelectArticoliOutput(select) {
  const selected = select.value;
  const categorie = etichetteCategorieInput();
  const proposti = articoliPropostiInOutput();
  const mostraCategoria = categorie.size > 1;
  select.replaceChildren(creaOpzione(
    "",
    categorie.size ? "Seleziona articolo della stessa categoria" : "Seleziona articolo",
  ));
  proposti.forEach((articolo) => {
    select.appendChild(creaOpzione(articolo.id, etichettaArticolo(articolo, mostraCategoria)));
  });
  select.value = proposti.some((articolo) => String(articolo.id) === selected) ? selected : "";
}

function aggiornaOutputPerCategoriaInput() {
  document.querySelectorAll('#trace-work-outputs select[data-field="articolo_id"]')
    .forEach(riempiSelectArticoliOutput);
  aggiornaAiutoOutput();
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
  document.querySelectorAll('.trace-line select[data-field="lotto_id"]').forEach(riempiSelectLotti);
  aggiornaOutputPerCategoriaInput();
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

function renderRicette() {
  const tbody = $("trace-recipes-tbody");
  const canManage = ["admin", "operatore"].includes(document.body.dataset.role);
  $("btn-trace-recipe-new").hidden = !canManage;
  tbody.replaceChildren();
  if (!ricette.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 7;
    cell.className = "empty";
    cell.textContent = "Nessuna ricetta configurata.";
    row.appendChild(cell);
    tbody.appendChild(row);
    riempiSelectRicette();
    return;
  }

  ricette.forEach((ricetta) => {
    const row = document.createElement("tr");
    const ingredienti = ricetta.ingredienti.map((ingrediente) => {
      const valore = ingrediente.tipo_quantita === "percentuale"
        ? `${ingrediente.valore}%`
        : `${ingrediente.valore} ${ingrediente.unita_misura}/kg`;
      return `${ingrediente.articolo_nome}: ${valore}${ingrediente.obbligatorio ? "" : " (facoltativo)"}`;
    }).join(", ");
    const values = [
      ricetta.nome,
      `${ricetta.articolo_nome} (${ricetta.unita_misura})`,
      `${ricetta.resa_attesa} / ${ricetta.scarto_atteso} ${ricetta.unita_misura}`,
      ingredienti || "Nessun ingrediente",
      ricetta.allergeni.join(", ") || "Nessuno indicato",
      ricetta.attiva ? "Attiva" : "Disattivata",
    ];
    values.forEach((value) => {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.appendChild(cell);
    });

    const actions = document.createElement("td");
    if (canManage) {
      const edit = document.createElement("button");
      edit.type = "button";
      edit.className = "btn ghost trace-recipe-edit";
      edit.dataset.recipeId = String(ricetta.id);
      edit.textContent = "Modifica";
      actions.appendChild(edit);
    } else {
      actions.textContent = "Sola lettura";
    }
    row.appendChild(actions);
    tbody.appendChild(row);
  });
  riempiSelectRicette();
}

function aggiungiIngredienteRicetta(ingrediente = null) {
  const row = document.createElement("div");
  row.className = "trace-recipe-ingredient-row";

  const articleLabel = document.createElement("label");
  articleLabel.textContent = "Articolo ingrediente";
  const articleSelect = document.createElement("select");
  articleSelect.dataset.field = "articolo_id";
  articleSelect.required = true;
  articleSelect.appendChild(creaOpzione("", "Seleziona ingrediente"));
  articoliAttivi()
    .filter((articolo) => articolo.utilizzabile_come_input)
    .forEach((articolo) => articleSelect.appendChild(creaOpzione(
      articolo.id,
      `${articolo.nome}${articolo.codice ? ` · ${articolo.codice}` : ""} (${articolo.unita_misura})`,
    )));
  articleSelect.value = String(ingrediente?.articolo_id ?? "");
  articleLabel.appendChild(articleSelect);
  row.appendChild(articleLabel);

  const typeLabel = document.createElement("label");
  typeLabel.textContent = "Tipo quantità";
  const typeSelect = document.createElement("select");
  typeSelect.dataset.field = "tipo_quantita";
  typeSelect.appendChild(creaOpzione("quantita", "Quantità per kg prodotto"));
  typeSelect.appendChild(creaOpzione("percentuale", "Percentuale"));
  typeSelect.value = ingrediente?.tipo_quantita ?? "quantita";
  typeLabel.appendChild(typeSelect);
  row.appendChild(typeLabel);

  const valueLabel = document.createElement("label");
  valueLabel.textContent = "Valore";
  const valueInput = document.createElement("input");
  valueInput.dataset.field = "valore";
  valueInput.type = "number";
  valueInput.min = "0.001";
  valueInput.step = "0.001";
  valueInput.inputMode = "decimal";
  valueInput.required = true;
  valueInput.value = String(ingrediente?.valore ?? "");
  typeSelect.addEventListener("change", () => {
    if (typeSelect.value === "percentuale") {
      valueInput.max = "100";
    } else {
      valueInput.removeAttribute("max");
    }
  });
  typeSelect.dispatchEvent(new Event("change"));
  valueLabel.appendChild(valueInput);
  row.appendChild(valueLabel);

  const requiredLabel = document.createElement("label");
  requiredLabel.className = "trace-recipe-ingredient-required";
  const requiredInput = document.createElement("input");
  requiredInput.dataset.field = "obbligatorio";
  requiredInput.type = "checkbox";
  requiredInput.checked = ingrediente?.obbligatorio ?? true;
  requiredLabel.append(requiredInput, document.createTextNode("Obbligatorio"));
  row.appendChild(requiredLabel);

  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "btn danger";
  remove.textContent = "Rimuovi";
  remove.setAttribute("aria-label", "Rimuovi ingrediente");
  remove.addEventListener("click", () => row.remove());
  row.appendChild(remove);
  $("trace-recipe-ingredients").appendChild(row);
}

function resetFormRicetta() {
  $("trace-recipe-form").reset();
  $("trace-recipe-id").value = "";
  $("trace-recipe-scrap").value = "0";
  $("trace-recipe-active").checked = true;
  $("trace-recipe-form-title").textContent = "Nuova ricetta";
  $("btn-trace-recipe-save").textContent = "Salva ricetta";
  $("trace-recipe-ingredients").replaceChildren();
  impostaMessaggio("trace-recipe-form-error");
}

function apriFormRicetta(ricetta = null) {
  resetFormRicetta();
  if (ricetta) {
    $("trace-recipe-id").value = String(ricetta.id);
    $("trace-recipe-name").value = ricetta.nome;
    $("trace-recipe-product").value = String(ricetta.articolo_id);
    $("trace-recipe-yield").value = String(ricetta.resa_attesa);
    $("trace-recipe-scrap").value = String(ricetta.scarto_atteso);
    $("trace-recipe-life").value = ricetta.giorni_vita ?? "";
    $("trace-recipe-storage").value = ricetta.istruzioni_conservazione ?? "";
    $("trace-recipe-cooking").value = ricetta.istruzioni_cottura ?? "";
    $("trace-recipe-active").checked = ricetta.attiva;
    $("trace-recipe-form-title").textContent = `Modifica ricetta: ${ricetta.nome}`;
    $("btn-trace-recipe-save").textContent = "Salva modifiche";
    document.querySelectorAll('input[name="trace-recipe-allergen"]').forEach((input) => {
      input.checked = ricetta.allergeni.includes(input.value);
    });
    ricetta.ingredienti.forEach(aggiungiIngredienteRicetta);
  }
  $("trace-recipe-form").hidden = false;
  $("trace-recipe-form").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function aggiornaRicette() {
  ricette = await api("/api/v1/ricette");
  renderRicette();
}

function configuraFormRicette() {
  riempiSelectArticoli($("trace-recipe-product"));
  $("trace-recipes-tbody").addEventListener("click", (event) => {
    const button = event.target.closest(".trace-recipe-edit");
    if (!button) return;
    const ricetta = ricette.find((item) => String(item.id) === button.dataset.recipeId);
    if (ricetta) apriFormRicetta(ricetta);
  });
  $("btn-trace-recipe-new").addEventListener("click", () => apriFormRicetta());
  $("btn-trace-recipe-add-ingredient").addEventListener("click", () => aggiungiIngredienteRicetta());
  $("btn-trace-recipe-cancel").addEventListener("click", () => {
    $("trace-recipe-form").hidden = true;
    resetFormRicetta();
  });
  $("trace-recipe-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    impostaMessaggio("trace-recipe-form-error");
    const ingredienti = [...$("trace-recipe-ingredients").querySelectorAll(".trace-recipe-ingredient-row")];
    const articoloIds = ingredienti.map((row) => row.querySelector('[data-field="articolo_id"]').value);
    if (articoloIds.includes("")) {
      impostaMessaggio("trace-recipe-form-error", "Seleziona un articolo per ogni ingrediente.");
      return;
    }
    if (new Set(articoloIds).size !== articoloIds.length) {
      impostaMessaggio("trace-recipe-form-error", "Ogni articolo può comparire una sola volta nella ricetta.");
      return;
    }
    const payload = {
      nome: $("trace-recipe-name").value.trim(),
      articolo_id: Number($("trace-recipe-product").value),
      resa_attesa: $("trace-recipe-yield").value,
      scarto_atteso: $("trace-recipe-scrap").value,
      ingredienti: ingredienti.map((row) => ({
        articolo_id: Number(row.querySelector('[data-field="articolo_id"]').value),
        tipo_quantita: row.querySelector('[data-field="tipo_quantita"]').value,
        valore: row.querySelector('[data-field="valore"]').value,
        obbligatorio: row.querySelector('[data-field="obbligatorio"]').checked,
      })),
      allergeni: [...document.querySelectorAll('input[name="trace-recipe-allergen"]:checked')]
        .map((input) => input.value),
      giorni_vita: $("trace-recipe-life").value ? Number($("trace-recipe-life").value) : null,
      istruzioni_conservazione: $("trace-recipe-storage").value.trim() || null,
      istruzioni_cottura: $("trace-recipe-cooking").value.trim() || null,
    };
    const recipeId = $("trace-recipe-id").value;
    if (recipeId) payload.attiva = $("trace-recipe-active").checked;

    const saveButton = $("btn-trace-recipe-save");
    impostaMessaggio("trace-recipes-error");
    saveButton.disabled = true;
    try {
      await api(
        recipeId ? `/api/v1/ricette/${encodeURIComponent(recipeId)}` : "/api/v1/ricette",
        {
          method: recipeId ? "PUT" : "POST",
          body: JSON.stringify(payload),
        },
      );
      $("trace-recipe-form").hidden = true;
      resetFormRicetta();
      try {
        await aggiornaRicette();
        impostaMessaggio("trace-recipes-error", "Ricetta salvata.", true);
      } catch (error) {
        impostaMessaggio(
          "trace-recipes-error",
          `Ricetta salvata, ma impossibile aggiornare l'elenco: ${error.message}`,
        );
      }
    } catch (error) {
      impostaMessaggio("trace-recipe-form-error", `Impossibile salvare la ricetta: ${error.message}`);
    } finally {
      saveButton.disabled = false;
    }
  });
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
  aggiornaOutputPerCategoriaInput();
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
    (select) => riempiSelectArticoliOutput(select),
    "Rimuovi prodotto output",
  );
  outputRow.querySelector('[data-field="articolo_id"]').value = String(ricetta.articolo_id);
  aggiornaAiutoOutput();

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

function valoreCampoRiga(row, field) {
  return row.querySelector(`[data-field="${field}"]`)?.value.trim() ?? "";
}

function righeCompilate(containerId, campi) {
  return [...$(containerId).querySelectorAll(".trace-line")]
    .map((row) => {
      const valori = {};
      campi.forEach((campo) => {
        valori[campo] = valoreCampoRiga(row, campo);
      });
      return valori;
    })
    .filter((riga) => campi.some((campo) => riga[campo]));
}

function testoScelta(numero, singolare, plurale) {
  return `${numero} ${numero === 1 ? singolare : plurale}`;
}

function arrotondaMilli(value) {
  return Math.round(Number(value) * 1000) / 1000;
}

function datiBilancioLavorazione() {
  const input = leggiRighe("trace-work-inputs", ["lotto_id", "quantita"]).map((riga) => {
    const lotto = lottiDisponibili.find((item) => String(item.id) === String(riga.lotto_id));
    return { quantita: riga.quantita, unita: lotto?.unita_misura || "" };
  });
  const output = leggiRighe(
    "trace-work-outputs",
    ["articolo_id", "quantita", "tipo_data", "data", "origine"],
  ).map((riga) => {
    const articolo = articoli.find((item) => String(item.id) === String(riga.articolo_id));
    return { quantita: riga.quantita, unita: articolo?.unita_misura || "" };
  });
  const scarti = leggiRighe("trace-work-scraps", ["descrizione", "quantita", "unita_misura"]).map((riga) => ({
    quantita: riga.quantita,
    unita: riga.unita_misura,
  }));
  return { input, output, scarti };
}

function messaggioBilancioMassa(input, output, scarti) {
  const voci = [
    ...input.map((riga) => ({ ...riga, segno: 1 })),
    ...output.map((riga) => ({ ...riga, segno: -1 })),
    ...scarti.map((riga) => ({ ...riga, segno: -1 })),
  ].filter((voce) => {
    const quantita = Number(voce.quantita);
    return Number.isFinite(quantita) && quantita > 0;
  });
  if (!voci.length) return "";
  if (voci.some((voce) => !String(voce.unita ?? "").trim())) {
    return "Unità di misura mancante: non è possibile verificare che input, output e scarti quadrino.";
  }
  const totali = new Map();
  voci.forEach((voce) => {
    const unita = String(voce.unita).trim();
    const chiave = unita.toLocaleLowerCase("it");
    const corrente = totali.get(chiave) || { unita, quantita: 0 };
    corrente.quantita += Number(voce.quantita) * voce.segno;
    totali.set(chiave, corrente);
  });
  const parti = [];
  [...totali.keys()].sort().forEach((chiave) => {
    const { unita, quantita } = totali.get(chiave);
    const delta = arrotondaMilli(quantita);
    if (delta === 0) return;
    if (delta > 0) {
      parti.push(
        `mancano ${formattaQuantita(delta, unita)} tra prodotti in output e scarti rispetto alla quantità consumata`,
      );
    } else {
      parti.push(
        `prodotti e scarti superano la quantità consumata di ${formattaQuantita(-delta, unita)}`,
      );
    }
  });
  if (!parti.length) return "";
  const testo = parti.join("; ");
  return `${testo.charAt(0).toLocaleUpperCase("it")}${testo.slice(1)}. Registra lo scarto oppure correggi le quantità.`;
}

function passoTreVisibile() {
  const panel = document.querySelector('[data-trace-work-panel="3"]');
  return Boolean(panel && !panel.hidden);
}

function aggiornaAvvisoBilancio() {
  const { input, output, scarti } = datiBilancioLavorazione();
  const messaggio = messaggioBilancioMassa(input, output, scarti);
  const elemento = $("trace-work-error");
  if (!passoTreVisibile()) {
    if (!messaggio && elemento.dataset.bilancio === "1") {
      impostaMessaggio("trace-work-error");
      delete elemento.dataset.bilancio;
    }
    return messaggio;
  }
  if (messaggio) {
    impostaMessaggio("trace-work-error", messaggio);
    elemento.dataset.bilancio = "1";
    return messaggio;
  }
  if (elemento.dataset.bilancio === "1") {
    impostaMessaggio("trace-work-error");
    delete elemento.dataset.bilancio;
  }
  return "";
}

function testoQuantitaTotale(righe) {
  const totale = new Map();
  righe.forEach((riga) => {
    if (riga.quantitaNumero === null) return;
    totale.set(riga.unita, (totale.get(riga.unita) || 0) + riga.quantitaNumero);
  });
  return totale.size
    ? [...totale].map(([unita, quantita]) => formattaQuantita(quantita, unita)).join(" · ")
    : "0";
}

function creaRigaSintesi(nome, dettagli, quantita) {
  const item = document.createElement("div");
  item.className = "ingresso-line trace-summary-line";

  const description = document.createElement("div");
  description.className = "ingresso-line-description";
  const name = document.createElement("strong");
  name.textContent = nome;
  description.appendChild(name);
  const testoDettagli = dettagli.filter(Boolean).join(" · ");
  if (testoDettagli) {
    const details = document.createElement("span");
    details.textContent = testoDettagli;
    description.appendChild(details);
  }

  const weight = document.createElement("strong");
  weight.className = "ingresso-line-weight";
  weight.textContent = quantita;
  item.append(description, weight);
  return item;
}

function riempiSintesi(container, righe, messaggioVuoto) {
  container.replaceChildren();
  if (righe.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = messaggioVuoto;
    container.appendChild(empty);
    return;
  }
  righe.forEach((riga) => container.appendChild(creaRigaSintesi(riga.nome, riga.dettagli, riga.quantita)));
}

function testoOpzioneSelezionata(select) {
  return select.selectedIndex > 0 ? select.options[select.selectedIndex].textContent : "";
}

function aggiornaRiepilogoLavorazione() {
  const data = $("trace-work-date").value;
  $("trace-summary-date").textContent = data
    ? new Date(`${data}T00:00:00`).toLocaleDateString("it-IT")
    : "—";
  $("trace-summary-operator").textContent = testoOpzioneSelezionata($("trace-work-operator")) || "—";
  $("trace-summary-description").textContent = $("trace-work-description").value.trim() || "—";
  $("trace-summary-recipe").textContent = testoOpzioneSelezionata($("trace-work-recipe")) || "Lavorazione manuale";

  const input = righeCompilate("trace-work-inputs", ["lotto_id", "quantita"]).map((riga) => {
    const lotto = lottiDisponibili.find((item) => String(item.id) === riga.lotto_id);
    const quantita = riga.quantita === "" ? null : Number(riga.quantita);
    const quantitaValida = Number.isFinite(quantita);
    const dataTipo = lotto?.data_scadenza ? "Scadenza" : lotto?.data_tmc ? "TMC" : "";
    const dataValore = lotto?.data_scadenza || lotto?.data_tmc;
    return {
      nome: lotto?.articolo || "Lotto non selezionato",
      dettagli: [
        lotto?.codice_lotto,
        lotto?.categoria,
        dataTipo && dataValore && `${dataTipo}: ${formattaData(dataValore)}`,
      ],
      quantita: quantitaValida ? formattaQuantita(quantita, lotto?.unita_misura || "") : "—",
      quantitaNumero: quantitaValida ? quantita : null,
      unita: lotto?.unita_misura || "",
    };
  });
  const output = righeCompilate(
    "trace-work-outputs",
    ["articolo_id", "quantita", "tipo_data", "data", "origine"],
  ).map((riga) => {
    const articolo = articoli.find((item) => String(item.id) === riga.articolo_id);
    const quantita = riga.quantita === "" ? null : Number(riga.quantita);
    const quantitaValida = Number.isFinite(quantita);
    const tipoData = riga.tipo_data === "scadenza" ? "Scadenza" : riga.tipo_data === "tmc" ? "TMC" : "";
    return {
      nome: articolo?.nome || "Articolo non selezionato",
      dettagli: [
        articolo?.categoria?.trim(),
        tipoData && (riga.data ? `${tipoData}: ${formattaData(riga.data)}` : tipoData),
        riga.origine && `Origine: ${riga.origine}`,
      ],
      quantita: quantitaValida ? formattaQuantita(quantita, articolo?.unita_misura || "") : "—",
      quantitaNumero: quantitaValida ? quantita : null,
      unita: articolo?.unita_misura || "",
    };
  });

  $("trace-summary-input-count").textContent = String(input.length);
  $("trace-summary-output-count").textContent = String(output.length);
  $("trace-summary-input-qty").textContent = testoQuantitaTotale(input);
  $("trace-summary-output-qty").textContent = testoQuantitaTotale(output);
  $("trace-summary-input-badge").textContent = testoScelta(input.length, "lotto", "lotti");
  $("trace-summary-output-badge").textContent = testoScelta(output.length, "prodotto", "prodotti");
  riempiSintesi(
    $("trace-work-summary-inputs"),
    input,
    "Nessun lotto in input. Torna all'input per selezionarlo.",
  );
  riempiSintesi(
    $("trace-work-summary-outputs"),
    output,
    "Nessun prodotto in output. Torna all'output per aggiungerlo.",
  );
  aggiornaAvvisoBilancio();
}

function mostraPassoLavorazione(numero) {
  const sezione = document.querySelector('[data-trace-section="lavorazione"]');
  const passo = Number(numero);
  sezione.querySelectorAll("[data-trace-work-panel]").forEach((panel) => {
    const attivo = Number(panel.dataset.traceWorkPanel) === passo;
    panel.hidden = !attivo;
    panel.classList.toggle("active", attivo);
  });
  sezione.querySelectorAll("[data-trace-work-indicator]").forEach((indicator) => {
    const attivo = Number(indicator.dataset.traceWorkIndicator) === passo;
    indicator.classList.toggle("active", attivo);
    if (attivo) indicator.setAttribute("aria-current", "step");
    else indicator.removeAttribute("aria-current");
  });
  if (passo === 3) aggiornaRiepilogoLavorazione();
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
  mostraPassoLavorazione(1);
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
    (select) => riempiSelectArticoliOutput(select),
    "Rimuovi prodotto output",
  );
  aggiornaAiutoOutput();
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
    if (!dettaglio.vendite.length) {
      appendTesto(forward, "p", "trace-muted", "Nessuna lavorazione successiva registrata.");
    }
  }
  appendTesto(forward, "h5", "", "Vendite collegate");
  const salesList = document.createElement("ul");
  if (dettaglio.vendite.length) {
    dettaglio.vendite.forEach((vendita) => {
      const tipoDocumento = vendita.tipo_documento === "DDT" ? "DDT" : "Ricevuta";
      appendTesto(
        salesList,
        "li",
        "",
        `${tipoDocumento} n. ${vendita.numero} · ${formattaData(vendita.data)} · ${vendita.cliente || "Banco"} — ${formattaQuantita(vendita.quantita, vendita.unita_misura)}`,
      );
    });
  } else {
    appendTesto(salesList, "li", "trace-muted", "Nessuna vendita registrata.");
  }
  forward.appendChild(salesList);
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
  impostaMessaggio("trace-recipes-error");
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
    impostaMessaggio(
      "trace-recipes-error",
      `Impossibile caricare le ricette: ${risultati[4].reason?.message || risultati[4].reason}`,
    );
  }
  riempiSelectArticoli($("trace-recipe-product"));
  renderRicette();
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
  if (["lavorazione", "ricette"].includes(nome) && !lottiCaricati) loadTracciabilita();
}

function configuraFormLavorazione() {
  $("trace-work-date").value = dataLocaleISO();
  aggiungiRigaInput();
  aggiungiRigaOutput();
  document.querySelector('[data-trace-section="lavorazione"]').addEventListener("click", (event) => {
    const button = event.target.closest("[data-trace-work-step]");
    if (!button) return;
    mostraPassoLavorazione(button.dataset.traceWorkStep);
  });
  $("btn-trace-add-input").addEventListener("click", aggiungiRigaInput);
  $("btn-trace-add-output").addEventListener("click", aggiungiRigaOutput);
  $("btn-trace-add-scrap").addEventListener("click", aggiungiRigaScarto);
  ["btn-trace-add-input", "btn-trace-add-output"].forEach((id) => {
    $(id).addEventListener("click", () => {
      $("trace-work-confirm-weights").checked = false;
    });
  });
  $("btn-trace-apply-recipe").addEventListener("click", applicaRicettaSelezionata);
  ["trace-work-date", "trace-work-operator", "trace-work-description"].forEach((id) => {
    $(id).addEventListener("input", aggiornaRiepilogoLavorazione);
    $(id).addEventListener("change", aggiornaRiepilogoLavorazione);
  });
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
        if (containerId === "trace-work-inputs") aggiornaOutputPerCategoriaInput();
      }
    });
    $(containerId).addEventListener("input", () => {
      $("trace-work-confirm-weights").checked = false;
      aggiornaAvvisoBilancio();
    });
    $(containerId).addEventListener("change", (event) => {
      $("trace-work-confirm-weights").checked = false;
      if (containerId === "trace-work-inputs" && event.target.matches('[data-field="lotto_id"]')) {
        aggiornaOutputPerCategoriaInput();
      }
    });
  });
  ["input", "change", "click"].forEach((tipo) => {
    $("trace-work-scraps").addEventListener(tipo, aggiornaAvvisoBilancio);
  });
  $("trace-work-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    impostaMessaggio("trace-work-error");
    if (!$("trace-work-confirm-weights").checked) {
      mostraPassoLavorazione(3);
      impostaMessaggio("trace-work-error", "Conferma i pesi rilevati prima di registrare la lavorazione.");
      return;
    }
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
    const { input: consumi, output: prodotti, scarti: rifili } = datiBilancioLavorazione();
    const bilancio = messaggioBilancioMassa(consumi, prodotti, rifili);
    if (bilancio) {
      mostraPassoLavorazione(3);
      impostaMessaggio("trace-work-error", bilancio);
      $("trace-work-error").dataset.bilancio = "1";
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
      mostraPassoLavorazione(1);
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
  configuraFormRicette();
}
