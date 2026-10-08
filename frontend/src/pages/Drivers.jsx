import { useCallback, useEffect, useMemo, useState } from "react";
import DataTable from "../components/DataTable";
import DeleteDialog from "../components/DeleteDialog";
import FormModal from "../components/FormModal";
import api from "../services/api";
import { getVehicles } from "../services/vehicleService";
import {
  createDriver,
  deleteDriver,
  getDriver,
  getDrivers,
  updateDriver,
} from "../services/driverService";

function getCreateFields(userOptions, vehicleOptions, optionsLoading) {
  return [
    {
      name: "user_id",
      label: "Driver User",
      type: "searchable-select",
      required: true,
      options: userOptions,
      disabled: optionsLoading,
      searchPlaceholder: "Search users by name or email...",
    },
    {
      name: "vehicle_id",
      label: "Assigned Vehicle",
      type: "searchable-select",
      options: vehicleOptions,
      disabled: optionsLoading,
      searchPlaceholder: "Search vehicles by registration or model...",
    },
    {
      name: "phone",
      label: "Phone",
      required: true,
      placeholder: "+1-555-0101",
      autoComplete: "tel",
    },
    {
      name: "license_number",
      label: "License Number",
      required: true,
      placeholder: "DL-2026-1142",
      autoComplete: "off",
    },
    {
      name: "max_capacity",
      label: "Max Capacity",
      type: "number",
      required: true,
      min: 1,
      step: 1,
      inputMode: "numeric",
      validate: (raw) => {
        const parsed = Number(raw);
        if (!Number.isInteger(parsed) || parsed <= 0) {
          return "Max Capacity must be a positive integer.";
        }
        return "";
      },
    },
  ];
}

function getEditFields(vehicleOptions, optionsLoading) {
  return [
    { name: "phone", label: "Phone", required: true, placeholder: "+1-555-0101", autoComplete: "tel" },
    { name: "license_number", label: "License Number", required: true, placeholder: "DL-2026-1142" },
    {
      name: "vehicle_id",
      label: "Assigned Vehicle",
      type: "searchable-select",
      options: vehicleOptions,
      disabled: optionsLoading,
      searchPlaceholder: "Search vehicles by registration or model...",
    },
    {
      name: "status",
      label: "Status",
      type: "select",
      options: [
        { label: "Available", value: "available" },
        { label: "Busy", value: "busy" },
        { label: "Offline", value: "offline" },
      ],
    },
    { name: "max_capacity", label: "Max Capacity", type: "number", required: true, min: 1, step: 1 },
    { name: "is_available", label: "Available for Dispatch", type: "checkbox" },
  ];
}

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

function getErrorMessage(error, fallback) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail.map((item) => item?.msg || "Validation error").join("; ");
  }
  return fallback;
}

function toPayload(values, mode) {
  const payload = { ...values };

  Object.keys(payload).forEach((key) => {
    if (typeof payload[key] === "string") {
      payload[key] = payload[key].trim();
      if (payload[key] === "") {
        delete payload[key];
      }
    }
  });

  if (payload.max_capacity !== undefined) {
    payload.max_capacity = Number(payload.max_capacity);
  }
  payload.is_available = Boolean(values.is_available);

  if (mode === "create") {
    const vehicleId = payload.vehicle_id ?? null;

    return {
      user_id: payload.user_id,
      license_number: payload.license_number,
      phone: payload.phone,
      vehicle_id: vehicleId,
      max_capacity: payload.max_capacity,
    };
  }

  return {
    license_number: payload.license_number,
    phone: payload.phone,
    vehicle_id: payload.vehicle_id,
    status: payload.status,
    max_capacity: payload.max_capacity,
    is_available: payload.is_available,
  };
}

