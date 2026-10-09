import { useEffect, useMemo, useState } from "react";
import { getDrivers } from "../services/driverService";
import { getOrders } from "../services/orderService";
import { getApiErrorMessage, optimizeRoutes } from "../services/optimizationService";
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
