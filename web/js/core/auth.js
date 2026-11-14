import { api, clearTokens, setTokens } from "../api/client.js";
import { $ } from "./dom.js";

export async function doLogin(email, password) {
  const data = await api("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  if (!data?.access_token) throw new Error("Credenziali non valide");

  setTokens(data.access_token, data.refresh_token);
  return {
    email: data.email,
    role: data.ruolo,
    tenant_id: data.tenant_id,
  };
}

export function logout() {
  clearTokens();
}

function showLogin() {
  logout();
  delete document.body.dataset.role;
  $("view-login").style.display = "flex";
  $("view-app").style.display = "none";
  showAuthPanel(resetTokenFromUrl() ? "confirm" : "login");
}

function showApp(user, showLanding) {
  $("view-login").style.display = "none";
  $("view-app").style.display = "flex";
  document.body.dataset.role = user.role || "";
  $("user-email").textContent = user.email || "";
  $("user-role").textContent = user.role || "";
  const isAdmin = user.role === "admin";
  document.querySelectorAll(".admin-only").forEach((element) => {
    element.style.display = isAdmin ? "block" : "none";
  });
  showLanding();
}

function showAuthPanel(panel) {
  $("login-form").hidden = panel !== "login";
  $("reset-request-form").hidden = panel !== "request";
  $("reset-confirm-form").hidden = panel !== "confirm";
}

function resetTokenFromUrl() {
  return new URLSearchParams(window.location.search).get("reset") || "";
}

function clearResetTokenFromUrl() {
  const url = new URL(window.location.href);
  url.searchParams.delete("reset");
  window.history.replaceState({}, "", url.pathname + url.search + url.hash);
}

export function initAuth(showLanding) {
  $("login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    $("login-error").textContent = "";
    try {
      const user = await doLogin($("login-email").value, $("login-password").value);
      showApp(user, showLanding);
    } catch (error) {
      $("login-error").textContent = error.message;
    }
  });

  $("btn-password-dimenticata").addEventListener("click", () => {
    $("reset-email").value = $("login-email").value;
    $("reset-request-message").textContent = "";
    $("reset-request-message").classList.remove("success");
    showAuthPanel("request");
  });

  $("btn-torna-login").addEventListener("click", () => {
    clearResetTokenFromUrl();
    showAuthPanel("login");
  });

  $("btn-annulla-reset").addEventListener("click", () => {
    clearResetTokenFromUrl();
    showAuthPanel("login");
  });

  $("reset-request-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = $("reset-request-message");
    message.textContent = "";
    message.classList.remove("success");
    try {
      const data = await api("/auth/password-dimenticata", {
        method: "POST",
        body: JSON.stringify({ email: $("reset-email").value }),
      });
      message.textContent = data?.messaggio || "Richiesta registrata.";
      message.classList.add("success");
    } catch (error) {
      message.textContent = error.message;
    }
  });

  $("reset-confirm-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = $("reset-confirm-message");
    message.textContent = "";
    message.classList.remove("success");
    try {
      const data = await api("/auth/password-reimposta", {
        method: "POST",
        body: JSON.stringify({
          token: resetTokenFromUrl(),
          password: $("reset-password").value,
        }),
      });
      message.textContent = data?.messaggio || "Password aggiornata.";
      message.classList.add("success");
      $("reset-password").value = "";
      clearResetTokenFromUrl();
    } catch (error) {
      message.textContent = error.message;
    }
  });

  $("btn-logout").addEventListener("click", showLogin);
  showLogin();
}
