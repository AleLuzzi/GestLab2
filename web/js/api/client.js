const API = "";

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
        if (text) {
          const body = JSON.parse(text);
          detail = body.detail || JSON.stringify(body);
        }
      } catch (_) {}
    }
    throw new Error(detail);
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
