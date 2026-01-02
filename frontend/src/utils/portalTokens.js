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
