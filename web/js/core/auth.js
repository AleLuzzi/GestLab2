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
  $("view-login").style.display = "flex";
  $("view-app").style.display = "none";
}

function showApp(user, showLanding) {
  $("view-login").style.display = "none";
  $("view-app").style.display = "flex";
  $("user-email").textContent = user.email || "";
  $("user-role").textContent = user.role || "";
  const isAdmin = user.role === "admin";
  document.querySelectorAll(".admin-only").forEach((element) => {
    element.style.display = isAdmin ? "block" : "none";
  });
  showLanding();
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
  $("btn-logout").addEventListener("click", showLogin);
  showLogin();
}
