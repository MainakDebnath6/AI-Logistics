import api from "./api";

const ANALYTICS_DASHBOARD_ENDPOINT = "/analytics/dashboard";

function toNumber(value) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function getAtPath(source, path) {
  if (!source || typeof source !== "object") {
    return undefined;
  }

  return path.split(".").reduce((current, segment) => {
    if (current && typeof current === "object" && segment in current) {
      return current[segment];
    }
    return undefined;
  }, source);
}

function pickNumber(source, paths) {
  for (const path of paths) {
    const rawValue = getAtPath(source, path);
    const numericValue = toNumber(rawValue);
    if (numericValue !== null) {
      return numericValue;
    }
  }
  return null;
}

function pickArray(source, paths) {
  for (const path of paths) {
    const value = getAtPath(source, path);
    if (Array.isArray(value)) {
      return value;
    }
  }
  return [];
}

function pickObject(source, paths) {
  for (const path of paths) {
    const value = getAtPath(source, path);
    if (value && typeof value === "object" && !Array.isArray(value)) {
      return value;
    }
  }
  return null;
}

function normalizePayload(payload) {
  if (payload && typeof payload === "object" && payload.data && typeof payload.data === "object") {
    return payload.data;
  }
  return payload && typeof payload === "object" ? payload : {};
}

export async function getDashboardAnalytics() {
  const response = await api.get(ANALYTICS_DASHBOARD_ENDPOINT);
  return response.data;
}

export function normalizeDashboardAnalytics(payload) {
  const source = normalizePayload(payload);

  return {
    totalOrders: pickNumber(source, [
      "total_orders",
      "totalOrders",
      "orders.total",
      "orders.count",
      "summary.total_orders",
      "dashboard.total_orders",
    ]),
    completedOrders: pickNumber(source, [
      "completed_orders",
      "completedOrders",
      "orders.completed",
      "summary.completed_orders",
      "dashboard.completed_orders",
    ]),
    pendingOrders: pickNumber(source, [
      "pending_orders",
      "pendingOrders",
      "orders.pending",
      "summary.pending_orders",
      "dashboard.pending_orders",
    ]),
    totalDrivers: null,
    totalVehicles: null,
    fleetUtilization: pickNumber(source, [
      "vehicle_utilization_percentage",
      "vehicle_utilization",
      "vehicleUtilization",
    ]),
    vehicleUtilization: pickNumber(source, [
      "vehicle_utilization_percentage",
      "vehicle_utilization",
      "vehicleUtilization",
      "utilization.vehicle",
      "summary.vehicle_utilization",
      "dashboard.vehicle_utilization",
    ]),
    driverUtilization: pickNumber(source, [
      "driver_utilization_percentage",
      "driver_utilization",
      "driverUtilization",
      "utilization.driver",
      "summary.driver_utilization",
      "dashboard.driver_utilization",
    ]),
    routeEfficiency: pickNumber(source, [
      "route_efficiency_percentage",
      "route_efficiency",
      "routeEfficiency",
      "efficiency.route",
      "summary.route_efficiency",
      "dashboard.route_efficiency",
    ]),
    averageEta: pickNumber(source, [
      "average_eta_minutes",
      "average_eta",
      "averageEta",
      "eta.average",
      "summary.average_eta",
      "dashboard.average_eta",
    ]),
    onTimeDelivery: pickNumber(source, [
      "on_time_delivery_percentage",
      "on_time_delivery",
      "onTimeDelivery",
      "delivery.on_time",
      "summary.on_time_delivery",
      "dashboard.on_time_delivery",
    ]),
    distanceCovered: pickNumber(source, [
      "average_route_distance_km",
      "distance_covered",
      "distanceCovered",
      "distance.total",
      "summary.distance_covered",
      "dashboard.distance_covered",
    ]),
    orderStatusMap: pickObject(source, [
      "order_status",
      "orderStatus",
      "orders.status",
      "dashboard.order_status",
    ]),
    utilizationTrend: pickArray(source, [
      "utilization_trend",
      "utilizationTrend",
      "trends.utilization",
      "dashboard.utilization_trend",
    ]),
    kpiTrend: pickArray(source, [
      "kpi_trend",
      "kpiTrend",
      "trends.kpi",
      "dashboard.kpi_trend",
    ]),
    etaDistanceTrend: pickArray(source, [
      "eta_distance_trend",
      "etaDistanceTrend",
      "trends.eta_distance",
      "dashboard.eta_distance_trend",
    ]),
  };
}

export function buildOrderStatusChartData(analytics) {
  if (!analytics) {
    return [];
  }

  if (analytics.orderStatusMap) {
    return Object.entries(analytics.orderStatusMap)
      .map(([name, value]) => ({ name, value: toNumber(value) }))
      .filter((item) => item.value !== null);
  }

  const fallback = [
    { name: "Completed", value: analytics.completedOrders },
    { name: "Pending", value: analytics.pendingOrders },
  ].filter((item) => typeof item.value === "number");

  return fallback;
}

export function buildUtilizationBreakdown(analytics) {
  if (!analytics) {
    return [];
  }

  const candidates = [{ name: "Vehicles", value: analytics.vehicleUtilization }, { name: "Drivers", value: analytics.driverUtilization }];

  return candidates.filter((item) => typeof item.value === "number");
}

export function buildKpiTrendSeries(analytics) {
  if (!analytics) {
    return [];
  }

  if (Array.isArray(analytics.kpiTrend) && analytics.kpiTrend.length > 0) {
    return analytics.kpiTrend.map((item, index) => ({
      label: item.label || item.period || item.name || `T${index + 1}`,
      routeEfficiency:
        toNumber(item.routeEfficiency ?? item.route_efficiency ?? item.efficiency) ?? null,
      onTimeDelivery:
        toNumber(item.onTimeDelivery ?? item.on_time_delivery ?? item.on_time) ?? null,
    }));
  }

  if (
    typeof analytics.routeEfficiency === "number" ||
    typeof analytics.onTimeDelivery === "number"
  ) {
    return [
      {
        label: "Current",
        routeEfficiency: analytics.routeEfficiency,
        onTimeDelivery: analytics.onTimeDelivery,
      },
    ];
  }

  return [];
}

export function buildEtaVsDistanceData(analytics) {
  if (!analytics) {
    return [];
  }

  if (Array.isArray(analytics.etaDistanceTrend) && analytics.etaDistanceTrend.length > 0) {
    return analytics.etaDistanceTrend.map((item, index) => ({
      label: item.label || item.period || item.name || `T${index + 1}`,
      averageEta: toNumber(item.averageEta ?? item.average_eta ?? item.eta) ?? null,
      distanceCovered:
        toNumber(item.distanceCovered ?? item.distance_covered ?? item.distance) ?? null,
    }));
  }

  if (typeof analytics.averageEta === "number" || typeof analytics.distanceCovered === "number") {
    return [
      {
        label: "Current",
        averageEta: analytics.averageEta,
        distanceCovered: analytics.distanceCovered,
      },
    ];
  }

  return [];
}
