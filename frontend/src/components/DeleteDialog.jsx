export default function DeleteDialog({
  isOpen,
  title = "Delete Record",
  message = "Are you sure you want to delete this record? This action cannot be undone.",
  confirmLabel = "Delete",
  loading = false,
  onCancel,
  onConfirm,
}) {
  function handleBackdropKeyDown(event) {
    if (event.key === "Escape" && !loading) {
      onCancel?.();
    }
  }

  if (!isOpen) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-3 backdrop-blur-sm sm:p-4"
      onKeyDown={handleBackdropKeyDown}
    >
      <div
        className="flex max-h-[88vh] w-full max-w-md flex-col overflow-hidden rounded-xl border border-slate-700 bg-slate-900 shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <div className="shrink-0 border-b border-slate-800 px-4 py-3 sm:px-5 sm:py-4">
          <h3 className="text-lg font-semibold text-white">{title}</h3>
        </div>

        <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-4 py-4 sm:px-5">
          <p className="text-sm text-slate-300">{message}</p>
        </div>

        <div className="flex shrink-0 items-center justify-end gap-2 border-t border-slate-800 bg-slate-900 px-4 py-3 sm:px-5 sm:py-4">
          <button
            type="button"
            onClick={onCancel}
            disabled={loading}
            className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-medium text-slate-200 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={loading}
            className="rounded-lg bg-rose-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-rose-400 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? "Deleting..." : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
