import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import api, { AUTH_TOKEN_KEY, AUTH_USER_KEY } from "../services/api";

const AuthContext = createContext(null);

function decodeJwtPayload(token) {
  try {
    const parts = token.split(".");
    if (parts.length < 2) {
      return null;
    }

    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64 + "=".repeat((4 - (base64.length % 4)) % 4);
    const decoded = atob(padded);
    return JSON.parse(decoded);
  } catch {
    return null;
  }
}

function readStoredUser() {
  const raw = localStorage.getItem(AUTH_USER_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function buildCurrentUser(token, responseData) {
  if (responseData?.user && typeof responseData.user === "object") {
    return responseData.user;
  }

  if (responseData?.data?.user && typeof responseData.data.user === "object") {
    return responseData.data.user;
  }

  const payload = decodeJwtPayload(token);
  if (!payload) {
    return null;
  }

  return {
    id: payload.sub ?? null,
    email: payload.email ?? payload.username ?? null,
    role: payload.role ?? null,
    name: payload.name ?? payload.full_name ?? null,
  };
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(AUTH_TOKEN_KEY));
  const [currentUser, setCurrentUser] = useState(() => readStoredUser());
  const [isAuthLoading, setIsAuthLoading] = useState(true);

  const logout = useCallback(() => {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_USER_KEY);
    setToken(null);
    setCurrentUser(null);
  }, []);

  useEffect(() => {
    const storedToken = localStorage.getItem(AUTH_TOKEN_KEY);
    const storedUser = readStoredUser();

    setToken(storedToken);
    setCurrentUser(storedUser);
    setIsAuthLoading(false);
  }, []);

  useEffect(() => {
    function handleUnauthorized() {
      setToken(null);
      setCurrentUser(null);
      localStorage.removeItem(AUTH_TOKEN_KEY);
      localStorage.removeItem(AUTH_USER_KEY);
    }

    function handleStorage(event) {
      if (event.key !== AUTH_TOKEN_KEY && event.key !== AUTH_USER_KEY) {
        return;
      }

      setToken(localStorage.getItem(AUTH_TOKEN_KEY));
      setCurrentUser(readStoredUser());
    }

    window.addEventListener("auth:unauthorized", handleUnauthorized);
    window.addEventListener("storage", handleStorage);

    return () => {
      window.removeEventListener("auth:unauthorized", handleUnauthorized);
      window.removeEventListener("storage", handleStorage);
    };
  }, []);

  const login = useCallback(async ({ email, password }) => {
    const response = await api.post("/auth/login", {
      email,
      password,
    });

    const nextToken =
      response?.data?.access_token ??
      response?.data?.accessToken ??
      response?.data?.token ??
      response?.data?.data?.access_token ??
      response?.data?.data?.accessToken ??
      null;

    if (!nextToken) {
      throw new Error("No access token returned by login endpoint.");
    }

    const user = buildCurrentUser(nextToken, response.data);

    localStorage.setItem(AUTH_TOKEN_KEY, nextToken);
    if (user) {
      localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(AUTH_USER_KEY);
    }

    setToken(nextToken);
    setCurrentUser(user);

    return { token: nextToken, currentUser: user };
  }, []);

  const value = useMemo(
    () => ({
      login,
      logout,
      currentUser,
      token,
      isAuthLoading,
      isAuthenticated: Boolean(token),
    }),
    [login, logout, currentUser, token, isAuthLoading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider.");
  }
  return context;
}
