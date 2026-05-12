const styles = {
  csv: "bg-mint/20 text-ink border border-mint/30",
  excel: "bg-sky/20 text-ink border border-sky/30",
  pdf: "bg-coral/15 text-ink border border-coral/40",
};

export default function SourceBadge({ type }) {
  const key = (type || "pdf").toLowerCase();
  return (
    <span className={`rounded-full px-2 py-1 text-xs font-medium ${styles[key] || styles.pdf}`}>
      {key.toUpperCase()}
    </span>
  );
}
