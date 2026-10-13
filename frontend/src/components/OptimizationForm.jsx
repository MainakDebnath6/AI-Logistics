import { useEffect, useMemo, useState } from "react";
import { getDrivers } from "../services/driverService";
import { getOrders } from "../services/orderService";
import { getApiErrorMessage, optimizeRoutes } from "../services/optimizationService";
import { getResearchAnalytics, buildSyntheticDemandSeries } from "../services/analyticsService";
import {
  assessForecastCapacity,
  forecastDemandForHorizon,
} from "../services/predictionService";
import { buildForecastReadinessView } from "./forecastReadinessView";
import { getVehicles } from "../services/vehicleService";
import {
  getDriverLabel,
  getDriverSelectionIssue,
  getOrderDescription,
  getOrderLabel,
  getOrderSelectionIssue,
  getVehicleLabel,
  getVehicleStatus,
} from "./optimizationSelection";

function normalizeListResponse(response) {
  if (Array.isArray(response)) {
    return response;
  }
  if (Array.isArray(response?.items)) {
    return response.items;
  }
  if (Array.isArray(response?.data)) {
    return response.data;
  }
  return [];
}

function getItemId(item) {
  return item?.id ?? item?._id ?? item?.uuid ?? null;
}

function SelectionGroup({
  title,
  items,
  selected,
  onToggle,
  disabled,
  getLabel,
  getDescription,
  getDisabledReason,
  readOnly = false,
  emptyLabel,
  searchText,
  onSearchTextChange,
}) {
  const filteredItems = useMemo(() => {
    const query = searchText.trim().toLowerCase();
    if (!query) {
      return items;
    }
    return items.filter((item) =>
      `${getLabel(item)} ${getDescription?.(item) || ""}`.toLowerCase().includes(query)
    );
  }, [getDescription, getLabel, items, searchText]);

  return (
    <section className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white">{title}</h3>
        <span className="text-xs text-slate-400">{selected.length} selected</span>
      </div>

      <input
        type="search"
        value={searchText}
        onChange={(event) => onSearchTextChange(event.target.value)}
        placeholder={`Search ${title.toLowerCase()}...`}
        disabled={disabled}
        className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-500 focus:border-teal-400 focus:ring-2 focus:ring-teal-400/25 disabled:opacity-70"
      />

      <div className="max-h-44 space-y-2 overflow-y-auto rounded-lg border border-slate-800 bg-slate-950/50 p-3">
        {filteredItems.length === 0 ? (
          <p className="text-sm text-slate-400">{emptyLabel}</p>
        ) : (
          filteredItems.map((item) => {
            const id = getItemId(item);
            if (id === null || id === undefined) {
              return null;
            }

            const checked = selected.includes(String(id));

            return (
              <label
                key={String(id)}
                className="flex cursor-pointer items-start gap-2 rounded-md p-1.5 text-sm text-slate-200 transition hover:bg-slate-800/60"
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => onToggle(String(id))}
                  disabled={disabled || readOnly || Boolean(getDisabledReason?.(item))}
                  className="mt-0.5 h-4 w-4 rounded border-slate-600 bg-slate-900 text-teal-400 focus:ring-teal-400"
                />
                <span className="min-w-0 wrap-break-word">
                  <span className="block">{getLabel(item)}</span>
                  {getDescription?.(item) ? (
                    <span className="mt-0.5 block text-xs text-slate-400">{getDescription(item)}</span>
                  ) : null}
                  {getDisabledReason?.(item) ? (
                    <span className="mt-0.5 block text-xs text-amber-300">{getDisabledReason(item)}</span>
                  ) : null}
                </span>
              </label>
            );
          })
        )}
      </div>
    </section>
  );
}

