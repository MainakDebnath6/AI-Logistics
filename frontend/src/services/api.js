import axios from "axios";

const rawBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const API_BASE_URL = String(rawBaseUrl).replace(/\/+$/, "");
export const AUTH_TOKEN_KEY = "auth_token";
export const AUTH_USER_KEY = "auth_current_user";

function buildApiError(error) {
  const status = error?.response?.status;
  const detail = error?.response?.data?.detail;

  let message = error?.message || "Request failed.";

  if (typeof detail === "string" && detail.trim()) {
    message = detail;
  } else if (Array.isArray(detail) && detail.length > 0) {
    message = detail.map((item) => item?.msg || "Validation error").join("; ");
  } else if (detail && typeof detail === "object" && typeof detail.message === "string") {
    message = detail.message;
  }

  const normalizedError = new Error(message);
  normalizedError.status = status;
  normalizedError.detail = detail;
  normalizedError.response = error?.response;
  normalizedError.originalError = error;
  return normalizedError;
}

export function getApiErrorMessage(error, fallback = "Unexpected error.") {
  if (error instanceof Error && typeof error.message === "string" && error.message.trim()) {
    return error.message;
  }

  const detail = error?.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  if (Array.isArray(detail) && detail.length > 0) {
    return detail.map((item) => item?.msg || "Validation error").join("; ");
  }

  return fallback;
}

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    if (token) {
      config.headers = config.headers || {};
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      localStorage.removeItem(AUTH_TOKEN_KEY);
      localStorage.removeItem(AUTH_USER_KEY);

      if (typeof window !== "undefined") {
        window.dispatchEvent(new Event("auth:unauthorized"));
      }
    }

    return Promise.reject(buildApiError(error));
  }
);

export default api;
