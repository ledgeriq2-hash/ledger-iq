import React, { createContext, useCallback, useEffect, useMemo, useState } from "react";
import authApi from "../api/authApi";
import { setAuthStateUpdater } from "../api/axiosClient";

export const AuthContext = createContext({
  user: null,
  tenant: null,
  accessToken: null,
  loading: false,
  error: null,
  login: async () => {},
  logout: () => {},
  refresh: async () => {},
  fetchCurrentUser: async () => {},
  isAuthenticated: false,
  hasRole: () => false,
  softLaunchBadge: false,
});

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [tenant, setTenant] = useState(null);
  const [accessToken, setAccessToken] = useState(localStorage.getItem("access_token"));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [softLaunchBadge, setSoftLaunchBadge] = useState(false);

  const setTokens = useCallback((access, refresh, tenantId) => {
    if (access) localStorage.setItem("access_token", access);
    if (refresh) localStorage.setItem("refresh_token", refresh);
    if (tenantId) localStorage.setItem("tenant_id", tenantId);
    setAccessToken(access || null);
  }, []);

  const clearTokens = useCallback(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("tenant_id");
    setAccessToken(null);
  }, []);

  useEffect(() => {
    setAuthStateUpdater(({ accessToken: newAccess }) => {
      setAccessToken(newAccess || null);
      if (!newAccess) {
        setUser(null);
      }
    });
  }, []);

  const fetchCurrentUser = useCallback(async () => {
    if (!localStorage.getItem("access_token")) return null;
    setLoading(true);
    try {
      const data = await authApi.me();
      setUser(data.user || data);
      setTenant(data.tenant || null);
      setSoftLaunchBadge(Boolean(data.soft_launch_badge));
      return data;
    } catch {
      setUser(null);
      setTenant(null);
      setSoftLaunchBadge(false);
    } finally {
      setLoading(false);
    }
  }, []);

  const login = useCallback(
    async ({ email, password, tenant }) => {
      setLoading(true);
      setError(null);
      try {
        const data = await authApi.login({ email, password, tenant });
        const access = data?.tokens?.access_token || data?.access_token;
        const refreshToken = data?.tokens?.refresh_token || data?.refresh_token;
        const tenantId = data?.tenant?.id || tenant;
        setTokens(access, refreshToken, tenantId);
        setUser(data?.user || data);
        setTenant(data?.tenant || null);
        setSoftLaunchBadge(Boolean(data?.soft_launch_badge));
        return data;
      } catch (err) {
        setError(err?.response?.data?.detail || "Login failed");
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [setTokens]
  );

  const refresh = useCallback(async () => {
    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) return null;
    const data = await authApi.refresh({ refresh_token: refreshToken });
    const access = data?.access_token || data?.tokens?.access_token;
    const refreshValue = data?.refresh_token || data?.tokens?.refresh_token;
    setTokens(access, refreshValue, localStorage.getItem("tenant_id"));
    return data;
  }, [setTokens]);

  const logout = useCallback(async () => {
    clearTokens();
    setUser(null);
    setTenant(null);
    setSoftLaunchBadge(false);
    try {
      const refreshToken = localStorage.getItem("refresh_token");
      await authApi.logout(refreshToken ? { refresh_token: refreshToken } : {});
    } catch {
      // ignore logout errors
    }
  }, [clearTokens]);

  useEffect(() => {
    fetchCurrentUser();
  }, [fetchCurrentUser]);

  const isAuthenticated = !!accessToken && !!user;

  const hasRole = useCallback(
    (role) => {
      if (!role || !user) return false;
      const currentRole = user.role?.name || user.role || user.role_id;
      return String(currentRole || "").toLowerCase() === String(role).toLowerCase();
    },
    [user]
  );

  const value = useMemo(
    () => ({
      user,
      tenant,
      accessToken,
      loading,
      error,
      login,
      logout,
      refresh,
      fetchCurrentUser,
      isAuthenticated,
      hasRole,
      softLaunchBadge,
    }),
    [user, tenant, accessToken, loading, error, login, logout, refresh, fetchCurrentUser, isAuthenticated, hasRole, softLaunchBadge]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
