import api from "./api";

const OPTIMIZATION_ENDPOINT = "/optimization/optimize";

function createApiError(error, fallbackMessage = "Request failed.") {
  const detail = error?.response?.data?.detail;

  let message = fallbackMessage;
  if (typeof detail === "string" && detail.trim()) {
    message = detail;
  } else if (Array.isArray(detail) && detail.length > 0) {
    message = detail.map((item) => item?.msg || "Validation error").join("; ");
  } else if (typeof error?.message === "string" && error.message.trim()) {
    message = error.message;
  }

  const normalizedError = new Error(message);
  normalizedError.status = error?.response?.status;
  normalizedError.detail = detail;
  normalizedError.response = error?.response;
  normalizedError.originalError = error;
  return normalizedError;
}

export function getApiErrorMessage(error, fallbackMessage = "Unexpected error.") {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallbackMessage;
}

export async function optimizeRoutes(payload) {
  try {
    const response = await api.post(OPTIMIZATION_ENDPOINT, payload);
    return response.data;
  } catch (error) {
    throw createApiError(error, "Failed to optimize routes.");
  }
}
