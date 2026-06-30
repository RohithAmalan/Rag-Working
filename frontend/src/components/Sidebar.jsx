import { dedupeByFileName, getFilteredRagDocuments } from "../utils/ragDocuments";

export default function Sidebar({ docs }) {
  const rawDocuments = Array.isArray(docs?.documents) ? docs.documents : [];
  const uniqueFiles = dedupeByFileName(getFilteredRagDocuments(rawDocuments));
  const hiddenCount = Math.max(rawDocuments.length - uniqueFiles.length, 0);

  const typeCounts = {
    csv: uniqueFiles.filter((file) => file.source_type === "csv").length,
    excel: uniqueFiles.filter((file) => file.source_type === "excel").length,
    pdf: uniqueFiles.filter((file) => file.source_type === "pdf").length,
  };

  return (
    <aside className="animate-rise rounded-3xl border border-white/70 bg-white/75 p-5 shadow-card backdrop-blur">
      <h1 className="font-display text-xl font-bold text-ink">RAG Explorer</h1>
      <p className="mt-2 text-sm text-ink/70">
        Excel and CSV are ranked first during retrieval, while PDFs are used as support context.
      </p>

      <div className="mt-6 space-y-3 text-sm text-ink/80">
        <div className="rounded-2xl bg-sand p-3">
          <p className="font-semibold">Pipeline</p>
          <p>Upload - Chunk - Embed - Retrieve - Generate</p>
        </div>
        <div className="rounded-2xl bg-sand p-3">
          <p className="font-semibold">Rule</p>
          <p>Answer only from retrieved context.</p>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-3 gap-2 text-center text-xs">
        <div className="rounded-xl bg-white/70 px-2 py-2 text-ink/80">
          <p className="font-semibold">CSV</p>
          <p>{typeCounts.csv}</p>
        </div>
        <div className="rounded-xl bg-white/70 px-2 py-2 text-ink/80">
          <p className="font-semibold">Excel</p>
          <p>{typeCounts.excel}</p>
        </div>
        <div className="rounded-xl bg-white/70 px-2 py-2 text-ink/80">
          <p className="font-semibold">PDF</p>
          <p>{typeCounts.pdf}</p>
        </div>
      </div>

      <div className="mt-6 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-ink">Indexed Files ({uniqueFiles.length})</h2>
          {hiddenCount > 0 && <span className="text-[11px] text-ink/55">hidden unsupported: {hiddenCount}</span>}
        </div>
        <div className="max-h-48 space-y-2 overflow-y-auto rounded-2xl bg-white/50 p-3">
          {uniqueFiles.length === 0 ? (
            <p className="text-sm text-ink/60">No files indexed yet</p>
          ) : (
            uniqueFiles.map((file, idx) => (
              <div
                key={`${file.file_name}-${idx}`}
                className="rounded-lg bg-white/70 p-2 text-xs text-ink/80"
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <p className="truncate font-medium">{file.file_name}</p>
                    <p className="text-ink/60">
                      {file.source_type === "csv" && "CSV"}
                      {file.source_type === "excel" && "Excel"}
                      {file.source_type === "pdf" && "PDF"}
                    </p>
                    <p className="text-ink/55">chunks: {file.chunks || 0}</p>
                    {file.analysis_report?.row_count !== undefined && (
                      <p className="text-ink/55">
                        rows: {file.analysis_report.row_count}
                        {file.analysis_report.column_count !== undefined
                          ? ` | cols: ${file.analysis_report.column_count}`
                          : ""}
                      </p>
                    )}
                    {file.analysis_report?.sheet_count !== undefined && (
                      <p className="text-ink/55">sheets: {file.analysis_report.sheet_count}</p>
                    )}
                    {file.analysis_report?.page_count !== undefined && (
                      <p className="text-ink/55">pages: {file.analysis_report.page_count}</p>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </aside>
  );
}
