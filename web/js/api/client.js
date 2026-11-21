const API = "";

const MESSAGGI_STATO = {
  400: "Richiesta non valida.",
  401: "Accesso non autorizzato.",
  403: "Operazione non consentita.",
  404: "Elemento non trovato.",
  409: "Operazione in conflitto con i dati già registrati.",
  422: "Dati non validi.",
  429: "Troppi tentativi. Riprova tra qualche minuto.",
  500: "Errore interno. Riprova o contatta l'assistenza.",
  503: "Servizio momentaneamente non disponibile.",
};

const MESSAGGI_STATO_TESTO = {
  "bad request": MESSAGGI_STATO[400],
  unauthorized: MESSAGGI_STATO[401],
  forbidden: MESSAGGI_STATO[403],
  "not found": MESSAGGI_STATO[404],
  conflict: MESSAGGI_STATO[409],
  "unprocessable entity": MESSAGGI_STATO[422],
  "unprocessable content": MESSAGGI_STATO[422],
  "too many requests": MESSAGGI_STATO[429],
  "internal server error": MESSAGGI_STATO[500],
  "service unavailable": MESSAGGI_STATO[503],
};

export function messaggioOperatore(detail, status) {
  if (typeof detail === "string") {
    const testo = detail.trim();
    const tradotto = MESSAGGI_STATO_TESTO[testo.toLowerCase()];
    if (tradotto) return tradotto;
    if (testo && !testo.startsWith("{") && !testo.startsWith("[")) return testo;
  }
  if (Array.isArray(detail)) {
    const frasi = detail.map((voce) => {
      if (typeof voce === "string") return voce.trim();
      if (voce && typeof voce.msg === "string") return voce.msg.trim();
      return "";
    }).filter((frase) => frase && !frase.startsWith("{") && !frase.startsWith("["));
    if (frasi.length) return frasi.join(" ");
  }
  return MESSAGGI_STATO[status] || "Operazione non riuscita.";
}

let accessToken = null;
let refreshToken = null;

export function setTokens(access, refresh) {
  accessToken = access;
  refreshToken = refresh;
}

export function clearTokens() {
  accessToken = null;
  refreshToken = null;
}

export async function endSession() {
  const token = refreshToken;
  clearTokens();
  if (!token) return;
  try {
    await fetch(API + "/auth/logout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: token }),
    });
  } catch (_) {}
}

async function tryRefresh() {
  if (!refreshToken) return false;

  try {
    const response = await fetch(API + "/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!response.ok) return false;

    const data = await response.json();
    if (!data.access_token) return false;

    accessToken = data.access_token;
    refreshToken = data.refresh_token || refreshToken;
    return true;
  } catch (_) {
    return false;
  }
}

async function request(path, options = {}, responseType = "json", retried = false) {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (accessToken) headers.set("Authorization", "Bearer " + accessToken);

  const response = await fetch(API + path, { ...options, headers });
  if (response.status === 401 && accessToken && !retried && path !== "/auth/refresh") {
    if (await tryRefresh()) return request(path, options, responseType, true);
  }

  const hasBody = response.status !== 204
    && response.status !== 205
    && response.headers.get("content-length") !== "0";

  if (!response.ok) {
    let detail = response.statusText;
    if (hasBody) {
      try {
        const text = await response.text();
        if (text) detail = JSON.parse(text).detail;
      } catch (_) {}
    }
    throw new Error(messaggioOperatore(detail, response.status));
  }

  if (!hasBody) return null;
  if (responseType === "blob") return response.blob();

  const text = await response.text();
  if (!text) return null;

  const contentType = response.headers.get("content-type") || "";
  return contentType.includes("application/json") ? JSON.parse(text) : text;
}

export function api(path, options = {}) {
  return request(path, options);
}

export function apiBlob(path, body) {
  return request(path, {
    method: "POST",
    body: JSON.stringify(body),
  }, "blob");
}

export function apiGetBlob(path) {
  return request(path, { method: "GET" }, "blob");
}
