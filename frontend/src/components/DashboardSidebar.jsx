import { dedupeByFileName, getFilteredRagDocuments } from "../utils/ragDocuments";

export default function DashboardSidebar({ documents, selectedFile, onSelectFile }) {
  const uniqueFiles = dedupeByFileName(
    getFilteredRagDocuments(Array.isArray(documents?.documents) ? documents.documents : [])
  );

  // Filter out PDFs for data dashboard (show only Excel/CSV)
  const dataFiles = uniqueFiles.filter(
    (file) => file.source_type === "csv" || file.source_type === "excel"
  );

  return (
    <aside className="animate-rise rounded-3xl border border-white/70 bg-white/75 p-5 shadow-card backdrop-blur">
      <h1 className="font-display text-xl font-bold text-ink">Data Dashboard</h1>
      <p className="mt-2 text-sm text-ink/70">
        View and explore your uploaded Excel and CSV files dynamically.
      </p>

      <div className="mt-6 space-y-3 text-sm text-ink/80">
        <div className="rounded-2xl bg-sand p-3">
          <p className="font-semibold">Features</p>
          <ul className="mt-1 list-inside list-disc space-y-1 text-xs">
            <li>Dynamic table view</li>
            <li>Column-based browsing</li>
            <li>Paginated data display</li>
            <li>Multi-sheet Excel support</li>
          </ul>
        </div>
      </div>

      {/* File Selector */}
      <div className="mt-6 space-y-3">
        <h2 className="font-semibold text-ink">
          Available Files ({dataFiles.length})
        </h2>
        <div className="max-h-96 space-y-2 overflow-y-auto rounded-2xl bg-white/50 p-3">
          {dataFiles.length === 0 ? (
            <div className="text-center text-sm text-ink/60">
              <p>No data files available</p>
              <p className="mt-2 text-xs">Upload Excel or CSV files to get started</p>
            </div>
          ) : (
            dataFiles.map((file, idx) => (
              <button
                key={`${file.file_name}-${idx}`}
                onClick={() => onSelectFile(file.file_name)}
                className={`w-full rounded-lg p-3 text-left text-xs transition-all ${
                  selectedFile === file.file_name
                    ? "bg-accent text-white shadow-md"
                    : "bg-white/70 text-ink/80 hover:bg-sand hover:shadow-sm"
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className="truncate font-medium">
                      {file.file_name}
                    </p>
                    <div className="mt-1 flex items-center gap-2">
                      <span className="text-[10px]">
                        {file.source_type === "csv" && "📊 CSV"}
                        {file.source_type === "excel" && "📗 Excel"}
                      </span>
                      {file.analysis_report?.row_count !== undefined && (
                        <span className="text-[10px] opacity-70">
                          {file.analysis_report.row_count.toLocaleString()} rows
                        </span>
                      )}
                      {file.analysis_report?.column_count !== undefined && (
                        <span className="text-[10px] opacity-70">
                          {file.analysis_report.column_count} cols
                        </span>
                      )}
                    </div>
                    {file.analysis_report?.sheet_count !== undefined && file.analysis_report.sheet_count > 1 && (
                      <p className="mt-1 text-[10px] opacity-70">
                        {file.analysis_report.sheet_count} sheets
                      </p>
                    )}
                  </div>
                  {selectedFile === file.file_name && (
                    <svg
                      className="h-4 w-4 flex-shrink-0"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                  )}
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Stats Summary */}
      {selectedFile && (
        <div className="mt-4 rounded-2xl bg-sand/50 p-3 text-xs">
          <p className="font-semibold text-ink">Selected File</p>
          <p className="mt-1 truncate text-ink/70">{selectedFile}</p>
        </div>
      )}
    </aside>
  );
}
