import { useState } from "react";

export default function FileDataViewer({ fileData, onPageChange, onSheetChange }) {
  if (!fileData) {
    return (
      <div className="animate-rise rounded-3xl border border-white/70 bg-white/75 p-6 shadow-card backdrop-blur">
        <p className="text-center text-ink/60">Select a file to view its data</p>
      </div>
    );
  }

  const { file_type, columns, rows, total_rows, current_page, total_pages, page_size, sheet_names, selected_sheet, pages } = fileData;

  // Render for Excel/CSV files
  if (file_type === "csv" || file_type === "excel") {
    return (
      <div className="animate-rise space-y-4">
        {/* Header with sheet selector for Excel */}
        <div className="flex items-center justify-between rounded-3xl border border-white/70 bg-white/75 p-4 shadow-card backdrop-blur">
          <div>
            <h2 className="font-display text-xl font-bold text-ink">
              {fileData.file_name}
            </h2>
            <p className="text-sm text-ink/60">
              {total_rows.toLocaleString()} total rows
            </p>
          </div>
          {file_type === "excel" && sheet_names && sheet_names.length > 1 && (
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-ink">Sheet:</label>
              <select
                value={selected_sheet}
                onChange={(e) => onSheetChange(e.target.value)}
                className="rounded-xl border border-ink/20 bg-white px-3 py-2 text-sm text-ink focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20"
              >
                {sheet_names.map((sheet) => (
                  <option key={sheet} value={sheet}>
                    {sheet}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Data Table */}
        <div className="rounded-3xl border border-white/70 bg-white/75 shadow-card backdrop-blur">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-ink/10 bg-sand/30">
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-ink/70">
                    #
                  </th>
                  {columns.map((col, idx) => (
                    <th
                      key={idx}
                      className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-ink/70"
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, rowIdx) => (
                  <tr
                    key={rowIdx}
                    className="border-b border-ink/5 transition-colors hover:bg-sand/20"
                  >
                    <td className="px-4 py-3 text-xs font-medium text-ink/50">
                      {(current_page - 1) * page_size + rowIdx + 1}
                    </td>
                    {columns.map((col, colIdx) => (
                      <td key={colIdx} className="px-4 py-3 text-sm text-ink">
                        {row[col] !== undefined && row[col] !== null && row[col] !== ""
                          ? String(row[col])
                          : "—"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {total_pages > 1 && (
            <div className="flex items-center justify-between border-t border-ink/10 bg-sand/10 px-6 py-4">
              <div className="text-sm text-ink/60">
                Page {current_page} of {total_pages}
                <span className="ml-2">
                  ({(current_page - 1) * page_size + 1} -{" "}
                  {Math.min(current_page * page_size, total_rows)} of {total_rows.toLocaleString()})
                </span>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => onPageChange(1)}
                  disabled={current_page === 1}
                  className="rounded-xl bg-white px-3 py-2 text-sm font-medium text-ink transition-all hover:bg-sand disabled:cursor-not-allowed disabled:opacity-40"
                >
                  First
                </button>
                <button
                  onClick={() => onPageChange(current_page - 1)}
                  disabled={current_page === 1}
                  className="rounded-xl bg-white px-3 py-2 text-sm font-medium text-ink transition-all hover:bg-sand disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Previous
                </button>
                <button
                  onClick={() => onPageChange(current_page + 1)}
                  disabled={current_page === total_pages}
                  className="rounded-xl bg-white px-3 py-2 text-sm font-medium text-ink transition-all hover:bg-sand disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Next
                </button>
                <button
                  onClick={() => onPageChange(total_pages)}
                  disabled={current_page === total_pages}
                  className="rounded-xl bg-white px-3 py-2 text-sm font-medium text-ink transition-all hover:bg-sand disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Last
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Render for PDF files
  if (file_type === "pdf") {
    return (
      <div className="animate-rise space-y-4">
        <div className="rounded-3xl border border-white/70 bg-white/75 p-4 shadow-card backdrop-blur">
          <h2 className="font-display text-xl font-bold text-ink">
            {fileData.file_name}
          </h2>
          <p className="text-sm text-ink/60">
            {total_pages} total pages
          </p>
        </div>

        <div className="space-y-4">
          {pages.map((page, idx) => (
            <div
              key={idx}
              className="rounded-3xl border border-white/70 bg-white/75 p-6 shadow-card backdrop-blur"
            >
              <div className="mb-3 flex items-center justify-between border-b border-ink/10 pb-2">
                <h3 className="font-semibold text-ink">Page {page.page_number}</h3>
              </div>
              <div className="whitespace-pre-wrap text-sm text-ink">
                {page.content || <span className="text-ink/40">No text content</span>}
              </div>
            </div>
          ))}
        </div>

        {/* Pagination for PDFs */}
        {total_pages > page_size && (
          <div className="flex items-center justify-between rounded-3xl border border-white/70 bg-white/75 p-4 shadow-card backdrop-blur">
            <div className="text-sm text-ink/60">
              Page {current_page} of {Math.ceil(total_pages / page_size)}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => onPageChange(current_page - 1)}
                disabled={current_page === 1}
                className="rounded-xl bg-white px-3 py-2 text-sm font-medium text-ink transition-all hover:bg-sand disabled:cursor-not-allowed disabled:opacity-40"
              >
                Previous
              </button>
              <button
                onClick={() => onPageChange(current_page + 1)}
                disabled={current_page * page_size >= total_pages}
                className="rounded-xl bg-white px-3 py-2 text-sm font-medium text-ink transition-all hover:bg-sand disabled:cursor-not-allowed disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    );
  }

  return null;
}
