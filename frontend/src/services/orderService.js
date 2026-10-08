import api from "./api";

const ORDERS_ENDPOINT = "/orders";

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

export async function getOrders(options = {}) {
  const response = await api.get(ORDERS_ENDPOINT, {
    params: buildListParams(options),
  });
  return response.data;
}

export async function getOrder(orderId) {
  const response = await api.get(`${ORDERS_ENDPOINT}/${orderId}`);
  return response.data;
}

export async function createOrder(payload) {
  const response = await api.post(ORDERS_ENDPOINT, payload);
  return response.data;
}

export async function updateOrder(orderId, payload) {
  const response = await api.put(`${ORDERS_ENDPOINT}/${orderId}`, payload);
  return response.data;
}

export async function deleteOrder(orderId) {
  const response = await api.delete(`${ORDERS_ENDPOINT}/${orderId}`);
  return response.data;
}
