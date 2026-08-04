import { createContext, useCallback, useContext, useMemo, useState } from "react";
import api, { AUTH_TOKEN_KEY } from "../services/api";

const AUTH_USER_KEY = "auth_current_user";

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

  const logout = useCallback(() => {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_USER_KEY);
    setToken(null);
    setCurrentUser(null);
  }, []);

  const login = useCallback(async ({ email, password }) => {
    const form = new URLSearchParams();
    form.append("username", email);
    form.append("password", password);

    const response = await api.post("/auth/login", form, {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });

    const nextToken = response?.data?.access_token ?? response?.data?.token ?? null;
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
      isAuthenticated: Boolean(token),
    }),
    [login, logout, currentUser, token]
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
