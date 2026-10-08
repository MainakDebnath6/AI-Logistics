import api from "./api";

const DRIVERS_ENDPOINT = "/drivers";

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

export async function getDrivers(options = {}) {
  const response = await api.get(DRIVERS_ENDPOINT, {
    params: buildListParams(options),
  });
  return response.data;
}

export async function getDriver(driverId) {
  const response = await api.get(`${DRIVERS_ENDPOINT}/${driverId}`);
  return response.data;
}

export async function createDriver(payload) {
  const response = await api.post(DRIVERS_ENDPOINT, payload);
  return response.data;
}

export async function updateDriver(driverId, payload) {
  const response = await api.put(`${DRIVERS_ENDPOINT}/${driverId}`, payload);
  return response.data;
}

export async function deleteDriver(driverId) {
  const response = await api.delete(`${DRIVERS_ENDPOINT}/${driverId}`);
  return response.data;
}
