import SourceBadge from "./SourceBadge";

export default function ContextViewer({ chunks }) {
  return (
    <section className="animate-rise rounded-3xl border border-white/70 bg-white/85 p-5 shadow-card">
      <h2 className="font-display text-lg font-semibold text-ink">Retrieved Context</h2>
      <p className="mt-1 text-sm text-ink/70">Top chunks used by the assistant for the latest answer.</p>

      <div className="mt-4 max-h-[26rem] space-y-3 overflow-y-auto">
        {chunks.length === 0 && <p className="text-sm text-ink/60">No retrieved context yet.</p>}
        {chunks.map((item, idx) => (
          <article key={idx} className="rounded-2xl border border-ink/10 bg-sand p-3">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <SourceBadge type={item.metadata?.source_type} />
                <span className="text-xs text-ink/60">{item.metadata?.file_name || "Unknown file"}</span>
              </div>
              <span className="font-mono text-xs text-ink/55">score: {item.score?.toFixed?.(4) || item.score}</span>
            </div>
            <p className="mt-2 whitespace-pre-wrap text-sm text-ink/90">{item.content}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
