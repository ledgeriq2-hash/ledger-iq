import React, { createContext, useCallback, useEffect, useMemo, useState } from "react";
import authApi from "../api/authApi.js";
import axiosClient, { ACCESS_TOKEN_STORAGE_KEY } from "../api/index";

const loadStored = (key) => (typeof window !== "undefined" ? localStorage.getItem(key) : null);
const LAST_TENANT_ID_KEY = "ledgeriqlastTenantId";

export const AuthContext = createContext({
  user: null,
  tenant: null,
  tenantId: null,
  actorId: null,
  accessToken: null,
  tenantOptions: [],
  tenantOptionsLoading: false,
  loading: false,
  error: null,
  login: async () => {},
  register: async () => {},
  logout: () => {},
  refresh: async () => {},
  fetchCurrentUser: async () => {},
  bootstrapDemoTenant: async () => {},
  isAuthenticated: false,
  hasRole: () => false,
  softLaunchBadge: false,
  setTenantId: () => {},
  setActorId: () => {},
});

export const AuthProvider = ({ children }) => {
  const [tenant, setTenant] = useState(null);
  const [user, setUser] = useState(null);
  const [tenantId, setTenantIdState] = useState(
    import.meta.env.VITE_TENANT_ID || loadStored("tenant_id")
  );
  const [actorId, setActorIdState] = useState(
    import.meta.env.VITE_ACTOR_ID || loadStored("actor_id")
  );
  const [accessToken, setAccessTokenState] = useState(loadStored(ACCESS_TOKEN_STORAGE_KEY));
  const [tenantOptions, setTenantOptions] = useState([]);
  const [tenantOptionsLoading, setTenantOptionsLoading] = useState(false);
  const [tenantOptionsLoaded, setTenantOptionsLoaded] = useState(false);
  const [softLaunchBadge, setSoftLaunchBadge] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const roles = useMemo(() => {
    if (!user) return [];
    const collected = [];
    if (user.roles) {
      collected.push(...(Array.isArray(user.roles) ? user.roles : [user.roles]));
    }
    if (user.role) {
      collected.push(user.role.name || user.role);
    }
    if (user.role_id && collected.length === 0) {
      collected.push("owner");
    }
    if (user.is_superuser) {
      collected.push("owner", "admin");
    }
    return collected;
  }, [user]);

  const roleIndex = useMemo(
    () => roles.map((role) => String(role).toLowerCase()),
    [roles]
  );

  const persistToken = (token) => {
    const next = token || null;
    setAccessTokenState(next);
    if (typeof window !== "undefined") {
      if (next) localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, next);
      else localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
    }
  };

  const setTenantId = useCallback((value) => {
    const next = value || null;
    setTenantIdState(next);
    if (typeof window !== "undefined") {
      if (next) {
        localStorage.setItem("tenant_id", next);
        localStorage.setItem(LAST_TENANT_ID_KEY, next);
      } else {
        localStorage.removeItem("tenant_id");
      }
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    let active = true;
    const envTenantId = import.meta.env.VITE_TENANT_ID;
    if (envTenantId && !tenantId) {
      setTenantId(envTenantId);
    }
    setTenantOptionsLoading(true);
    const loadTenants = async () => {
      let items = [];
      try {
        const res = await axiosClient.request({
          method: "GET",
          url: "/v1/dev/tenants",
          skipTenant: true,
          skipAuth: true,
        });
        items = Array.isArray(res?.data?.items) ? res.data.items : [];
      } catch (err) {
        if (accessToken) {
          try {
            const me = await authApi.me();
            if (me?.tenant) {
              items = [me.tenant];
            }
          } catch (meErr) {
            items = [];
          }
        }
      }
      if (!active) return;
      setTenantOptions(items);
      setTenantOptionsLoading(false);
      setTenantOptionsLoaded(true);
    };
    loadTenants();
    return () => {
      active = false;
    };
  }, [setTenantId, tenantId, accessToken]);

  useEffect(() => {
    if (!tenantOptionsLoaded) return;
    const items = Array.isArray(tenantOptions) ? tenantOptions : [];
    const lastTenantId = loadStored(LAST_TENANT_ID_KEY);
    const legacySlug = loadStored("tenant_slug");

    if (tenantId && items.length) {
      const matched = items.find((tenantItem) => tenantItem.id === tenantId);
      if (matched) {
        setTenant(matched);
        if (legacySlug) {
          localStorage.removeItem("tenant_slug");
        }
        return;
      }
      setTenant(null);
      setTenantId(null);
      return;
    }

    if (!tenantId) {
      if (legacySlug) {
        const matched = items.find((tenantItem) => tenantItem.slug === legacySlug);
        if (matched) {
          setTenantId(matched.id);
          setTenant(matched);
          localStorage.removeItem("tenant_slug");
          return;
        }
        localStorage.removeItem("tenant_slug");
      }

      if (lastTenantId && items.some((tenantItem) => tenantItem.id === lastTenantId)) {
        const matched = items.find((tenantItem) => tenantItem.id === lastTenantId);
        if (matched) {
          setTenantId(matched.id);
          setTenant(matched);
          return;
        }
      }

      if (items.length === 1) {
        setTenantId(items[0].id);
        setTenant(items[0]);
      }
    }
  }, [tenantOptionsLoaded, tenantOptions, tenantId, setTenantId, setTenant]);

  useEffect(() => {
    if (!tenantId) {
      setTenant(null);
    }
  }, [tenantId, setTenant]);

  const setActorId = useCallback((value) => {
    const next = value || null;
    setActorIdState(next);
    if (typeof window !== "undefined") {
      if (next) localStorage.setItem("actor_id", next);
      else localStorage.removeItem("actor_id");
    }
  }, []);

  const login = async (credentials) => {
    setLoading(true);
    setError(null);
    try {
      const res = await authApi.login(credentials);
      const tokens = res?.tokens || res?.token;
      persistToken(tokens?.access_token || null);
      const tenantPayload = res?.tenant || null;
      const userPayload = res?.user || null;
      setTenant(tenantPayload);
      setUser(userPayload);
      setTenantId(tenantPayload?.id || credentials?.tenant || tenantId);
      setActorId(userPayload?.id || null);
      setSoftLaunchBadge(res?.soft_launch_badge === true);
      return res;
    } catch (err) {
      setError(err?.message || "Login failed");
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const register = async (payload) => {
    setLoading(true);
    setError(null);
    try {
      const res = await authApi.register(payload);
      const tokens = res?.tokens || res?.token;
      persistToken(tokens?.access_token || null);
      const tenantPayload = res?.tenant || null;
      const userPayload = res?.user || null;
      setTenant(tenantPayload);
      setUser(userPayload);
      setTenantId(tenantPayload?.id || tenantId);
      setActorId(userPayload?.id || null);
      setSoftLaunchBadge(res?.soft_launch_badge === true);
      return res;
    } catch (err) {
      setError(err?.message || "Signup failed");
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const refresh = async (payload = {}) => {
    const res = await authApi.refresh(payload);
    if (res?.access_token) {
      persistToken(res.access_token);
    }
    return res;
  };

  const fetchCurrentUser = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await authApi.me();
      setUser(res?.user || res || null);
      if (res?.tenant) {
        setTenant(res.tenant);
        setTenantId(res.tenant.id || tenantId);
      }
      return res;
    } catch (err) {
      setError(err?.message || "Failed to load current user");
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } catch (err) {
      console.warn("Logout failed", err);
    }
    persistToken(null);
    setTenant(null);
    setUser(null);
    setTenantId(null);
    setActorId(null);
    setSoftLaunchBadge(false);
    setError(null);
    if (typeof window !== "undefined") {
      localStorage.removeItem(LAST_TENANT_ID_KEY);
    }
  };

  const bootstrapDemoTenant = useCallback(async () => {
    const suffix = Date.now().toString(36);
    const payload = {
      seed_demo: true,
      tenant: {
        name: `Demo Company ${suffix}`,
        slug: `demo-${suffix}`,
      },
      admin: {
        email: `admin-${suffix}@example.com`,
        password: "Test1234",
        full_name: "Demo Admin",
      },
    };
    const res = await axiosClient.request({
      method: "POST",
      url: "/v1/dev/bootstrap",
      data: payload,
      skipTenant: true,
      skipAuth: true,
    });
    const createdId = res?.data?.tenant_id || res?.data?.tenant?.id || "";
    if (!createdId) {
      throw new Error("Bootstrap response missing tenant_id");
    }
    const accessToken = res?.data?.access_token;
    if (accessToken) {
      persistToken(accessToken);
    }
    if (res?.data?.tenant) {
      setTenant(res.data.tenant);
    }
    setTenantId(createdId);
    return res?.data;
  }, [persistToken, setTenantId]);

  const value = useMemo(
    () => ({
      user,
      tenant,
      tenantId,
      actorId,
      accessToken,
      tenantOptions,
      tenantOptionsLoading,
      loading,
      error,
      login,
      register,
      logout,
      refresh,
      fetchCurrentUser,
      bootstrapDemoTenant,
      isAuthenticated: Boolean(tenantId),
      hasRole: (role) => roleIndex.includes(String(role).toLowerCase()),
      softLaunchBadge,
      setTenantId,
      setActorId,
    }),
    [
      user,
      tenant,
      tenantId,
      actorId,
      accessToken,
      tenantOptions,
      tenantOptionsLoading,
      loading,
      error,
      softLaunchBadge,
      roleIndex,
      bootstrapDemoTenant,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
