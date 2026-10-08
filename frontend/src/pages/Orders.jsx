import { useCallback, useEffect, useMemo, useState } from "react";
import DataTable from "../components/DataTable";
import DeleteDialog from "../components/DeleteDialog";
import FormModal from "../components/FormModal";
import {
  createOrder,
  deleteOrder,
  getOrder,
  getOrders,
  updateOrder,
} from "../services/orderService";

const ORDER_FIELDS = [
  { name: "customer_name", label: "Customer Name", required: true, placeholder: "North Hub Outlet", fullWidth: true },
  { name: "customer_phone", label: "Customer Phone", required: true, placeholder: "+1-555-0101", autoComplete: "tel" },
  { name: "pickup_address", label: "Pickup Address", required: true, fullWidth: true, placeholder: "Warehouse / pickup location" },
  { name: "delivery_address", label: "Delivery Address", required: true, fullWidth: true, placeholder: "Customer drop-off location" },
  { name: "pickup_latitude", label: "Pickup Latitude", type: "number", required: true, step: "any", placeholder: "22.5726" },
  { name: "pickup_longitude", label: "Pickup Longitude", type: "number", required: true, step: "any", placeholder: "88.3639" },
  { name: "delivery_latitude", label: "Delivery Latitude", type: "number", required: true, step: "any", placeholder: "22.5900" },
  { name: "delivery_longitude", label: "Delivery Longitude", type: "number", required: true, step: "any", placeholder: "88.4100" },
  { name: "demand", label: "Demand", type: "number", required: true, min: 1, step: 1 },
  { name: "priority", label: "Priority", type: "number", required: true, min: 1, step: 1 },
  {
    name: "status",
    label: "Status",
    type: "select",
    options: [
      { label: "Pending", value: "pending" },
      { label: "Assigned", value: "assigned" },
      { label: "In Transit", value: "in_transit" },
      { label: "Delivered", value: "delivered" },
      { label: "Cancelled", value: "cancelled" },
    ],
  },
  { name: "assigned_driver_id", label: "Assigned Driver ID", placeholder: "Optional" },
  { name: "assigned_vehicle_id", label: "Assigned Vehicle ID", placeholder: "Optional" },
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

  [
    "pickup_latitude",
    "pickup_longitude",
    "delivery_latitude",
    "delivery_longitude",
    "demand",
    "priority",
  ].forEach((key) => {
    if (payload[key] !== undefined) {
      payload[key] = Number(payload[key]);
    }
  });

  if (mode === "create") {
    return {
      customer_name: payload.customer_name,
      customer_phone: payload.customer_phone,
      pickup_address: payload.pickup_address,
      delivery_address: payload.delivery_address,
      pickup_latitude: payload.pickup_latitude,
      pickup_longitude: payload.pickup_longitude,
      delivery_latitude: payload.delivery_latitude,
      delivery_longitude: payload.delivery_longitude,
      demand: payload.demand,
      priority: payload.priority,
    };
  }

  return {
    customer_name: payload.customer_name,
    customer_phone: payload.customer_phone,
    pickup_address: payload.pickup_address,
    delivery_address: payload.delivery_address,
    pickup_latitude: payload.pickup_latitude,
    pickup_longitude: payload.pickup_longitude,
    delivery_latitude: payload.delivery_latitude,
    delivery_longitude: payload.delivery_longitude,
    demand: payload.demand,
    priority: payload.priority,
    status: payload.status,
    assigned_driver_id: payload.assigned_driver_id,
    assigned_vehicle_id: payload.assigned_vehicle_id,
  };
}

