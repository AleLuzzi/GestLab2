import { api } from "../api/client.js";
import { $ } from "../core/dom.js";

let fornitori = [];
let merceologie = [];
let tagli = [];
let righeIngresso = [];
let merceologiaSelezionata = null;
let tagliSelezionati = new Set();
let progressivo = "";
let datiCaricati = false;
let caricamentoDati = null;
let prossimoIdRiga = 1;

function dataLocaleISO() {
  const oggi = new Date();
  const mese = String(oggi.getMonth() + 1).padStart(2, "0");
  const giorno = String(oggi.getDate()).padStart(2, "0");
  return `${oggi.getFullYear()}-${mese}-${giorno}`;
}

function nomeFornitoreSelezionato() {
  const select = $("ingress-fornitore");
  return select.selectedIndex > 0 ? select.options[select.selectedIndex].textContent : "-";
}

function mostraStep(numero) {
  document.querySelectorAll(".ingresso-step").forEach((step) => {
    const attivo = Number(step.dataset.step) === numero;
    step.hidden = !attivo;
    step.classList.toggle("active", attivo);
  });
  document.querySelectorAll("[data-step-indicator]").forEach((indicator) => {
    const attivo = Number(indicator.dataset.stepIndicator) === numero;
    indicator.classList.toggle("active", attivo);
    if (attivo) indicator.setAttribute("aria-current", "step");
    else indicator.removeAttribute("aria-current");
  });
  $("ingress-error").textContent = "";
  $("ingress-error").classList.remove("success");
}

function aggiornaRiepilogo() {
  const data = $("ingress-data").value;
  const pesoTotale = righeIngresso.reduce((totale, riga) => totale + riga.peso, 0);
  const conteggio = righeIngresso.length;

  $("summary-data").textContent = data
    ? new Date(`${data}T00:00:00`).toLocaleDateString("it-IT")
    : "-";
  $("summary-progressivo").textContent = progressivo || "-";
  $("summary-fornitore").textContent = nomeFornitoreSelezionato();
  $("summary-ddt").textContent = $("ingress-ddt").value.trim() || "-";
  $("summary-conteggio").textContent = String(conteggio);
  $("summary-peso").textContent = `${new Intl.NumberFormat("it-IT", {
    maximumFractionDigits: 2,
  }).format(pesoTotale)} kg`;
  $("ingress-conteggio").textContent = `${conteggio} ${conteggio === 1 ? "articolo" : "articoli"}`;

  const container = $("ingress-riepilogo-righe");
  container.replaceChildren();
  if (conteggio === 0) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "Nessun articolo aggiunto. Torna agli articoli per iniziare.";
    container.appendChild(empty);
    return;
  }

  righeIngresso.forEach((riga) => {
    const item = document.createElement("div");
    item.className = "ingresso-line";

    const description = document.createElement("div");
    description.className = "ingresso-line-description";
    const name = document.createElement("strong");
    name.textContent = riga.taglio;
    const category = document.createElement("span");
    category.textContent = riga.merceologia;
    description.append(name, category);

    const weight = document.createElement("strong");
    weight.className = "ingresso-line-weight";
    weight.textContent = `${new Intl.NumberFormat("it-IT", {
      maximumFractionDigits: 2,
    }).format(riga.peso)} kg`;

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "btn danger ingresso-remove-line";
    remove.textContent = "Rimuovi";
    remove.setAttribute("aria-label", `Rimuovi ${riga.taglio} dal riepilogo`);
    remove.addEventListener("click", () => {
      righeIngresso = righeIngresso.filter((itemRow) => itemRow.id !== riga.id);
      $("ingress-error").textContent = "";
      $("ingress-error").classList.remove("success");
      aggiornaRiepilogo();
    });

    item.append(description, weight, remove);
    container.appendChild(item);
  });
}

function renderFornitori() {
  const select = $("ingress-fornitore");
  select.replaceChildren();
  select.disabled = fornitori.length === 0;
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = fornitori.length ? "Seleziona fornitore" : "Nessun fornitore abilitato";
  select.appendChild(placeholder);

  fornitori.forEach((fornitore) => {
    const option = document.createElement("option");
    option.value = String(fornitore.id);
    option.textContent = fornitore.azienda;
    select.appendChild(option);
  });
}

