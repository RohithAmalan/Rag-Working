export default function Sidebar({ docs }) {
  // Get unique files - deduplicate by file_name
  const uniqueFiles = docs?.documents 
    ? Array.from(
        new Map(
          docs.documents.map((doc) => [doc.file_name, doc])
        ).values()
      )
    : [];

  return (
    <aside className="animate-rise rounded-3xl border border-white/70 bg-white/75 p-5 shadow-card backdrop-blur">
      <h1 className="font-display text-xl font-bold text-ink">RAG Control Deck</h1>
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

      {/* Display Indexed Files */}
      <div className="mt-6 space-y-3">
        <h2 className="font-semibold text-ink">Indexed Files ({uniqueFiles.length})</h2>
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
                      {file.source_type === "csv" && "📊 CSV"}
                      {(file.source_type === "xlsx" || file.source_type === "excel") && "📗 Excel"}
                      {file.source_type === "pdf" && "📄 PDF"}
                    </p>
                    <p className="text-ink/55">chunks: {file.chunks || 0}</p>
                    <p className="text-ink/55">storage: {file.storage_backend || "local"}</p>
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
