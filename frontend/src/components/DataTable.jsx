import { useMemo, useState } from "react";
import LoadingSpinner from "./LoadingSpinner";

function toSearchText(value) {
  if (value === null || value === undefined) {
    return "";
  }
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return "";
}

function resolveCellValue(row, column) {
  if (typeof column.accessor === "function") {
    return column.accessor(row);
  }
  if (typeof column.key === "string") {
    return row?.[column.key];
  }
  return undefined;
}

export default function DataTable({
  data = [],
  columns = [],
  loading = false,
  emptyMessage = "No data available.",
  searchPlaceholder = "Search records...",
  searchable = true,
  rowKey = "id",
  initialPageSize = 10,
  pageSizeOptions = [10, 25, 50],
  actions,
  className = "",
}) {
  const [searchTerm, setSearchTerm] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(initialPageSize);

  const normalizedColumns = useMemo(
    () =>
      columns.map((column) => ({
        searchable: true,
        align: "left",
        ...column,
      })),
    [columns]
  );

  const filteredData = useMemo(() => {
    if (!searchable || !searchTerm.trim()) {
      return data;
    }

    const query = searchTerm.toLowerCase();
    return data.filter((row) =>
      normalizedColumns.some((column) => {
        if (!column.searchable) {
          return false;
        }
        const value = resolveCellValue(row, column);
        return toSearchText(value).toLowerCase().includes(query);
      })
    );
  }, [data, normalizedColumns, searchTerm, searchable]);

  const totalItems = filteredData.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  const safePage = Math.min(page, totalPages);

  const paginatedData = useMemo(() => {
    const start = (safePage - 1) * pageSize;
    return filteredData.slice(start, start + pageSize);
  }, [filteredData, safePage, pageSize]);

  function handleSearchChange(event) {
    setSearchTerm(event.target.value);
    setPage(1);
  }

  function handlePageSizeChange(event) {
    setPageSize(Number(event.target.value));
    setPage(1);
  }

  function handlePrevPage() {
    setPage((prev) => Math.max(1, prev - 1));
  }

  function handleNextPage() {
    setPage((prev) => Math.min(totalPages, prev + 1));
  }

  return (
    <section className={`rounded-xl border border-slate-800 bg-slate-900/70 ${className}`}>
      <header className="flex flex-col gap-3 border-b border-slate-800 p-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-slate-300">
          {totalItems} record{totalItems === 1 ? "" : "s"}
        </p>

        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          {searchable ? (
            <input
              type="search"
              value={searchTerm}
              onChange={handleSearchChange}
              placeholder={searchPlaceholder}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-500 focus:border-teal-400 focus:ring-2 focus:ring-teal-400/25 sm:w-64"
              aria-label="Search table data"
            />
          ) : null}

          <select
            value={pageSize}
            onChange={handlePageSizeChange}
            className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-teal-400"
            aria-label="Rows per page"
          >
            {pageSizeOptions.map((option) => (
              <option key={option} value={option}>
                {option} / page
              </option>
            ))}
          </select>
        </div>
      </header>

      {loading ? (
        <div className="p-8">
          <LoadingSpinner label="Loading records..." />
        </div>
      ) : paginatedData.length === 0 ? (
        <div className="p-8 text-center text-sm text-slate-300">{emptyMessage}</div>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-800">
              <thead className="bg-slate-950/40">
                <tr>
                  {normalizedColumns.map((column) => (
                    <th
                      key={column.key || column.header}
                      className={`px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-400 ${
                        column.align === "right"
                          ? "text-right"
                          : column.align === "center"
                            ? "text-center"
                            : "text-left"
                      }`}
                    >
                      {column.header}
                    </th>
                  ))}
                  {actions ? (
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-400">
                      Actions
                    </th>
                  ) : null}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {paginatedData.map((row, rowIndex) => {
                  const key =
                    (typeof rowKey === "function" ? rowKey(row) : row?.[rowKey]) ??
                    `${rowIndex}`;

                  return (
                    <tr key={key} className="hover:bg-slate-800/45">
                      {normalizedColumns.map((column) => {
                        const rawValue = resolveCellValue(row, column);
                        const renderedValue = column.render
                          ? column.render(rawValue, row)
                          : toSearchText(rawValue);

                        return (
                          <td
                            key={column.key || column.header}
                            className={`px-4 py-3 text-sm text-slate-100 ${
                              column.align === "right"
                                ? "text-right"
                                : column.align === "center"
                                  ? "text-center"
                                  : "text-left"
                            }`}
                          >
                            {renderedValue}
                          </td>
                        );
                      })}

                      {actions ? (
                        <td className="px-4 py-3 text-right text-sm text-slate-100">
                          <div className="inline-flex items-center gap-2">{actions(row)}</div>
                        </td>
                      ) : null}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <footer className="flex flex-col gap-3 border-t border-slate-800 p-4 text-sm text-slate-300 sm:flex-row sm:items-center sm:justify-between">
            <p>
              Showing {(safePage - 1) * pageSize + 1}-
              {Math.min(safePage * pageSize, totalItems)} of {totalItems}
            </p>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handlePrevPage}
                disabled={safePage <= 1}
                className="rounded-md border border-slate-700 px-3 py-1.5 text-slate-200 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Previous
              </button>
              <span className="min-w-20 text-center text-slate-300">
                Page {safePage} / {totalPages}
              </span>
              <button
                type="button"
                onClick={handleNextPage}
                disabled={safePage >= totalPages}
                className="rounded-md border border-slate-700 px-3 py-1.5 text-slate-200 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </footer>
        </>
      )}
    </section>
  );
}