function renderMerceologie() {
  const container = $("ingress-merceologie");
  container.replaceChildren();
  const categorieConTagli = merceologie.filter((merceologia) =>
    tagli.some((taglio) => String(taglio.id_merceologia) === String(merceologia.id)));

  if (categorieConTagli.length === 0) {
    $("ingress-articoli-feedback").textContent = "Non ci sono merceologie con tagli disponibili.";
    return;
  }

  categorieConTagli.forEach((merceologia) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "merceologia-button";
    button.textContent = merceologia.merceologia;
    button.setAttribute("aria-pressed", String(
      String(merceologia.id) === String(merceologiaSelezionata?.id),
    ));
    button.addEventListener("click", () => selezionaMerceologia(merceologia));
    container.appendChild(button);
  });
}

function renderTagli() {
  const container = $("ingress-tagli");
  container.replaceChildren();
  if (!merceologiaSelezionata) {
    $("ingress-articoli-feedback").textContent = "Seleziona una merceologia per vedere i tagli disponibili.";
    return;
  }

  const disponibili = tagli.filter((taglio) =>
    String(taglio.id_merceologia) === String(merceologiaSelezionata.id));
  if (disponibili.length === 0) {
    $("ingress-articoli-feedback").textContent = "Nessun taglio disponibile per questa merceologia.";
    return;
  }

  $("ingress-articoli-feedback").textContent = "Seleziona un taglio da aggiungere.";
  disponibili.forEach((taglio) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "taglio-button";
    button.textContent = taglio.taglio;
    button.setAttribute("aria-pressed", String(tagliSelezionati.has(String(taglio.id))));
    button.addEventListener("click", () => {
      const id = String(taglio.id);
      if (tagliSelezionati.has(id)) tagliSelezionati.delete(id);
      else {
        tagliSelezionati.clear();
        tagliSelezionati.add(id);
      }
      renderTagli();
    });
    container.appendChild(button);
  });
}

function selezionaMerceologia(merceologia) {
  merceologiaSelezionata = merceologia;
  tagliSelezionati.clear();
  $("ingress-articoli-feedback").textContent = "";
  renderMerceologie();
  renderTagli();
}

async function caricaDatiIngresso() {
  if (datiCaricati) return;
  if (caricamentoDati) return caricamentoDati;

  $("ingress-load-error").textContent = "";
  $("ingress-progressivo").value = "Caricamento…";
  caricamentoDati = Promise.allSettled([
    api("/api/v1/fornitori"),
    api("/api/v1/merceologie"),
    api("/api/v1/tagli"),
    api("/api/v1/progressivi"),
  ]).then((results) => {
    const endpoints = ["fornitori", "merceologie", "tagli", "progressivo"];
    const errors = [];
    results.forEach((result, index) => {
      if (result.status === "rejected") {
        const detail = result.reason?.message || String(result.reason || "errore sconosciuto");
        errors.push(`Impossibile caricare ${endpoints[index]}: ${detail}`);
      }
    });
    if (errors.length) $("ingress-load-error").textContent = errors.join(" ");

    if (results[0].status === "fulfilled") {
      fornitori = results[0].value.filter((fornitore) => Number(fornitore.flag1_ing_merce) === 1);
      renderFornitori();
    } else {
      const select = $("ingress-fornitore");
      select.replaceChildren();
      const option = document.createElement("option");
      option.value = "";
      option.textContent = "Errore nel caricamento fornitori";
      select.appendChild(option);
      select.disabled = true;
    }
    if (results[1].status === "fulfilled") merceologie = results[1].value;
    if (results[2].status === "fulfilled") tagli = results[2].value;
    if (results[3].status === "fulfilled") {
      const valore = results[3].value[0]?.prog_acq;
      progressivo = valore == null ? "" : `${valore}A`;
      $("ingress-progressivo").value = progressivo || "Non configurato";
    }

    if (results[1].status === "fulfilled" && results[2].status === "fulfilled") {
      renderMerceologie();
      renderTagli();
    }
    datiCaricati = results.every((result) => result.status === "fulfilled");
  }).finally(() => {
    caricamentoDati = null;
  });
  return caricamentoDati;
}

function aggiungiRighe() {
  const peso = Number($("ingress-peso").value);
  if (!merceologiaSelezionata) {
    $("ingress-articoli-feedback").textContent = "Seleziona prima una merceologia.";
    return;
  }
  if (tagliSelezionati.size === 0) {
    $("ingress-articoli-feedback").textContent = "Seleziona almeno un taglio.";
    return;
  }
  if (!Number.isFinite(peso) || peso <= 0) {
    $("ingress-articoli-feedback").textContent = "Inserisci un peso maggiore di zero.";
    $("ingress-peso").focus();
    return;
  }

  const selezionati = tagli.filter((taglio) => tagliSelezionati.has(String(taglio.id)));
  selezionati.forEach((taglio) => {
    righeIngresso.push({
      id: prossimoIdRiga++,
      taglio: taglio.taglio,
      id_merc: merceologiaSelezionata.id,
      merceologia: merceologiaSelezionata.merceologia,
      peso,
    });
  });
  tagliSelezionati.clear();
  $("ingress-peso").value = "";
  $("ingress-error").textContent = "";
  $("ingress-error").classList.remove("success");
  renderTagli();
  aggiornaRiepilogo();
  $("ingress-articoli-feedback").textContent =
    `${selezionati.length} ${selezionati.length === 1 ? "articolo aggiunto" : "articoli aggiunti"} al riepilogo.`;
}

