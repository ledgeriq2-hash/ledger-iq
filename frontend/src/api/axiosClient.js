import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  "http://localhost:8000/api/v1";

let authStateUpdater = null;
let errorNotifier = null;

export const setAuthStateUpdater = (updater) => {
  authStateUpdater = updater;
};

export const setErrorNotifier = (notifier) => {
  errorNotifier = notifier || null;
};

const normalizeError = (error) => {
  const status = error?.response?.status;
  const data = error?.response?.data;
  const message =
    data?.error?.message ||
    data?.message ||
    error?.message ||
    "Unexpected error. Please try again.";
  const code = data?.error?.code || data?.code || status || "unknown_error";
  return { status, code, message, raw: error };
};

const persistTokens = (accessToken, refreshToken) => {
  if (accessToken) localStorage.setItem("access_token", accessToken);
  if (refreshToken) localStorage.setItem("refresh_token", refreshToken);
  authStateUpdater?.({ accessToken, refreshToken });
};

const clearTokens = () => {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  authStateUpdater?.({ accessToken: null, refreshToken: null });
};

const axiosClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

axiosClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    const tenantId = localStorage.getItem("tenant_id");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    if (tenantId) {
      config.headers["X-Tenant-ID"] = tenantId;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

let isRefreshing = false;
let refreshPromise = null;

const refreshAccessToken = async () => {
  const refreshToken = localStorage.getItem("refresh_token");
  if (!refreshToken) {
    clearTokens();
    throw new Error("No refresh token");
  }
  const plainAxios = axios.create({ baseURL: API_BASE_URL });
  const response = await plainAxios.post("/auth/refresh", { refresh_token: refreshToken });
  const { access_token: newAccess, refresh_token: newRefresh } = response.data || {};
  persistTokens(newAccess, newRefresh);
  return newAccess;
};

axiosClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config || {};
    const status = error?.response?.status;
    if (status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        if (!isRefreshing) {
          isRefreshing = true;
          refreshPromise = refreshAccessToken().finally(() => {
            isRefreshing = false;
          });
        }
        const newAccess = await refreshPromise;
        if (newAccess) {
          originalRequest.headers = originalRequest.headers || {};
          originalRequest.headers.Authorization = `Bearer ${newAccess}`;
          return axiosClient(originalRequest);
        }
      } catch (refreshError) {
        clearTokens();
        if (typeof window !== "undefined") {
          window.location.replace("/login");
        }
      }
    }
    const normalized = normalizeError(error);
    if (status === 401) {
      clearTokens();
      if (typeof window !== "undefined") {
        window.location.replace("/login");
      }
    }
    if (errorNotifier && (!status || status >= 500)) {
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
