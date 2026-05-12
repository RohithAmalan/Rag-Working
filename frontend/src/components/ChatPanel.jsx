export default function ChatPanel({
  chatHistory,
  question,
  setQuestion,
  onAsk,
  loading,
  error,
}) {
  return (
    <section className="animate-rise rounded-3xl border border-white/70 bg-white/85 p-5 shadow-card">
      <h2 className="font-display text-lg font-semibold text-ink">Ask Questions</h2>
      <p className="mt-1 text-sm text-ink/70">Natural language queries over your uploaded business data.</p>

      <div className="mt-4 h-72 space-y-3 overflow-y-auto rounded-2xl bg-sand p-3">
        {chatHistory.length === 0 && <p className="text-sm text-ink/60">No messages yet.</p>}
        {chatHistory.map((item, idx) => (
          <div key={`${item.role}-${idx}`} className="rounded-xl bg-white p-3">
            <p className="text-xs uppercase tracking-wide text-ink/50">{item.role}</p>
            <p className="mt-1 whitespace-pre-wrap text-sm text-ink">{item.text}</p>
          </div>
        ))}
      </div>

      <div className="mt-4 flex flex-col gap-3 sm:flex-row">
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="What was the highest sales month?"
          className="h-24 w-full rounded-xl border border-ink/15 bg-white p-3 text-sm text-ink outline-none focus:border-ink/40"
        />
        <button
          type="button"
          onClick={onAsk}
          disabled={loading || !question.trim()}
          className="rounded-xl bg-coral px-5 py-3 text-sm font-semibold text-white transition disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? "Thinking..." : "Send"}
        </button>
      </div>

      {error && <p className="mt-3 text-sm text-coral">{error}</p>}
    </section>
  );
}
