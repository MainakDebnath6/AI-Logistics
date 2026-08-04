import { useCallback, useEffect, useMemo, useState } from "react";
import DataTable from "../components/DataTable";
import DeleteDialog from "../components/DeleteDialog";
import FormModal from "../components/FormModal";
import {
  createDriver,
  deleteDriver,
  getDriver,
  getDrivers,
  updateDriver,
} from "../services/driverService";

const DRIVER_FIELDS = [
  { name: "full_name", label: "Full Name", required: true, placeholder: "Alex Carter" },
  { name: "email", label: "Email", type: "email", required: true, placeholder: "alex@fleet.com" },
  { name: "phone_number", label: "Phone Number", required: true, placeholder: "+1-555-0101" },
  { name: "license_number", label: "License Number", required: true, placeholder: "DL-2026-1142" },
  {
    name: "status",
    label: "Status",
    type: "select",
    required: true,
    options: [
      { label: "Active", value: "active" },
      { label: "Inactive", value: "inactive" },
      { label: "On Leave", value: "on_leave" },
    ],
  },
  { name: "is_available", label: "Available for Dispatch", type: "checkbox" },
];

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

function toPayload(values) {
  const payload = { ...values };

  Object.keys(payload).forEach((key) => {
    if (typeof payload[key] === "string") {
      payload[key] = payload[key].trim();
      if (payload[key] === "") {
        delete payload[key];
      }
    }
  });

  payload.is_available = Boolean(values.is_available);
  return payload;
}

export default function Drivers() {
  const [drivers, setDrivers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState("create");
  const [activeDriver, setActiveDriver] = useState(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [driverToDelete, setDriverToDelete] = useState(null);

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

  useEffect(() => {
    fetchDrivers();
  }, [fetchDrivers]);

  const columns = useMemo(
    () => [
      {
        key: "full_name",
        header: "Name",
        accessor: (row) => row.full_name || row.name || "-",
      },
      {
        key: "email",
        header: "Email",
        accessor: (row) => row.email || "-",
      },
      {
        key: "phone_number",
        header: "Phone",
        accessor: (row) => row.phone_number || row.phone || "-",
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
    setModalOpen(true);
  }

  async function handleEditClick(driver) {
    setModalMode("edit");
    setFormError("");
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
      const payload = toPayload(values);
      if (modalMode === "create") {
        await createDriver(payload);
      } else if (activeDriver?.id) {
        await updateDriver(activeDriver.id, payload);
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

      <DataTable
        data={drivers}
        columns={columns}
        loading={loading}
        searchable
        searchPlaceholder="Search drivers by name, email, phone, or license..."
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
        fields={DRIVER_FIELDS}
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
        message={`Are you sure you want to delete ${driverToDelete?.full_name || driverToDelete?.name || "this driver"}? This action cannot be undone.`}
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
