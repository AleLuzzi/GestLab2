import { api } from "../api/client.js";
import { $ } from "../core/dom.js";

let fornitori = [];
let articoli = [];
let righeIngresso = [];
let categoriaSelezionata = null;
let articoliSelezionati = new Set();
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
  const quantitaPerUnita = righeIngresso.reduce((totale, riga) => {
    totale.set(riga.unitaMisura, (totale.get(riga.unitaMisura) || 0) + riga.quantita);
    return totale;
  }, new Map());
  const conteggio = righeIngresso.length;

  $("summary-data").textContent = data
    ? new Date(`${data}T00:00:00`).toLocaleDateString("it-IT")
    : "-";
  $("summary-fornitore").textContent = nomeFornitoreSelezionato();
  $("summary-ddt").textContent = $("ingress-ddt").value.trim() || "-";
  $("summary-conteggio").textContent = String(conteggio);
  $("summary-quantita").textContent = quantitaPerUnita.size
    ? [...quantitaPerUnita].map(([unita, quantita]) =>
      `${new Intl.NumberFormat("it-IT", { maximumFractionDigits: 3 }).format(quantita)} ${unita}`,
    ).join(" · ")
    : "0";
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
    name.textContent = riga.articolo;
    const category = document.createElement("span");
    category.textContent = riga.categoria;
    description.append(name, category);

    const weight = document.createElement("strong");
    weight.className = "ingresso-line-weight";
    weight.textContent = `${new Intl.NumberFormat("it-IT", {
      maximumFractionDigits: 3,
    }).format(riga.quantita)} ${riga.unitaMisura}`;

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "btn danger ingresso-remove-line";
    remove.textContent = "Rimuovi";
    remove.setAttribute("aria-label", `Rimuovi ${riga.articolo} dal riepilogo`);
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
    option.value = String(fornitore.soggetto_id);
    option.textContent = fornitore.azienda;
    select.appendChild(option);
  });
}

function articoliAttivi() {
  return articoli.filter((articolo) => articolo.attivo);
}

function categorieArticoli() {
  return [...new Set(articoliAttivi().map((articolo) =>
    articolo.categoria?.trim() || "Senza categoria"))];
}

function renderCategorie() {
  const container = $("ingress-categorie");
  container.replaceChildren();
  const categorie = categorieArticoli();

  if (categorie.length === 0) {
    $("ingress-articoli-feedback").textContent = "Non ci sono articoli attivi disponibili.";
    return;
  }

  categorie.forEach((categoria) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "categoria-button";
    button.textContent = categoria;
    button.setAttribute("aria-pressed", String(categoria === categoriaSelezionata));
    button.addEventListener("click", () => selezionaCategoria(categoria));
    container.appendChild(button);
  });
}

function renderArticoli() {
  const container = $("ingress-articoli");
  container.replaceChildren();
  if (!categoriaSelezionata) {
    $("ingress-articoli-feedback").textContent = "Seleziona una categoria per vedere gli articoli.";
    return;
  }

  const disponibili = articoliAttivi().filter((articolo) =>
    (articolo.categoria?.trim() || "Senza categoria") === categoriaSelezionata);
  if (disponibili.length === 0) {
    $("ingress-articoli-feedback").textContent = "Nessun articolo attivo in questa categoria.";
    return;
  }

  $("ingress-articoli-feedback").textContent = "Seleziona un articolo da aggiungere.";
  disponibili.forEach((articolo) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "articolo-button";
    button.textContent = `${articolo.nome} (${articolo.unita_misura})`;
    button.setAttribute("aria-pressed", String(articoliSelezionati.has(String(articolo.id))));
    button.addEventListener("click", () => {
      const id = String(articolo.id);
      if (articoliSelezionati.has(id)) articoliSelezionati.delete(id);
      else {
        articoliSelezionati.clear();
        articoliSelezionati.add(id);
      }
      renderArticoli();
    });
    container.appendChild(button);
  });
}

function selezionaCategoria(categoria) {
  categoriaSelezionata = categoria;
  articoliSelezionati.clear();
  $("ingress-articoli-feedback").textContent = "";
  renderCategorie();
  renderArticoli();
}

