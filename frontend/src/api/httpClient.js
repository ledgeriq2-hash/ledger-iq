import axiosClient from "./index";

const PORTAL_TOKEN_QUERY_KEY = "portal_token";
const PORTAL_TOKEN_STORAGE_KEY = "portal_token";

let inMemoryPortalToken = null;

const getPortalTokenFromQuery = () => {
  if (typeof window === "undefined") return null;
  const params = new URLSearchParams(window.location.search || "");
  return params.get(PORTAL_TOKEN_QUERY_KEY);
};

export const setPortalToken = (token) => {
  inMemoryPortalToken = token || null;
  if (typeof window === "undefined") return;
  if (token) {
    localStorage.setItem(PORTAL_TOKEN_STORAGE_KEY, token);
  } else {
    localStorage.removeItem(PORTAL_TOKEN_STORAGE_KEY);
  }
};

export const getPortalToken = () => {
  const queryToken = getPortalTokenFromQuery();
  if (queryToken) {
    setPortalToken(queryToken);
    return queryToken;
  }

  if (inMemoryPortalToken) return inMemoryPortalToken;

  if (typeof window !== "undefined") {
    return localStorage.getItem(PORTAL_TOKEN_STORAGE_KEY);
  }

  return null;
};

const withPortalHeaders = (config = {}) => {
  const portalToken = getPortalToken();
  const headers = { ...(config.headers || {}) };

  const tenantId =
    import.meta.env.VITE_TENANT_ID ||
    (typeof window !== "undefined" ? localStorage.getItem("tenant_id") : null);

  const actorId =
    import.meta.env.VITE_ACTOR_ID ||
    (typeof window !== "undefined" ? localStorage.getItem("actor_id") : null);

  if (!tenantId) {
    throw new Error("Missing tenant id: set VITE_TENANT_ID (or localStorage tenant_id)");
  }

  headers["X-Tenant-Id"] = tenantId;
  if (actorId) headers["X-Actor-Id"] = actorId;

  if (portalToken) {
    headers["X-Portal-Token"] = headers["X-Portal-Token"] || portalToken;
  }

  return { ...config, headers };
};

const request = (config) => axiosClient.request(withPortalHeaders(config));

const httpClient = {
  request,
  get: (url, config) => request({ ...config, method: "get", url }),
  post: (url, data, config) => request({ ...config, method: "post", url, data }),
  put: (url, data, config) => request({ ...config, method: "put", url, data }),
  patch: (url, data, config) => request({ ...config, method: "patch", url, data }),
  delete: (url, config) => request({ ...config, method: "delete", url }),
};

export default httpClient;
