import { useCallback, useEffect, useMemo, useState } from "react";
import DataTable from "../components/DataTable";
import DeleteDialog from "../components/DeleteDialog";
import FormModal from "../components/FormModal";
import {
  createVehicle,
  deleteVehicle,
  getVehicle,
  getVehicles,
  updateVehicle,
} from "../services/vehicleService";

const VEHICLE_FIELDS = [
  { name: "plate_number", label: "Plate Number", required: true, placeholder: "WB-02-AB-1122" },
  { name: "model", label: "Model", required: true, placeholder: "Tata Ace" },
  { name: "capacity", label: "Capacity", type: "number", required: true, min: 1, step: 1 },
  {
    name: "status",
    label: "Status",
    type: "select",
    required: true,
    options: [
      { label: "Available", value: "available" },
      { label: "In Transit", value: "in_transit" },
      { label: "Maintenance", value: "maintenance" },
    ],
  },
  { name: "is_active", label: "Active", type: "checkbox" },
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

  if (payload.capacity !== undefined) {
    payload.capacity = Number(payload.capacity);
  }
  payload.is_active = Boolean(values.is_active);

  return payload;
}

export default function Vehicles() {
  const [vehicles, setVehicles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState("create");
  const [activeVehicle, setActiveVehicle] = useState(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [vehicleToDelete, setVehicleToDelete] = useState(null);

  const fetchVehicles = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await getVehicles({ skip: 0, limit: 1000 });
      setVehicles(normalizeListResponse(response));
    } catch (err) {
      setError(getErrorMessage(err, "Failed to load vehicles."));
      setVehicles([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchVehicles();
  }, [fetchVehicles]);

  const columns = useMemo(
    () => [
      {
        key: "plate_number",
        header: "Plate",
        accessor: (row) => row.plate_number || row.plate || "-",
      },
      {
        key: "model",
        header: "Model",
        accessor: (row) => row.model || "-",
      },
      {
        key: "capacity",
        header: "Capacity",
        accessor: (row) => row.capacity ?? "-",
        align: "right",
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
        key: "is_active",
        header: "Active",
        accessor: (row) => (row.is_active ? "Yes" : "No"),
        searchable: false,
      },
    ],
    []
  );

  function handleCreateClick() {
    setModalMode("create");
    setActiveVehicle(null);
    setFormError("");
    setModalOpen(true);
  }

  async function handleEditClick(vehicle) {
    setModalMode("edit");
    setFormError("");
    setSaving(true);
    setModalOpen(true);

    try {
      const fresh = await getVehicle(vehicle.id);
      setActiveVehicle(fresh);
    } catch (err) {
      setFormError(getErrorMessage(err, "Failed to load vehicle details."));
      setActiveVehicle(vehicle);
    } finally {
      setSaving(false);
    }
  }

  function handleDeleteClick(vehicle) {
    setVehicleToDelete(vehicle);
    setDeleteOpen(true);
  }

  async function handleSubmit(values) {
    setSaving(true);
    setFormError("");

    try {
      const payload = toPayload(values);
      if (modalMode === "create") {
        await createVehicle(payload);
      } else if (activeVehicle?.id) {
        await updateVehicle(activeVehicle.id, payload);
      }

      setModalOpen(false);
      setActiveVehicle(null);
      await fetchVehicles();
    } catch (err) {
      setFormError(getErrorMessage(err, "Unable to save vehicle."));
    } finally {
      setSaving(false);
    }
  }

  async function handleConfirmDelete() {
    if (!vehicleToDelete?.id) {
      return;
    }

    setDeleting(true);
    setError("");
    try {
      await deleteVehicle(vehicleToDelete.id);
      setDeleteOpen(false);
      setVehicleToDelete(null);
      await fetchVehicles();
    } catch (err) {
      setError(getErrorMessage(err, "Unable to delete vehicle."));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <section className="space-y-5">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Vehicles</h2>
          <p className="mt-1 text-sm text-slate-300">
            Maintain vehicle inventory, capacity, and operational status.
          </p>
        </div>

        <button
          type="button"
          onClick={handleCreateClick}
          className="rounded-lg bg-teal-400 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-teal-300"
        >
          Add Vehicle
        </button>
      </header>

      {error ? (
        <p className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-sm text-rose-300">
          {error}
        </p>
      ) : null}

      <DataTable
        data={vehicles}
        columns={columns}
        loading={loading}
        searchable
        searchPlaceholder="Search vehicles by plate, model, or status..."
        emptyMessage="No vehicles found. Add your first vehicle to build fleet capacity."
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
        title={modalMode === "create" ? "Add Vehicle" : "Edit Vehicle"}
        fields={VEHICLE_FIELDS}
        initialValues={activeVehicle || {}}
        loading={saving}
        errorMessage={formError}
        onCancel={() => {
          if (!saving) {
            setModalOpen(false);
            setActiveVehicle(null);
          }
        }}
        onSubmit={handleSubmit}
      />

      <DeleteDialog
        isOpen={deleteOpen}
        title="Delete Vehicle"
        message={`Are you sure you want to delete vehicle ${vehicleToDelete?.plate_number || vehicleToDelete?.plate || "record"}? This action cannot be undone.`}
        loading={deleting}
        onCancel={() => {
          if (!deleting) {
            setDeleteOpen(false);
            setVehicleToDelete(null);
          }
        }}
        onConfirm={handleConfirmDelete}
      />
    </section>
  );
}