export default function OptimizationForm({
  onOptimized,
  onError,
  onOptimizingChange,
  className = "",
}) {
  const [drivers, setDrivers] = useState([]);
  const [vehicles, setVehicles] = useState([]);
  const [orders, setOrders] = useState([]);

  const [driversQuery, setDriversQuery] = useState("");
  const [vehiclesQuery, setVehiclesQuery] = useState("");
  const [ordersQuery, setOrdersQuery] = useState("");

  const [selectedDriverIds, setSelectedDriverIds] = useState([]);
  const [selectedVehicleIds, setSelectedVehicleIds] = useState([]);
  const [selectedOrderIds, setSelectedOrderIds] = useState([]);

  const [loadingOptions, setLoadingOptions] = useState(true);
  const [optionsError, setOptionsError] = useState("");
  const [submitError, setSubmitError] = useState("");
  const [validationErrors, setValidationErrors] = useState({});
  const [optimizing, setOptimizing] = useState(false);
  const [forecastHorizonDays, setForecastHorizonDays] = useState(1);
  const [demandHistory, setDemandHistory] = useState([]);
  const [demandSourceStatus, setDemandSourceStatus] = useState("loading");
  const [readiness, setReadiness] = useState({ status: "loading" });

  const selectedVehicleCapacity = useMemo(
    () => vehicles
      .filter((vehicle) => selectedVehicleIds.includes(String(getItemId(vehicle))))
      .reduce((total, vehicle) => total + Number(vehicle?.capacity || 0), 0),
    [selectedVehicleIds, vehicles],
  );
  const readinessRequestKey = `${forecastHorizonDays}:${selectedVehicleCapacity}`;
  const currentReadiness = readiness.requestKey === readinessRequestKey
    ? readiness
    : { status: "loading" };
  const readinessView = buildForecastReadinessView(
    currentReadiness,
    demandHistory.length,
    demandSourceStatus,
  );

  useEffect(() => {
    let mounted = true;

    async function loadOptions() {
      setLoadingOptions(true);
      setOptionsError("");

      try {
        const [driversResponse, vehiclesResponse, ordersResponse] = await Promise.all([
          getDrivers({ skip: 0, limit: 1000 }),
          getVehicles({ skip: 0, limit: 1000 }),
          getOrders({ skip: 0, limit: 1000 }),
        ]);

        if (!mounted) {
          return;
        }

        setDrivers(normalizeListResponse(driversResponse));
        setVehicles(normalizeListResponse(vehiclesResponse));
        setOrders(normalizeListResponse(ordersResponse));
      } catch (error) {
        if (!mounted) {
          return;
        }
        setOptionsError(getApiErrorMessage(error, "Unable to load optimization resources."));
        setDrivers([]);
        setVehicles([]);
        setOrders([]);
      } finally {
        if (mounted) {
          setLoadingOptions(false);
        }
      }
    }

    loadOptions();

    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    let active = true;

    async function loadDemandHistory() {
      setDemandSourceStatus("loading");
      try {
        const research = await getResearchAnalytics();
        if (!active) {
          return;
        }
        const history = buildSyntheticDemandSeries(research).map((entry) => entry.demand);
        setDemandHistory(history);
        setDemandSourceStatus(history.length > 0 ? "available" : "empty");
      } catch {
        if (active) {
          setDemandHistory([]);
          setDemandSourceStatus("error");
        }
      }
    }

    loadDemandHistory();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (demandSourceStatus !== "available") {
      return undefined;
    }

    let active = true;

    async function loadReadiness() {
      try {
        const forecastPayload = {
          historical_demand_values: demandHistory,
          horizon_days: forecastHorizonDays,
        };
        if (forecastHorizonDays === 1 && selectedVehicleCapacity > 0) {
          const assessment = await assessForecastCapacity({
            ...forecastPayload,
            available_capacity: selectedVehicleCapacity,
          });
          if (active) {
            setReadiness({
              status: "success",
              requestKey: readinessRequestKey,
              ...assessment,
              source: "Repository synthetic series (not paper simulation)",
              model: "Exponential smoothing fallback",
            });
          }
          return;
        }

        const forecast = await forecastDemandForHorizon(forecastPayload);
        if (active) {
          setReadiness({
            status: "success",
            requestKey: readinessRequestKey,
            ...forecast,
            available_capacity: null,
            capacityUnavailable: forecastHorizonDays > 1,
            source: "Repository synthetic series (not paper simulation)",
            model: "Exponential smoothing fallback",
          });
        }
      } catch (requestError) {
        if (active) {
          setReadiness({
            status: "error",
            requestKey: readinessRequestKey,
            message: getApiErrorMessage(requestError, "Forecast assessment is unavailable."),
          });
        }
      }
    }

    loadReadiness();
    return () => {
      active = false;
    };
  }, [demandHistory, demandSourceStatus, forecastHorizonDays, readinessRequestKey, selectedVehicleCapacity]);

  function toggleSelected(setter, id) {
    setter((previous) => {
      if (previous.includes(id)) {
        return previous.filter((item) => item !== id);
      }
      return [...previous, id];
    });
  }

  function getDriverDisabledReason(driver) {
    const driverId = String(getItemId(driver));
    if (selectedDriverIds.includes(driverId)) {
      return null;
    }
    const issue = getDriverSelectionIssue(driver, vehicles);
    if (issue) {
      return issue;
    }
    const duplicatePair = drivers.some(
      (candidate) =>
        selectedDriverIds.includes(String(getItemId(candidate)))
        && String(candidate?.vehicle_id) === String(driver.vehicle_id),
    );
    return duplicatePair ? "Assigned vehicle is already paired with a selected driver." : null;
  }

  function toggleDriverSelection(driverId) {
    const driver = drivers.find((item) => String(getItemId(item)) === driverId);
    if (!driver) {
      return;
    }
    const vehicleId = driver.vehicle_id ? String(driver.vehicle_id) : null;
    if (selectedDriverIds.includes(driverId)) {
      setSelectedDriverIds((previous) => previous.filter((id) => id !== driverId));
      if (vehicleId) {
        setSelectedVehicleIds((previous) => previous.filter((id) => id !== vehicleId));
      }
      setValidationErrors((previous) => ({ ...previous, pairing: "" }));
      return;
    }

    const issue = getDriverDisabledReason(driver);
    if (issue) {
      setValidationErrors((previous) => ({ ...previous, pairing: issue }));
      return;
    }
    setSelectedDriverIds((previous) => [...previous, driverId]);
    setSelectedVehicleIds((previous) => [...new Set([...previous, vehicleId])]);
    setValidationErrors((previous) => ({ ...previous, pairing: "" }));
  }

  function getVehicleDescription(vehicle) {
    const assignedDriver = drivers.find(
      (driver) => String(driver?.vehicle_id) === String(getItemId(vehicle)),
    );
    const assignment = assignedDriver
      ? `Assigned to ${getDriverLabel(assignedDriver)}`
      : "No driver assigned";
    return `${getVehicleStatus(vehicle)} · ${assignment}`;
  }

  function validate() {
    const errors = {};

    if (selectedDriverIds.length === 0) {
      errors.drivers = "Select at least one driver.";
    }
    if (selectedVehicleIds.length === 0) {
      errors.vehicles = "Select at least one vehicle.";
    }
    if (selectedOrderIds.length === 0) {
      errors.orders = "Select at least one order.";
    }

    const selectedDrivers = drivers.filter((driver) =>
      selectedDriverIds.includes(String(getItemId(driver)))
    );
    const assignedVehicleIds = selectedDrivers.map((driver) =>
      driver?.vehicle_id ? String(driver.vehicle_id) : null
    );
    if (
      selectedDrivers.length > 0 &&
      (assignedVehicleIds.some((id) => id === null) ||
        assignedVehicleIds.length !== selectedVehicleIds.length ||
        assignedVehicleIds.some((id) => !selectedVehicleIds.includes(id)))
    ) {
      errors.pairing = "Select each driver's assigned vehicle, with one vehicle per driver.";
    }
    if (selectedDrivers.some((driver) => getDriverSelectionIssue(driver, vehicles))) {
      errors.pairing = "Selected drivers must be available and have an active, available assigned vehicle.";
    }
    if (new Set(assignedVehicleIds).size !== assignedVehicleIds.length) {
      errors.pairing = "A vehicle can only be paired with one selected driver.";
    }

    const selectedOrders = orders.filter((order) =>
      selectedOrderIds.includes(String(getItemId(order)))
    );
    if (selectedOrders.length !== selectedOrderIds.length || selectedOrders.some(getOrderSelectionIssue)) {
      errors.orders = "Remove unavailable orders or orders with invalid delivery coordinates.";
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitError("");

    if (!validate()) {
      return;
    }

    const payload = {
      driver_ids: selectedDriverIds,
      vehicle_ids: selectedVehicleIds,
      order_ids: selectedOrderIds,
    };

    setOptimizing(true);
    onOptimizingChange?.(true);

    try {
      const response = await optimizeRoutes(payload);
      onOptimized?.(response, payload);
    } catch (error) {
      const message = getApiErrorMessage(error, "Route optimization failed.");
      setSubmitError(message);
      onError?.(message, error);
    } finally {
      setOptimizing(false);
      onOptimizingChange?.(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className={`space-y-4 rounded-xl border border-slate-800 bg-slate-900/70 p-4 ${className}`}
    >
      <header>
        <h3 className="text-lg font-semibold text-white">Optimization Inputs</h3>
        <p className="mt-1 text-sm text-slate-300">
          Select available resources and orders for route optimization.
        </p>
      </header>

      <section className="space-y-3 rounded-lg border border-slate-700 bg-slate-950/70 p-3" aria-live="polite">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h4 className="text-sm font-semibold text-white">Forecast &amp; Fleet Readiness</h4>
            <p className="mt-1 text-xs text-slate-400">HGFCI advisory only; separate from the paper's HCCR reservation policy and never used as a routing constraint.</p>
          </div>
          <label className="flex items-center gap-2 text-xs text-slate-300">
            <span>Forecast horizon</span>
            <select
              value={forecastHorizonDays}
              onChange={(event) => setForecastHorizonDays(Number(event.target.value))}
              disabled={optimizing}
              className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1.5 text-sm text-white"
            >
              {[1, 7, 14].map((days) => (
                <option key={days} value={days}>{days} day{days === 1 ? "" : "s"}</option>
              ))}
            </select>
          </label>
        </div>

        {readinessView.state !== "success" ? (
          <p className={`text-sm ${readinessView.state === "loading" ? "text-slate-300" : "text-amber-200"}`}>
            {readinessView.message}
          </p>
        ) : null}
        {readinessView.state === "success" ? (
          <>
            <div className="grid gap-2 sm:grid-cols-2">
              <div>
                <p className="text-xs text-slate-400">
                  {readiness.horizon_days === 1
                    ? "One-day forecast demand"
                    : `Cumulative forecast workload over ${readiness.horizon_days} days`}
                </p>
                <p className="text-lg font-semibold text-white">{Number(readiness.predicted_demand).toFixed(2)} synthetic units</p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Model · provenance</p>
                <p className="text-sm text-slate-200">{readiness.model} · {readiness.source} ({demandHistory.length} daily observations)</p>
              </div>
            </div>
            {readiness.capacityUnavailable ? (
              <p className="rounded-md border border-amber-500/40 bg-amber-500/10 p-2 text-xs text-amber-100">
                {readinessView.capacityMessage}
              </p>
            ) : readiness.available_capacity !== null && readiness.available_capacity !== undefined ? (
              <>
                <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                  <ReadinessMetric label="Available capacity" value={`${readiness.available_capacity} vehicle units / dispatch cycle`} />
                  <ReadinessMetric label="Delta" value={`${readiness.capacity_delta?.toFixed(2)} synthetic units`} />
                  <ReadinessMetric label="Rho" value={readiness.rho === null ? "Undefined (zero capacity)" : readiness.rho?.toFixed(3)} />
                  <ReadinessMetric label="Nonnegative risk" value={`${readiness.capacity_risk?.toFixed(2)} synthetic units`} />
                </div>
                <p className={`text-xs ${readiness.preparation_recommended ? "text-amber-200" : "text-emerald-200"}`}>
                  {readiness.preparation_recommended
                    ? `Preparation recommendation: review ${readiness.recommended_additional_capacity.toFixed(2)} additional capacity units. Informational only; no vehicles are added to the solver.`
                    : "Preparation recommendation: no additional capacity indicated for this one-day scenario."}
                </p>
              </>
            ) : (
              <p className="text-xs text-amber-200">Select an available vehicle to compare one-day synthetic demand with fleet capacity.</p>
            )}
            <p className="text-xs text-amber-200">Synthetic demand units are not validated against operational vehicle-capacity units; treat this forecast comparison as illustrative, not operational advice.</p>
            <p className="text-xs text-amber-200">{readinessView.calibrationMessage}</p>
            {readinessView.historyMessage ? (
              <p className="text-xs text-amber-200">{readinessView.historyMessage}</p>
            ) : null}
          </>
        ) : null}
      </section>

      {loadingOptions ? (
        <div className="rounded-lg border border-slate-800 bg-slate-950/50 p-4">
          <div className="flex items-center gap-3 text-slate-300">
            <span className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-slate-700 border-t-teal-400" />
            <span className="text-sm">Loading drivers, vehicles, and orders...</span>
          </div>
        </div>
      ) : null}

      {optionsError ? (
        <p className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-sm text-rose-300">
          {optionsError}
        </p>
      ) : null}

      {!loadingOptions ? (
        <>
          <SelectionGroup
            title="Drivers"
            items={drivers}
            selected={selectedDriverIds}
            onToggle={toggleDriverSelection}
            disabled={optimizing}
            getLabel={getDriverLabel}
            getDescription={(driver) => {
              const assignedVehicle = vehicles.find(
                (vehicle) => String(vehicle.id) === String(driver?.vehicle_id),
              );
              return `${driver?.status || "Unknown status"} · ${driver?.is_available ? "Available" : "Unavailable"} · ${assignedVehicle ? `Assigned: ${getVehicleLabel(assignedVehicle)}` : "No assigned vehicle"}`;
            }}
            getDisabledReason={getDriverDisabledReason}
            emptyLabel="No drivers available."
            searchText={driversQuery}
            onSearchTextChange={setDriversQuery}
          />
          {validationErrors.drivers ? (
            <p className="-mt-2 text-sm text-rose-300">{validationErrors.drivers}</p>
          ) : null}

          <SelectionGroup
            title="Assigned Vehicles"
            items={vehicles}
            selected={selectedVehicleIds}
            onToggle={() => {}}
            disabled={optimizing}
            readOnly
            getLabel={getVehicleLabel}
            getDescription={getVehicleDescription}
            getDisabledReason={(vehicle) => {
              if (vehicle?.status !== "available" || vehicle?.is_active !== true) {
                return "Unavailable for optimization.";
              }
              return selectedVehicleIds.includes(String(getItemId(vehicle)))
                ? "Selected automatically with its assigned driver."
                : "Select the assigned driver to include this vehicle.";
            }}
            emptyLabel="No vehicles available."
            searchText={vehiclesQuery}
            onSearchTextChange={setVehiclesQuery}
          />
          {validationErrors.vehicles ? (
            <p className="-mt-2 text-sm text-rose-300">{validationErrors.vehicles}</p>
          ) : null}
          {validationErrors.pairing ? (
            <p className="-mt-2 text-sm text-rose-300">{validationErrors.pairing}</p>
          ) : null}

          <SelectionGroup
            title="Orders"
            items={orders}
            selected={selectedOrderIds}
            onToggle={(id) => toggleSelected(setSelectedOrderIds, id)}
            disabled={optimizing}
            getLabel={getOrderLabel}
            getDescription={getOrderDescription}
            getDisabledReason={getOrderSelectionIssue}
            emptyLabel="No orders available."
            searchText={ordersQuery}
            onSearchTextChange={setOrdersQuery}
          />
          {validationErrors.orders ? (
            <p className="-mt-2 text-sm text-rose-300">{validationErrors.orders}</p>
          ) : null}
        </>
      ) : null}

      {submitError ? (
        <p className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-sm text-rose-300">
          {submitError}
        </p>
      ) : null}

      <button
        type="submit"
        disabled={loadingOptions || optimizing}
        className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-teal-400 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-teal-300 disabled:cursor-not-allowed disabled:opacity-70"
      >
        {optimizing ? (
          <>
            <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-slate-800 border-t-transparent" />
            Optimizing...
          </>
        ) : (
          "Optimize Routes"
        )}
      </button>
    </form>
  );
}

function ReadinessMetric({ label, value }) {
  return (
    <div className="rounded-md border border-slate-800 bg-slate-900 p-2">
      <p className="text-[11px] text-slate-400">{label}</p>
      <p className="mt-1 wrap-break-word text-sm font-medium text-white">{value ?? "Unavailable"}</p>
    </div>
  );
}