function azzeraIngresso() {
  $("ingress-fornitore").value = "";
  $("ingress-data").value = dataLocaleISO();
  $("ingress-ddt").value = "";
  $("ingress-peso").value = "";
  righeIngresso = [];
  merceologiaSelezionata = null;
  tagliSelezionati.clear();
  prossimoIdRiga = 1;
  $("btn-salva-ingresso").disabled = false;
  $("ingress-success").textContent = "";
  $("ingress-success").classList.remove("success");
  $("ingress-error").textContent = "";
  $("ingress-articoli-feedback").textContent = "";
  mostraStep(1);
  renderMerceologie();
  renderTagli();
  aggiornaRiepilogo();
}

export function openIngressoMerce() {
  document.querySelectorAll(".panel").forEach((panel) => panel.classList.remove("active"));
  $("view-ingresso-merce").classList.add("active");
  document.querySelectorAll(".nav-item").forEach((button) => button.classList.remove("active"));
  if (!$("ingress-data").value) $("ingress-data").value = dataLocaleISO();
  aggiornaRiepilogo();
  caricaDatiIngresso();
}

export function initIngressoMerce() {
  $("btn-reset-ingresso").addEventListener("click", azzeraIngresso);
  $("btn-ingresso-step-1").addEventListener("click", () => {
    if (!$("ingress-fornitore").value) {
      $("ingress-error").textContent = "Seleziona un fornitore prima di continuare.";
      $("ingress-fornitore").focus();
      return;
    }
    mostraStep(2);
  });
  $("btn-aggiungi-ingresso").addEventListener("click", aggiungiRighe);
  $("btn-ingresso-step-2").addEventListener("click", () => {
    if (righeIngresso.length === 0) {
      $("ingress-articoli-feedback").textContent = "Aggiungi almeno un articolo prima di continuare.";
      return;
    }
    aggiornaRiepilogo();
    mostraStep(3);
  });
  document.querySelectorAll("[data-step-back]").forEach((button) => {
    button.addEventListener("click", () => mostraStep(Number(button.dataset.stepBack)));
  });
  $("ingress-fornitore").addEventListener("change", aggiornaRiepilogo);
  $("ingress-ddt").addEventListener("input", aggiornaRiepilogo);

  $("btn-salva-ingresso").addEventListener("click", async () => {
    if (!$("ingress-fornitore").value || righeIngresso.length === 0) {
      $("ingress-error").classList.remove("success");
      $("ingress-error").textContent = "Completa l'intestazione e aggiungi almeno un articolo.";
      return;
    }
    if (!progressivo) {
      $("ingress-error").classList.remove("success");
      $("ingress-error").textContent = "Progressivo di ingresso non disponibile.";
      return;
    }

    const button = $("btn-salva-ingresso");
    button.disabled = true;
    $("ingress-error").classList.remove("success");
    $("ingress-error").textContent = "Salvataggio ingresso in corso…";
    try {
      const response = await api("/api/v1/ingresso-merce", {
        method: "POST",
        body: JSON.stringify({
          prog_acq: progressivo,
          data: $("ingress-data").value,
          num_ddt: $("ingress-ddt").value.trim(),
          fornitore: nomeFornitoreSelezionato(),
          righe: righeIngresso.map((riga) => ({
            taglio: riga.taglio,
            peso: String(riga.peso),
            id_merc: riga.id_merc,
          })),
        }),
      });
      const progressivoNumerico = Number.parseInt(progressivo, 10);
      progressivo = `${progressivoNumerico + 1}A`;
      $("ingress-progressivo").value = progressivo;
      azzeraIngresso();
      $("ingress-success").classList.add("success");
      $("ingress-success").textContent =
        `Ingresso salvato nel database (${response.inseriti} righe).`;
    } catch (error) {
      button.disabled = false;
      $("ingress-error").textContent = `Impossibile salvare l'ingresso: ${error.message}`;
    }
  });
  $("ingress-data").value = dataLocaleISO();
  $("ingress-fornitore").disabled = true;
  aggiornaRiepilogo();
  renderMerceologie();
  renderTagli();
}