async function caricaDatiIngresso() {
  if (datiCaricati) return;
  if (caricamentoDati) return caricamentoDati;

  $("ingress-load-error").textContent = "";
  caricamentoDati = Promise.allSettled([
    api("/api/v1/fornitori"),
    api("/api/v1/articoli"),
  ]).then((results) => {
    const endpoints = ["fornitori", "articoli"];
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
    if (results[1].status === "fulfilled") articoli = results[1].value;

    if (results[1].status === "fulfilled") {
      renderCategorie();
      renderArticoli();
    }
    datiCaricati = results.every((result) => result.status === "fulfilled");
  }).finally(() => {
    caricamentoDati = null;
  });
  return caricamentoDati;
}

function aggiungiRighe() {
  const inputQuantita = $("ingress-quantita");
  const quantita = inputQuantita.valueAsNumber;
  if (!categoriaSelezionata) {
    $("ingress-articoli-feedback").textContent = "Seleziona prima una categoria.";
    return;
  }
  if (articoliSelezionati.size === 0) {
    $("ingress-articoli-feedback").textContent = "Seleziona almeno un articolo.";
    return;
  }
  if (!Number.isFinite(quantita) || !inputQuantita.checkValidity()) {
    $("ingress-articoli-feedback").textContent =
      "Inserisci una quantità valida, da 0,001 a 999.999.999,999, con massimo 3 decimali.";
    inputQuantita.focus();
    return;
  }

  const selezionati = articoliAttivi().filter((articolo) =>
    articoliSelezionati.has(String(articolo.id)));
  selezionati.forEach((articolo) => {
    righeIngresso.push({
      id: prossimoIdRiga++,
      articoloId: articolo.id,
      articolo: articolo.nome,
      categoria: articolo.categoria?.trim() || "Senza categoria",
      unitaMisura: articolo.unita_misura,
      quantita,
    });
  });
  articoliSelezionati.clear();
  $("ingress-quantita").value = "";
  $("ingress-error").textContent = "";
  $("ingress-error").classList.remove("success");
  renderArticoli();
  aggiornaRiepilogo();
  $("ingress-articoli-feedback").textContent =
    `${selezionati.length} ${selezionati.length === 1 ? "articolo aggiunto" : "articoli aggiunti"} al riepilogo.`;
}

function azzeraIngresso() {
  $("ingress-fornitore").value = "";
  $("ingress-data").value = dataLocaleISO();
  $("ingress-ddt").value = "";
  $("ingress-quantita").value = "";
  righeIngresso = [];
  categoriaSelezionata = null;
  articoliSelezionati.clear();
  prossimoIdRiga = 1;
  $("btn-salva-ingresso").disabled = false;
  $("ingress-success").textContent = "";
  $("ingress-success").classList.remove("success");
  $("ingress-error").textContent = "";
  $("ingress-articoli-feedback").textContent = "";
  mostraStep(1);
  renderCategorie();
  renderArticoli();
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
    const button = $("btn-salva-ingresso");
    button.disabled = true;
    $("ingress-error").classList.remove("success");
    $("ingress-error").textContent = "Salvataggio ingresso in corso…";
    try {
      const response = await api("/api/v1/tracciabilita/ingressi", {
        method: "POST",
        body: JSON.stringify({
          data: $("ingress-data").value,
          numero_ddt: $("ingress-ddt").value.trim(),
          fornitore_id: Number($("ingress-fornitore").value),
          righe: righeIngresso.map((riga) => ({
            articolo_id: Number(riga.articoloId),
            quantita: riga.quantita.toFixed(3),
          })),
        }),
      });
      const codiciLotto = response.lotti.map((lotto) => lotto.codice_lotto).join(", ");
      azzeraIngresso();
      $("ingress-success").classList.add("success");
      $("ingress-success").textContent =
        `Ingresso registrato. Lotti creati: ${codiciLotto}.`;
    } catch (error) {
      button.disabled = false;
      $("ingress-error").textContent = `Impossibile salvare l'ingresso: ${error.message}`;
    }
  });
  $("ingress-data").value = dataLocaleISO();
  $("ingress-fornitore").disabled = true;
  aggiornaRiepilogo();
  renderCategorie();
  renderArticoli();
}