export default function Orders() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState("create");
  const [activeOrder, setActiveOrder] = useState(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");

  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [orderToDelete, setOrderToDelete] = useState(null);

  const fetchOrders = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await getOrders({ skip: 0, limit: 1000 });
      setOrders(normalizeListResponse(response));
    } catch (err) {
      setError(getErrorMessage(err, "Failed to load orders."));
      setOrders([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  const columns = useMemo(
    () => [
      {
        key: "customer_name",
        header: "Customer",
        accessor: (row) => row.customer_name || "-",
      },
      {
        key: "pickup_address",
        header: "Pickup",
        accessor: (row) => row.pickup_address || "-",
      },
      {
        key: "delivery_address",
        header: "Dropoff",
        accessor: (row) => row.delivery_address || "-",
      },
      {
        key: "demand",
        header: "Qty",
        accessor: (row) => row.demand ?? "-",
        align: "right",
      },
      {
        key: "priority",
        header: "Priority",
        accessor: (row) => row.priority || "-",
        render: (value) => (
          <span className="inline-flex rounded-full border border-slate-700 px-2 py-0.5 text-xs capitalize text-slate-200">
            {value || "unknown"}
          </span>
        ),
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
    ],
    []
  );

  function handleCreateClick() {
    setModalMode("create");
    setActiveOrder(null);
    setFormError("");
    setSuccessMessage("");
    setModalOpen(true);
  }

  async function handleEditClick(order) {
    setModalMode("edit");
    setFormError("");
    setSuccessMessage("");
    setSaving(true);
    setModalOpen(true);

    try {
      const fresh = await getOrder(order.id);
      setActiveOrder(fresh);
    } catch (err) {
      setFormError(getErrorMessage(err, "Failed to load order details."));
      setActiveOrder(order);
    } finally {
      setSaving(false);
    }
  }

  function handleDeleteClick(order) {
    setOrderToDelete(order);
    setDeleteOpen(true);
  }

  async function handleSubmit(values) {
    setSaving(true);
    setFormError("");

    try {
      const payload = toPayload(values, modalMode);
      if (modalMode === "create") {
        await createOrder(payload);
        setSuccessMessage("Order created successfully.");
      } else if (activeOrder?.id) {
        await updateOrder(activeOrder.id, payload);
        setSuccessMessage("Order updated successfully.");
      }

      setModalOpen(false);
      setActiveOrder(null);
      await fetchOrders();
    } catch (err) {
      setFormError(getErrorMessage(err, "Unable to save order."));
    } finally {
      setSaving(false);
    }
  }

  async function handleConfirmDelete() {
    if (!orderToDelete?.id) {
      return;
    }

    setDeleting(true);
    setError("");
    try {
      await deleteOrder(orderToDelete.id);
      setSuccessMessage("Order deleted successfully.");
      setDeleteOpen(false);
      setOrderToDelete(null);
      await fetchOrders();
    } catch (err) {
      setError(getErrorMessage(err, "Unable to delete order."));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <section className="space-y-5">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Orders</h2>
          <p className="mt-1 text-sm text-slate-300">
            Manage pickup and dropoff orders with assignment-ready details.
          </p>
        </div>

        <button
          type="button"
          onClick={handleCreateClick}
          className="rounded-lg bg-teal-400 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-teal-300"
        >
          Add Order
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
        data={orders}
        columns={columns}
        loading={loading}
        searchable
        searchPlaceholder="Search orders by customer, address, status, or priority..."
        emptyMessage="No orders found. Create an order to begin fulfillment operations."
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
        title={modalMode === "create" ? "Add Order" : "Edit Order"}
        fields={ORDER_FIELDS}
        initialValues={activeOrder || {}}
        loading={saving}
        errorMessage={formError}
        onCancel={() => {
          if (!saving) {
            setModalOpen(false);
            setActiveOrder(null);
          }
        }}
        onSubmit={handleSubmit}
      />

      <DeleteDialog
        isOpen={deleteOpen}
        title="Delete Order"
        message={`Are you sure you want to delete order ${orderToDelete?.id || "record"}? This action cannot be undone.`}
        loading={deleting}
        onCancel={() => {
          if (!deleting) {
            setDeleteOpen(false);
            setOrderToDelete(null);
          }
        }}
        onConfirm={handleConfirmDelete}
      />
    </section>
  );
}
