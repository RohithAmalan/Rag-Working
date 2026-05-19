import { useMemo, useState } from "react";

export default function ReportPanel({ docs, onDeleteDocument, deletingDocumentId }) {
  const items = Array.isArray(docs?.documents) ? docs.documents : [];
  const [selectedKey, setSelectedKey] = useState("");

  const selectedDoc = useMemo(() => {
    if (!items.length) return null;

    const defaultKey = `${items[0].file_name || "Unknown file"}-0`;
    const activeKey = selectedKey || defaultKey;

    const found = items.find((doc, idx) => {
      const key = `${doc.file_name || "Unknown file"}-${idx}`;
      return key === activeKey;
    });

    return found || items[0];
  }, [items, selectedKey]);

  const renderDetails = () => {
    if (!selectedDoc) return <p className="text-sm text-ink/60">Select a file to view report details.</p>;

    const report = selectedDoc.analysis_report || {};
    const columnNames = Array.isArray(report.column_names) ? report.column_names : [];
    const sampleRows = Array.isArray(report.sample_rows) ? report.sample_rows : [];
    const sheetReports = Array.isArray(report.sheet_reports) ? report.sheet_reports : [];

    return (
      <div className="space-y-3 rounded-2xl border border-ink/10 bg-white/70 p-3">
        <div className="flex items-center justify-between gap-2">
          <p className="truncate text-sm font-semibold text-ink">{selectedDoc.file_name || "Unknown file"}</p>
          <span className="text-xs uppercase tracking-wide text-ink/60">{selectedDoc.source_type || "unknown"}</span>
        </div>

        <div className="grid grid-cols-1 gap-1 text-xs text-ink/80 sm:grid-cols-2">
          <p>chunks: {selectedDoc.chunks || 0}</p>
          <p>storage: {selectedDoc.storage_backend || "local"}</p>
          {selectedDoc.storage_path && <p className="truncate sm:col-span-2">path: {selectedDoc.storage_path}</p>}
          {report.file_size_bytes !== undefined && <p>size: {report.file_size_bytes} bytes</p>}
          {report.row_count !== undefined && <p>rows: {report.row_count}</p>}
          {report.column_count !== undefined && <p>columns: {report.column_count}</p>}
          {report.sheet_count !== undefined && <p>sheets: {report.sheet_count}</p>}
          {report.page_count !== undefined && <p>pages: {report.page_count}</p>}
          {report.pages_with_text !== undefined && <p>pages with text: {report.pages_with_text}</p>}
          {report.character_count !== undefined && <p>chars: {report.character_count}</p>}
        </div>

        {columnNames.length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-ink/60">Column Titles</p>
            <p className="mt-1 text-xs text-ink/85">{columnNames.join(", ")}</p>
          </div>
        )}

        {sheetReports.length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-ink/60">Sheet Details</p>
            <div className="mt-1 space-y-2">
              {sheetReports.map((sheet, idx) => (
                <div key={`${sheet.sheet_name || "sheet"}-${idx}`} className="rounded-lg border border-ink/10 bg-sand p-2 text-xs text-ink/85">
                  <p className="font-semibold">{sheet.sheet_name || "Sheet"}</p>
                  <p>rows: {sheet.row_count ?? 0} | columns: {sheet.column_count ?? 0}</p>
                  {Array.isArray(sheet.column_names) && sheet.column_names.length > 0 && (
                    <p className="mt-1">titles: {sheet.column_names.join(", ")}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {sampleRows.length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-ink/60">Sample Rows</p>
            <pre className="mt-1 max-h-48 overflow-auto rounded-lg border border-ink/10 bg-sand p-2 text-xs text-ink/85">
{JSON.stringify(sampleRows, null, 2)}
            </pre>
          </div>
        )}
      </div>
    );
  };

  return (
    <section className="animate-rise rounded-3xl border border-white/70 bg-white/85 p-5 shadow-card">
      <h2 className="font-display text-lg font-semibold text-ink">Upload Reports</h2>
      <p className="mt-1 text-sm text-ink/70">
        Click a file to inspect row/column titles and detailed upload report.
      </p>

      <div className="mt-4 grid grid-cols-1 gap-3 xl:grid-cols-2">
        <div className="max-h-[26rem] space-y-3 overflow-y-auto pr-1">
        {items.length === 0 && <p className="text-sm text-ink/60">No upload reports yet.</p>}

        {items.map((doc, idx) => {
          const report = doc.analysis_report || {};
          const fileName = doc.file_name || "Unknown file";
          const sourceType = doc.source_type || "unknown";
          const storage = doc.storage_backend || "local";
          const storagePath = doc.storage_path || "";
          const key = `${fileName}-${idx}`;
          const isSelected = selectedDoc && selectedDoc.file_name === fileName && selectedDoc.source_type === sourceType;

          return (
            <div
              key={key}
              role="button"
              tabIndex={0}
              onClick={() => setSelectedKey(key)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  setSelectedKey(key);
                }
              }}
              className={`w-full rounded-2xl border p-3 text-left transition ${
                isSelected
                  ? "border-sky/50 bg-white shadow-sm"
                  : "border-ink/10 bg-sand hover:border-sky/40 hover:bg-white/80"
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <p className="truncate text-sm font-semibold text-ink">{fileName}</p>
                <span className="text-xs uppercase tracking-wide text-ink/60">{sourceType}</span>
              </div>

              <div className="mt-2 flex items-center justify-end">
                <button
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation();
                    if (doc.document_id && onDeleteDocument) {
                      onDeleteDocument(doc.document_id, fileName);
                    }
                  }}
                  disabled={!doc.document_id || deletingDocumentId === fileName}
                  className="rounded-lg border border-coral/40 bg-white px-2 py-1 text-xs font-semibold text-coral transition hover:bg-coral/10 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {deletingDocumentId === fileName ? "Deleting..." : "Delete"}
                </button>
              </div>

              <div className="mt-2 grid grid-cols-1 gap-1 text-xs text-ink/80 sm:grid-cols-2">
                <p>chunks: {doc.chunks || 0}</p>
                <p>storage: {storage}</p>
                {storagePath && <p className="truncate sm:col-span-2">path: {storagePath}</p>}
                {report.file_size_bytes !== undefined && <p>size: {report.file_size_bytes} bytes</p>}
                {report.row_count !== undefined && <p>rows: {report.row_count}</p>}
                {report.column_count !== undefined && <p>columns: {report.column_count}</p>}
              </div>
            </div>
          );
        })}
        </div>

        <div className="max-h-[26rem] overflow-y-auto pr-1">{renderDetails()}</div>
      </div>
    </section>
  );
}
