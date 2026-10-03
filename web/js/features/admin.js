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

export function initAdmin() {
  $("btn-crea-utente").addEventListener("click", creaUtente);
  $("btn-crea-dev").addEventListener("click", registraDispositivo);
}
