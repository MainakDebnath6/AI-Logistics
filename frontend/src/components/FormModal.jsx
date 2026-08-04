import { useEffect, useMemo, useState } from "react";

function buildInitialState(fields, initialValues) {
  const state = {};

  fields.forEach((field) => {
    const value = initialValues?.[field.name];
    if (value === null || value === undefined) {
      if (field.type === "checkbox") {
        state[field.name] = false;
      } else {
        state[field.name] = "";
      }
      return;
    }

    state[field.name] = field.type === "checkbox" ? Boolean(value) : String(value);
  });

  return state;
}

function validateValues(fields, values) {
  const errors = {};

  fields.forEach((field) => {
    const rawValue = values[field.name];

    if (field.required) {
      if (field.type === "checkbox") {
        if (!rawValue) {
          errors[field.name] = `${field.label} is required.`;
        }
      } else if (String(rawValue ?? "").trim() === "") {
        errors[field.name] = `${field.label} is required.`;
      }
    }

    if (!errors[field.name] && typeof field.validate === "function") {
      const result = field.validate(rawValue, values);
      if (typeof result === "string" && result.trim()) {
        errors[field.name] = result;
      }
    }
  });

  return errors;
}

export default function FormModal({
  isOpen,
  mode = "create",
  title,
  fields = [],
  initialValues = {},
  submitLabel,
  loading = false,
  errorMessage = "",
  onCancel,
  onSubmit,
}) {
  const [values, setValues] = useState(() => buildInitialState(fields, initialValues));
  const [errors, setErrors] = useState({});

  const resolvedTitle =
    title || (mode === "edit" ? "Edit Record" : "Create Record");

  const resolvedSubmitLabel =
    submitLabel || (mode === "edit" ? "Save Changes" : "Create");

  const hasFields = fields.length > 0;

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    setValues(buildInitialState(fields, initialValues));
    setErrors({});
  }, [isOpen, fields, initialValues]);

  const formFields = useMemo(() => fields, [fields]);

  if (!isOpen) {
    return null;
  }

  function handleChange(event) {
    const { name, value, type, checked } = event.target;
    setValues((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));

    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: undefined }));
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const nextErrors = validateValues(formFields, values);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    await onSubmit(values);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-4 backdrop-blur-sm">
      <div className="w-full max-w-2xl rounded-xl border border-slate-700 bg-slate-900 shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
          <h3 className="text-lg font-semibold text-white">{resolvedTitle}</h3>
          <button
            type="button"
            onClick={onCancel}
            className="rounded-md p-1 text-slate-300 transition hover:bg-slate-800 hover:text-white"
            aria-label="Close modal"
            disabled={loading}
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5 p-5">
          {errorMessage ? (
            <p className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-sm text-rose-300">
              {errorMessage}
            </p>
          ) : null}

          {hasFields ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {formFields.map((field) => {
                const value = values[field.name];
                const error = errors[field.name];
                const sharedClass =
                  "w-full rounded-lg border bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-500 focus:ring-2";
                const inputClass = error
                  ? `${sharedClass} border-rose-500/60 focus:border-rose-400 focus:ring-rose-400/20`
                  : `${sharedClass} border-slate-700 focus:border-teal-400 focus:ring-teal-400/20`;

                if (field.type === "checkbox") {
                  return (
                    <label
                      key={field.name}
                      className="flex items-center gap-3 rounded-lg border border-slate-800 bg-slate-950/40 px-3 py-2"
                    >
                      <input
                        type="checkbox"
                        name={field.name}
                        checked={Boolean(value)}
                        onChange={handleChange}
                        disabled={loading}
                        className="h-4 w-4 rounded border-slate-600 bg-slate-900 text-teal-400 focus:ring-teal-400"
                      />
                      <span className="text-sm text-slate-200">{field.label}</span>
                    </label>
                  );
                }

                return (
                  <div
                    key={field.name}
                    className={field.fullWidth ? "sm:col-span-2" : undefined}
                  >
                    <label
                      htmlFor={field.name}
                      className="mb-1 block text-sm font-medium text-slate-200"
                    >
                      {field.label}
                    </label>

                    {field.type === "select" ? (
                      <select
                        id={field.name}
                        name={field.name}
                        value={value}
                        onChange={handleChange}
                        disabled={loading}
                        className={inputClass}
                      >
                        <option value="">Select {field.label}</option>
                        {(field.options || []).map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        id={field.name}
                        name={field.name}
                        type={field.type || "text"}
                        value={value}
                        onChange={handleChange}
                        disabled={loading}
                        placeholder={field.placeholder || ""}
                        min={field.min}
                        max={field.max}
                        step={field.step}
                        className={inputClass}
                      />
                    )}

                    {error ? (
                      <p className="mt-1 text-xs text-rose-300">{error}</p>
                    ) : null}
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-300">
              No form fields configured for this action.
            </p>
          )}

          <div className="flex items-center justify-end gap-2 border-t border-slate-800 pt-4">
            <button
              type="button"
              onClick={onCancel}
              disabled={loading}
              className="rounded-lg border border-slate-700 px-4 py-2 text-sm font-medium text-slate-200 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !hasFields}
              className="rounded-lg bg-teal-400 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-teal-300 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? "Saving..." : resolvedSubmitLabel}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
