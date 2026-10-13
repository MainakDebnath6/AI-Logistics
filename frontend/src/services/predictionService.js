import api from "./api";

export async function forecastDemandForHorizon(payload) {
  const response = await api.post("/predictions/demand/horizon", payload);
  return response.data;
}

export async function assessForecastCapacity(payload) {
  const response = await api.post("/predictions/hgfc/from-history", payload);
  return response.data;
}