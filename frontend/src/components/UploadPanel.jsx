export default function UploadPanel({ files, onPickFiles, onUpload, uploading, uploadResult, error }) {
  return (
    <section className="animate-rise rounded-3xl border border-white/70 bg-white/85 p-5 shadow-card">
      <h2 className="font-display text-lg font-semibold text-ink">Upload Data Sources</h2>
      <p className="mt-1 text-sm text-ink/70">Supports .csv, .xlsx, and .pdf files.</p>

      <label className="mt-4 flex cursor-pointer items-center justify-center rounded-2xl border-2 border-dashed border-sky/50 bg-sky/5 p-6 text-center text-sm text-ink/75 hover:bg-sky/10">
        <input
          type="file"
          className="hidden"
          multiple
          accept=".csv,.xlsx,.pdf"
          onChange={(event) => onPickFiles(Array.from(event.target.files || []))}
        />
        Select one or more files
      </label>

      <div className="mt-3 text-sm text-ink/70">
        {files.length ? `${files.length} file(s) selected` : "No files selected"}
      </div>

      <button
        type="button"
        onClick={onUpload}
        disabled={!files.length || uploading}
        className="mt-4 rounded-xl bg-ink px-4 py-2 text-sm font-medium text-white transition disabled:cursor-not-allowed disabled:opacity-50"
      >
        {uploading ? "Uploading..." : "Upload and Index"}
      </button>

      {uploadResult && (
        <p className="mt-3 text-sm text-mint">
          Indexed {uploadResult.processed_files} files ({uploadResult.total_chunks || 0} chunks)
        </p>
      )}
      {error && <p className="mt-3 text-sm text-coral">{error}</p>}
    </section>
  );
}
