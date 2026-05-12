export default function Sidebar() {
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
    </aside>
  );
}
