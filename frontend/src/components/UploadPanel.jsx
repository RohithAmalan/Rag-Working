export default function UploadPanel({ files, onPickFiles, onUpload, uploading, uploadResult, error, storageStatus }) {
  const minioEnabled = Boolean(storageStatus?.minio?.enabled);
  const minioConnected = Boolean(storageStatus?.minio?.connected);
  const minioEndpoint = storageStatus?.minio?.endpoint || "localhost:9000";
  const canUpload = storageStatus?.can_upload !== false;

  return (
    <section className="animate-rise rounded-3xl border border-white/70 bg-white/85 p-5 shadow-card">
      <h2 className="font-display text-lg font-semibold text-ink">Upload Data Sources</h2>
      <p className="mt-1 text-sm text-ink/70">Supports .csv, .xlsx, and .pdf files.</p>

      {minioEnabled && !minioConnected && (
        <div className="mt-3 rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          MinIO is required but currently unreachable at {minioEndpoint}. Start MinIO to enable uploads.
        </div>
      )}

      <label className="mt-4 flex cursor-pointer items-center justify-center rounded-2xl border-2 border-dashed border-sky/50 bg-gradient-to-br from-sky/5 to-sky/10 p-8 text-center text-sm text-ink/75 transition-all hover:border-sky hover:bg-sky/15 hover:shadow-lg">
        <input
          type="file"
          className="hidden"
          multiple
          accept=".csv,.xlsx,.pdf"
          onChange={(event) => onPickFiles(Array.from(event.target.files || []))}
        />
        <div>
          <div className="mb-2 text-3xl">📂</div>
          <div className="font-medium">Select one or more files</div>
          <div className="mt-1 text-xs text-ink/50">CSV, Excel, or PDF</div>
        </div>
      </label>

      <div className="mt-3 text-sm text-ink/70">
        {files.length ? (
          <div className="flex items-center gap-2 rounded-lg bg-mint/10 px-3 py-2">
            <span className="text-mint">✓</span>
            <span className="font-medium">{files.length} file(s) selected</span>
          </div>
        ) : (
          <div className="text-ink/50">No files selected</div>
        )}
      </div>

      <button
        type="button"
        onClick={onUpload}
        disabled={!files.length || uploading || !canUpload}
        className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-ink to-ink/80 px-4 py-3 text-sm font-semibold text-white shadow-md transition-all hover:shadow-lg disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
      >
        {uploading ? (
          <>
            <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Uploading...
          </>
        ) : (
          <>
            <span>⬆️</span> Upload and Index
          </>
        )}
      </button>

      {uploadResult && (
        <div className="mt-3 rounded-lg border border-mint/30 bg-mint/10 px-3 py-2">
          <p className="text-sm font-medium text-mint">
            ✓ Indexed {uploadResult.processed_files} files ({uploadResult.total_chunks || 0} chunks)
          </p>
        </div>
      )}
      {error && (
        <div className="mt-3 rounded-lg border border-coral/30 bg-coral/10 px-3 py-2">
          <p className="text-sm font-medium text-coral">✗ {error}</p>
        </div>
      )}
    </section>
  );
}
