import api from "./api";

const VEHICLES_ENDPOINT = "/vehicles";

function buildListParams(options = {}) {
  const params = {};

  if (typeof options.skip === "number") {
    params.skip = options.skip;
  }
  if (typeof options.limit === "number") {
    params.limit = options.limit;
  }

  return params;
}

export async function getVehicles(options = {}) {
  const response = await api.get(VEHICLES_ENDPOINT, {
    params: buildListParams(options),
  });
  return response.data;
}

export async function getVehicle(vehicleId) {
  const response = await api.get(`${VEHICLES_ENDPOINT}/${vehicleId}`);
  return response.data;
}

export async function createVehicle(payload) {
  const response = await api.post(VEHICLES_ENDPOINT, payload);
  return response.data;
}

export async function updateVehicle(vehicleId, payload) {
  const response = await api.put(`${VEHICLES_ENDPOINT}/${vehicleId}`, payload);
  return response.data;
}

export async function deleteVehicle(vehicleId) {
  const response = await api.delete(`${VEHICLES_ENDPOINT}/${vehicleId}`);
  return response.data;
}