export default function Drivers() {
  const [drivers, setDrivers] = useState([]);
  const [users, setUsers] = useState([]);
  const [vehicles, setVehicles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [optionsLoading, setOptionsLoading] = useState(true);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState("create");
  const [activeDriver, setActiveDriver] = useState(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [driverToDelete, setDriverToDelete] = useState(null);

  const userOptions = useMemo(
    () =>
      users
        .filter((user) => user?.id)
        .map((user) => ({
          value: user.id,
          label: `${user.full_name || "Unknown User"} (${user.email || "no-email"})`,
        })),
    [users]
  );

  const vehicleOptions = useMemo(
    () =>
      vehicles
        .filter((vehicle) => vehicle?.id)
        .map((vehicle) => ({
          value: vehicle.id,
          label: `${vehicle.registration_number || "Unknown"} - ${vehicle.model || "Vehicle"}`,
        })),
    [vehicles]
  );

  const driverFormFields = useMemo(() => {
    if (modalMode === "create") {
      return getCreateFields(userOptions, vehicleOptions, optionsLoading);
    }
    return getEditFields(vehicleOptions, optionsLoading);
  }, [modalMode, optionsLoading, userOptions, vehicleOptions]);

  const fetchDrivers = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await getDrivers({ skip: 0, limit: 1000 });
      setDrivers(normalizeListResponse(response));
    } catch (err) {
      setError(getErrorMessage(err, "Failed to load drivers."));
      setDrivers([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchFormOptions = useCallback(async () => {
    setOptionsLoading(true);
    try {
      const [usersResponse, vehiclesResponse] = await Promise.all([
        api.get("/users"),
        getVehicles({ skip: 0, limit: 1000 }),
      ]);

      setUsers(normalizeListResponse(usersResponse?.data));
      setVehicles(normalizeListResponse(vehiclesResponse));
    } catch {
      setUsers([]);
      setVehicles([]);
    } finally {
      setOptionsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDrivers();
  }, [fetchDrivers]);

  useEffect(() => {
    fetchFormOptions();
  }, [fetchFormOptions]);

  const columns = useMemo(
    () => [
      {
        key: "user_id",
        header: "User ID",
        accessor: (row) => row.user_id || "-",
      },
      {
        key: "phone",
        header: "Phone",
        accessor: (row) => row.phone || "-",
      },
      {
        key: "license_number",
        header: "License",
        accessor: (row) => row.license_number || "-",
      },
      {
        key: "status",
        header: "Status",
        accessor: (row) => row.status || "-",
        render: (value) => (
          <span className="inline-flex rounded-full border border-slate-700 px-2 py-0.5 text-xs capitalize text-slate-200">
            {value || "unknown"}
          </span>
        ),
      },
      {
        key: "is_available",
        header: "Availability",
        accessor: (row) => (row.is_available ? "Available" : "Unavailable"),
        searchable: false,
      },
    ],
    []
  );

  function handleCreateClick() {
    setModalMode("create");
    setActiveDriver(null);
    setFormError("");
    setSuccessMessage("");
    setModalOpen(true);
  }

  async function handleEditClick(driver) {
    setModalMode("edit");
    setFormError("");
    setSuccessMessage("");
    setSaving(true);
    setModalOpen(true);

    try {
      const fresh = await getDriver(driver.id);
      setActiveDriver(fresh);
    } catch (err) {
      setFormError(getErrorMessage(err, "Failed to load driver details."));
      setActiveDriver(driver);
    } finally {
      setSaving(false);
    }
  }

  function handleDeleteClick(driver) {
    setDriverToDelete(driver);
    setDeleteOpen(true);
  }

  async function handleSubmit(values) {
    setSaving(true);
    setFormError("");

    try {
      const payload = toPayload(values, modalMode);
      if (modalMode === "create") {
        await createDriver(payload);
        setSuccessMessage("Driver created successfully.");
      } else if (activeDriver?.id) {
        await updateDriver(activeDriver.id, payload);
        setSuccessMessage("Driver updated successfully.");
      }

      setModalOpen(false);
      setActiveDriver(null);
      await fetchDrivers();
    } catch (err) {
      setFormError(getErrorMessage(err, "Unable to save driver."));
    } finally {
      setSaving(false);
    }
  }

  async function handleConfirmDelete() {
    if (!driverToDelete?.id) {
      return;
    }

    setDeleting(true);
    setError("");
    try {
      await deleteDriver(driverToDelete.id);
      setSuccessMessage("Driver deleted successfully.");
      setDeleteOpen(false);
      setDriverToDelete(null);
      await fetchDrivers();
    } catch (err) {
      setError(getErrorMessage(err, "Unable to delete driver."));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <section className="space-y-5">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Drivers</h2>
          <p className="mt-1 text-sm text-slate-300">
            Manage driver profiles, availability, and dispatch readiness.
          </p>
        </div>

        <button
          type="button"
          onClick={handleCreateClick}
          className="rounded-lg bg-teal-400 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-teal-300"
        >
          Add Driver
        </button>
      </header>

      {error ? (
        <p className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-sm text-rose-300">
          {error}
        </p>
      ) : null}

      {successMessage ? (
        <p className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-300">
          {successMessage}
        </p>
      ) : null}

      <DataTable
        data={drivers}
        columns={columns}
        loading={loading}
        searchable
        searchPlaceholder="Search drivers by user ID, phone, or license..."
        emptyMessage="No drivers found. Create your first driver to start dispatching."
        rowKey="id"
        actions={(row) => (
          <>
            <button
              type="button"
              onClick={() => handleEditClick(row)}
              className="rounded-md border border-slate-700 px-2.5 py-1 text-xs text-slate-200 transition hover:bg-slate-800"
            >
              Edit
            </button>
            <button
              type="button"
              onClick={() => handleDeleteClick(row)}
              className="rounded-md border border-rose-500/40 px-2.5 py-1 text-xs text-rose-300 transition hover:bg-rose-500/15"
            >
              Delete
            </button>
          </>
        )}
      />

      <FormModal
        isOpen={modalOpen}
        mode={modalMode}
        title={modalMode === "create" ? "Add Driver" : "Edit Driver"}
        fields={driverFormFields}
        initialValues={activeDriver || {}}
        loading={saving}
        errorMessage={formError}
        onCancel={() => {
          if (!saving) {
            setModalOpen(false);
            setActiveDriver(null);
          }
        }}
        onSubmit={handleSubmit}
      />

      <DeleteDialog
        isOpen={deleteOpen}
        title="Delete Driver"
        message={`Are you sure you want to delete driver ${driverToDelete?.id || "record"}? This action cannot be undone.`}
        loading={deleting}
        onCancel={() => {
          if (!deleting) {
            setDeleteOpen(false);
            setDriverToDelete(null);
          }
        }}
        onConfirm={handleConfirmDelete}
      />
    </section>
  );
}
