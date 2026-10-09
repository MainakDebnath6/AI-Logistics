function statusValue(value) {
  return String(value?.value ?? value ?? "").toLowerCase();
}

function isCoordinateValid(value, minimum, maximum) {
  return typeof value === "number" && Number.isFinite(value) && value >= minimum && value <= maximum;
}

export function getDriverLabel(driver) {
  const name = driver?.full_name || driver?.name;
  const license = driver?.license_number;
  if (name && license) {
    return `${name} · ${license}`;
  }
  return name || (license ? `Driver · ${license}` : `Driver ${driver?.id ?? "-"}`);
}

export function getDriverSelectionIssue(driver, vehicles) {
  if (statusValue(driver?.status) !== "available" || driver?.is_available !== true) {
    return "Driver is not currently available.";
  }
  if (!driver?.vehicle_id) {
    return "No vehicle is assigned to this driver.";
  }
  const vehicle = vehicles.find((item) => String(item.id) === String(driver.vehicle_id));
  if (!vehicle) {
    return "The assigned vehicle is not in the loaded fleet.";
  }
  if (statusValue(vehicle.status) !== "available" || vehicle.is_active !== true) {
    return "The assigned vehicle is unavailable or inactive.";
  }
  return null;
}

export function getVehicleLabel(vehicle) {
  const identity = [vehicle?.registration_number, vehicle?.manufacturer, vehicle?.model]
    .filter(Boolean)
    .join(" · ");
  return identity || `Vehicle ${vehicle?.id ?? "-"}`;
}

export function getVehicleStatus(vehicle) {
  const active = vehicle?.is_active === true ? "Active" : "Inactive";
  const status = statusValue(vehicle?.status) || "unknown";
  return `${status.replaceAll("_", " ")} · ${active}`;
}

export function getOrderSelectionIssue(order) {
  const status = statusValue(order?.status);
  if (status === "cancelled" || status === "delivered") {
    return `Order is ${status} and cannot be optimized.`;
  }
  if (
    !isCoordinateValid(order?.delivery_latitude, -90, 90)
    || !isCoordinateValid(order?.delivery_longitude, -180, 180)
  ) {
    return "Delivery coordinates are missing or invalid.";
  }
  return null;
}

export function getOrderLabel(order) {
  return order?.customer_name || order?.reference || order?.order_number || `Order ${order?.id ?? "-"}`;
}

export function getOrderDescription(order) {
  const status = statusValue(order?.status) || "unknown";
  const demand = Number.isFinite(order?.demand) ? `Demand ${order.demand}` : "Demand unavailable";
  return `${status.replaceAll("_", " ")} · ${demand}${order?.delivery_address ? ` · ${order.delivery_address}` : ""}`;
}