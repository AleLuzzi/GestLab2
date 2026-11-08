import { api } from "../api/client.js";
import { $ } from "../core/dom.js";

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
  } catch (error) {
    $("admin-error").textContent = error.message;
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
  } catch (error) {
    $("dev-result").textContent = "Errore: " + error.message;
  }
}

export async function loadDatiOsa() {
  $("osa-error").textContent = "";
  try {
    const dati = await api("/api/v1/tenant/osa");
    $("osa-ragione-sociale").value = dati.ragione_sociale;
    $("osa-indirizzo").value = dati.indirizzo;
    $("osa-laboratorio").value = dati.laboratorio;
    $("osa-partita-iva").value = dati.partita_iva;
  } catch (error) {
    $("osa-error").textContent = `Impossibile caricare i dati OSA: ${error.message}`;
  }
}

async function salvaDatiOsa() {
  $("osa-error").textContent = "";
  try {
    await api("/api/v1/tenant/osa", {
      method: "PUT",
      body: JSON.stringify({
        ragione_sociale: $("osa-ragione-sociale").value,
        indirizzo: $("osa-indirizzo").value,
        laboratorio: $("osa-laboratorio").value,
        partita_iva: $("osa-partita-iva").value,
      }),
    });
    $("osa-error").textContent = "Dati OSA salvati.";
    $("osa-error").classList.add("success");
  } catch (error) {
    $("osa-error").classList.remove("success");
    $("osa-error").textContent = `Impossibile salvare i dati OSA: ${error.message}`;
  }
}

export function initAdmin() {
  $("btn-crea-utente").addEventListener("click", creaUtente);
  $("btn-crea-dev").addEventListener("click", registraDispositivo);
  $("btn-salva-osa").addEventListener("click", salvaDatiOsa);
}
