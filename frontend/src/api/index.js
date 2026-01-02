import axios from "axios";

const DEFAULT_TIMEOUT = 15000;
const ACCESS_TOKEN_KEY = "access_token";
const API_BASE_PATH = "/api";
const API_VERSION_PREFIX = "/v1";
const LEGACY_API_PREFIX = `${API_BASE_PATH}${API_VERSION_PREFIX}`;
const DUPLICATE_LEGACY_PREFIX = `${LEGACY_API_PREFIX}${LEGACY_API_PREFIX}`;
const DUPLICATE_VERSION_PREFIX = `${API_VERSION_PREFIX}${API_VERSION_PREFIX}`;
export const ACCESS_TOKEN_STORAGE_KEY = ACCESS_TOKEN_KEY;

const getEnvValue = (key) => {
  if (typeof import.meta.env[key] !== "string") return "";
  return import.meta.env[key].trim();
};

const trimSuffix = (value) => value.replace(/\/+$/, "");
const isAbsoluteUrl = (value = "") => /^https?:\/\//i.test(value);
const ensureLeadingSlash = (value = "") => {
  if (isAbsoluteUrl(value)) return value;
  return value.startsWith("/") ? value : `/${value}`;
};

const resolveOrigin = () => {
  const override = trimSuffix(getEnvValue("VITE_API_ORIGIN"));
  if (override) return override;
  if (typeof window !== "undefined") {
    return trimSuffix(window.location.origin);
  }
  return "";
};

const resolveBaseURL = () => {
  const origin = resolveOrigin();
  if (origin) {
    return `${origin}${API_BASE_PATH}`;
  }
  return API_BASE_PATH;
};

export const API_BASE_URL = resolveBaseURL() || undefined;

const normalizeRequestPath = (url = "") => {
  if (!url || isAbsoluteUrl(url)) return url;
  let normalized = ensureLeadingSlash(url);

  if (normalized.startsWith(`${API_BASE_PATH}/`)) {
    normalized = normalized.slice(API_BASE_PATH.length);
  } else if (normalized === API_BASE_PATH) {
    normalized = "/";
  }

  return normalized.replace(/\/{2,}/g, "/");
};

const getResolvedUrl = (config = {}) => {
  const url = config.url || "";
  if (!url) return "unknown url";
  try {
    const base = config.baseURL || (typeof window !== "undefined" ? window.location.origin : "");
    return new URL(url, base || undefined).toString();
  } catch {
    if (config.baseURL) {
      return `${config.baseURL.replace(/\/$/, "")}${url}`;
    }
    return url;
  }
};

const shouldSkipTenant = (url = "", config = {}) => {
  if (config.skipTenant === true) return true;
  const normalized = ensureLeadingSlash(url);
  return (
    normalized.startsWith(`${API_VERSION_PREFIX}/auth/`) ||
    normalized.startsWith("/auth/") ||
    normalized.startsWith("/health") ||
    normalized.startsWith(`${API_VERSION_PREFIX}/portal/`) ||
    normalized.startsWith("/portal/")
  );
};

const shouldSkipAuth = (url = "", config = {}) => {
  if (config.skipAuth === true) return true;
  const normalized = ensureLeadingSlash(url);
  return normalized.startsWith(`${API_VERSION_PREFIX}/portal/`) || normalized.startsWith("/portal/");
};

const isAuthRoute = (url = "") => {
  const normalized = ensureLeadingSlash(url);
  return (
    normalized.startsWith(`${API_VERSION_PREFIX}/auth/`) ||
    normalized.startsWith("/auth/") ||
    normalized.startsWith(`${API_VERSION_PREFIX}/portal/`) ||
    normalized.startsWith("/portal/")
  );
};

const guardApiPath = (baseURL, url) => {
  const combined = `${baseURL || ""}${url || ""}`;
  if (combined.includes(DUPLICATE_LEGACY_PREFIX) || combined.includes(DUPLICATE_VERSION_PREFIX)) {
    throw new Error(`API path misconfigured (contains duplicated API prefix): ${combined}`);
  }
};

const getAccessToken = () => {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_TOKEN_KEY);
};

let errorNotifier = null;

export const setErrorNotifier = (notifier) => {
  errorNotifier = notifier || null;
};

export const TENANT_NOT_SET_ERROR = {
  code: "TENANT_NOT_SET",
  message: "Tenant not set",
};

const clearTenantContext = () => {
  if (typeof window === "undefined") return;
  localStorage.removeItem("tenant_id");
  localStorage.removeItem("actor_id");
};

const normalizeError = (error) => {
  if (error && typeof error === "object" && !error?.response && error?.code && error?.message) {
    return {
      status: error?.status ?? null,
      code: error.code,
      message: error.message,
      raw: error?.raw ?? error,
    };
  }

  const status = error?.response?.status;
  const data = error?.response?.data;
  const message =
    data?.message ||
    data?.error?.message ||
    data?.detail ||
    error?.message ||
    "Unexpected error. Please try again.";
  const code = data?.code || data?.error?.code || status || "unknown_error";
  return { status, code, message, raw: error };
};

const axiosClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: DEFAULT_TIMEOUT,
  withCredentials: true,
});

axiosClient.interceptors.request.use(
  (config) => {
    const resolvedBase = config.baseURL || API_BASE_URL;
    const normalizedUrl = normalizeRequestPath(config.url || "");
    config.baseURL = resolvedBase || undefined;
    config.url = normalizedUrl;
    guardApiPath(config.baseURL, config.url);

    const tenantId =
      config.headers?.["X-Tenant-Id"] ||
      (typeof window !== "undefined" ? localStorage.getItem("tenant_id") : null) ||
      import.meta.env.VITE_TENANT_ID;
    const actorId =
      config.headers?.["X-Actor-Id"] ||
      import.meta.env.VITE_ACTOR_ID ||
      (typeof window !== "undefined" ? localStorage.getItem("actor_id") : null);

    const token = config.headers?.Authorization || getAccessToken();

    config.headers = config.headers || {};

    if (!shouldSkipTenant(config.url, config)) {
      if (!tenantId) {
        return Promise.reject(TENANT_NOT_SET_ERROR);
      }
      config.headers["X-Tenant-Id"] = tenantId;
      if (actorId) {
        config.headers["X-Actor-Id"] = actorId;
      }
    }

    if (token && !config.headers.Authorization && !shouldSkipAuth(config.url, config)) {
      config.headers.Authorization = token.startsWith("Bearer ") ? token : `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

axiosClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error?.response?.status;
    const normalized = normalizeError(error);
    const resolvedUrl = getResolvedUrl(error?.config);
    const method = (error?.config?.method || "request").toUpperCase();
    const token = getAccessToken();

    console.error(`[API] ${method} failed (${resolvedUrl})`, {
      status,
      error: normalized,
    });

    if (
      status === 401 &&
      !token &&
      typeof window !== "undefined" &&
      !isAuthRoute(error?.config?.url || "")
    ) {
      const path = window.location.pathname || "";
      if (!path.startsWith("/login")) {
        window.location.assign("/login");
      }
    }

    if (
      status === 404 &&
      typeof window !== "undefined" &&
      (normalized?.code === "tenant_not_found" ||
        String(normalized?.message || "").toLowerCase().includes("tenant not found"))
    ) {
      clearTenantContext();
      window.location.assign("/onboarding/tenant");
    }

    if (normalized?.code !== "TENANT_NOT_SET" && errorNotifier && (!status || status >= 500)) {
      errorNotifier({
        title: "Request failed",
        message: normalized.message,
        status,
      });
    }

    return Promise.reject(normalized);
  }
);

export default axiosClient;
