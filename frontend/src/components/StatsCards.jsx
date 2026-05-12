export default function StatsCards({ docs }) {
  const cards = [
    { label: "Total Chunks", value: docs.total_chunks || 0 },
    { label: "Primary Chunks", value: docs.primary_chunks || 0 },
    { label: "Secondary Chunks", value: docs.secondary_chunks || 0 },
  ];

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      {cards.map((card, idx) => (
        <div
          key={card.label}
          className="animate-rise rounded-2xl border border-white/70 bg-white/85 p-4 shadow-card"
          style={{ animationDelay: `${idx * 80}ms` }}
        >
          <p className="text-xs uppercase tracking-wide text-ink/60">{card.label}</p>
          <p className="mt-2 font-display text-2xl font-bold text-ink">{card.value}</p>
        </div>
      ))}
    </div>
  );
}
