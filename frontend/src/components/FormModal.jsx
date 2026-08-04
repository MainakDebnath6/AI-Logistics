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
  const [searchQueries, setSearchQueries] = useState({});

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
    setSearchQueries({});
  }, [isOpen, fields, initialValues]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    function handleKeyDown(event) {
      if (event.key === "Escape" && !loading) {
        onCancel?.();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, loading, onCancel]);

  const formFields = useMemo(() => fields, [fields]);

  if (!isOpen) {
    return null;
  }

  function getSelectedOption(field) {
    if (!Array.isArray(field.options)) {
      return null;
    }
    return field.options.find((option) => String(option.value) === String(values[field.name])) || null;
  }

  function getFilteredOptions(field) {
    if (!Array.isArray(field.options)) {
      return [];
    }

    const query = (searchQueries[field.name] || "").trim().toLowerCase();
    if (!query) {
      return field.options;
    }

    return field.options.filter((option) => {
      const label = String(option.label || "").toLowerCase();
      const value = String(option.value || "").toLowerCase();
      return label.includes(query) || value.includes(query);
    });
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-3 backdrop-blur-sm sm:p-4">
      <div
        className="flex max-h-[92vh] w-full max-w-3xl flex-col overflow-hidden rounded-xl border border-slate-700 bg-slate-900 shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-label={resolvedTitle}
      >
        <div className="flex shrink-0 items-center justify-between border-b border-slate-800 px-4 py-3 sm:px-5 sm:py-4">
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

        <form onSubmit={handleSubmit} className="flex min-h-0 flex-1 flex-col">
          <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4 sm:px-5">
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
                    <label htmlFor={field.name} className="mb-1 block text-sm font-medium text-slate-200">
                      {field.label}
                      {field.required ? <span className="ml-1 text-rose-300" aria-hidden="true">*</span> : null}
                    </label>

                    {field.type === "searchable-select" ? (
                      <div className="space-y-2">
                        <input
                          type="search"
                          value={searchQueries[field.name] || ""}
                          onChange={(event) =>
                            setSearchQueries((previous) => ({
                              ...previous,
                              [field.name]: event.target.value,
                            }))
                          }
                          disabled={loading || field.disabled}
                          placeholder={field.searchPlaceholder || `Search ${field.label.toLowerCase()}...`}
                          className={inputClass}
                          aria-label={`Search ${field.label}`}
                        />

                        <div className="max-h-40 overflow-y-auto rounded-lg border border-slate-700 bg-slate-950/60 p-1.5">
                          {getFilteredOptions(field).length === 0 ? (
                            <p className="px-2 py-1.5 text-xs text-slate-400">No matches found.</p>
                          ) : (
                            getFilteredOptions(field).map((option) => {
                              const selected = String(option.value) === String(value);

                              return (
                                <button
                                  key={option.value}
                                  type="button"
                                  onClick={() => {
                                    setValues((previous) => ({
                                      ...previous,
                                      [field.name]: String(option.value),
                                    }));
                                    if (errors[field.name]) {
                                      setErrors((previous) => ({ ...previous, [field.name]: undefined }));
                                    }
                                  }}
                                  disabled={loading || field.disabled}
                                  className={`flex w-full items-start rounded-md px-2 py-1.5 text-left text-sm transition ${
                                    selected
                                      ? "bg-teal-500/20 text-teal-100"
                                      : "text-slate-200 hover:bg-slate-800"
                                  }`}
                                >
                                  {option.label}
                                </button>
                              );
                            })
                          )}
                        </div>

                        {getSelectedOption(field) ? (
                          <p className="text-xs text-slate-400">
                            Selected: <span className="text-slate-200">{getSelectedOption(field).label}</span>
                          </p>
                        ) : null}
                      </div>
                    ) : field.type === "select" ? (
                      <select
                        id={field.name}
                        name={field.name}
                        value={value}
                        onChange={handleChange}
                        disabled={loading || field.disabled}
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
                        disabled={loading || field.disabled}
                        placeholder={field.placeholder || ""}
                        min={field.min}
                        max={field.max}
                        step={field.step}
                        className={inputClass}
                        autoComplete={field.autoComplete}
                        inputMode={field.inputMode}
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
