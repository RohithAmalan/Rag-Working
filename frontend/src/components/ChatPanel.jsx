import { useState } from "react";
import toast from "react-hot-toast";

export default function ChatPanel({
  chatHistory,
  question,
  setQuestion,
  onAsk,
  loading,
  error,
  documents,
  selectedFile,
  setSelectedFile,
}) {
  const docItems = Array.isArray(documents?.documents) ? documents.documents : [];
  const [copiedIndex, setCopiedIndex] = useState(null);

  const handleCopy = (text, index) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedIndex(index);
      toast.success("Answer copied to clipboard!");
      setTimeout(() => setCopiedIndex(null), 2000);
    }).catch(() => {
      toast.error("Failed to copy");
    });
  };

  return (
    <section className="animate-rise rounded-3xl border border-white/70 bg-white/85 p-5 shadow-card">
      <h2 className="font-display text-lg font-semibold text-ink">Ask Questions</h2>
      <p className="mt-1 text-sm text-ink/70">Natural language queries over your uploaded business data.</p>

      <div className="mt-3 grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-[9rem_minmax(0,1fr)] sm:items-center">
        <p className="text-xs font-semibold uppercase tracking-wide text-ink/60">Search Scope</p>
        <select
          value={selectedFile}
          onChange={(event) => setSelectedFile(event.target.value)}
          className="w-full min-w-0 rounded-xl border border-ink/15 bg-white px-3 py-2 text-sm text-ink outline-none focus:border-ink/40"
        >
          <option value="__all__">All files</option>
          {docItems.map((doc, idx) => {
            const fileName = doc.file_name || `file-${idx + 1}`;
            return (
              <option key={`${fileName}-${idx}`} value={fileName}>
                {fileName}
              </option>
            );
          })}
        </select>
      </div>

      <div className="mt-4 h-72 space-y-3 overflow-y-auto rounded-2xl bg-sand p-3">
        {chatHistory.length === 0 && (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-ink/50">💬 No messages yet. Ask a question to get started!</p>
          </div>
        )}
        {chatHistory.map((item, idx) => (
          <div
            key={`${item.role}-${idx}`}
            className={`group relative rounded-xl p-4 shadow-sm transition-all hover:shadow-md ${
              item.role === "user"
                ? "border border-sky/30 bg-gradient-to-br from-sky/10 to-white"
                : "border border-mint/30 bg-gradient-to-br from-mint/10 to-white"
            }`}
          >
            <div className="mb-2 flex items-center justify-between">
              <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-ink/60">
                {item.role === "user" ? (
                  <>
                    <span className="text-sky">👤</span> You
                  </>
                ) : (
                  <>
                    <span className="text-mint">🤖</span> Assistant
                  </>
                )}
              </p>
              {item.role === "assistant" && (
                <button
                  onClick={() => handleCopy(item.text, idx)}
                  className="rounded-lg bg-white px-3 py-1 text-xs font-medium text-ink/60 opacity-0 shadow-sm transition-all hover:bg-ink hover:text-white group-hover:opacity-100"
                  title="Copy answer"
                >
                  {copiedIndex === idx ? "✓ Copied" : "📋 Copy"}
                </button>
              )}
            </div>
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink">{item.text}</p>
            
            {/* Display citations if available */}
            {item.role === "assistant" && item.citations && item.citations.length > 0 && (
              <div className="mt-3 border-t border-mint/20 pt-3">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink/60">
                  📚 Sources ({item.citations.length})
                </p>
                <div className="space-y-2">
                  {item.citations.map((citation, citIdx) => (
                    <div 
                      key={citIdx}
                      className="rounded-lg border border-mint/20 bg-white/60 p-2 text-xs"
                    >
                      <div className="flex items-start gap-2">
                        <span className="flex-shrink-0 font-bold text-mint">[{citation.number}]</span>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-ink">
                            {citation.file_name}
                            {citation.page_number && ` • Page ${citation.page_number}`}
                            {citation.row_number && ` • Row ${citation.row_number}`}
                          </p>
                          {citation.text_preview && (
                            <p className="mt-1 text-ink/60 line-clamp-2">
                              {citation.text_preview}
                            </p>
                          )}
                          <span className="mt-1 inline-block rounded px-2 py-0.5 text-[10px] font-medium uppercase bg-mint/10 text-mint">
                            {citation.source_type}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex items-center gap-3 rounded-xl border border-accent/30 bg-gradient-to-br from-accent/10 to-white p-4">
            <div className="flex space-x-1">
              <div className="h-2 w-2 animate-bounce rounded-full bg-accent" style={{ animationDelay: "0ms" }}></div>
              <div className="h-2 w-2 animate-bounce rounded-full bg-accent" style={{ animationDelay: "150ms" }}></div>
              <div className="h-2 w-2 animate-bounce rounded-full bg-accent" style={{ animationDelay: "300ms" }}></div>
            </div>
            <p className="text-sm font-medium text-accent">Thinking...</p>
          </div>
        )}
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
          className="flex items-center justify-center gap-2 rounded-xl bg-coral px-5 py-3 text-sm font-bold text-white shadow-lg transition-all hover:bg-coral/90 hover:shadow-xl disabled:cursor-not-allowed disabled:bg-gray-400 disabled:shadow-none"
        >
          {loading ? (
            <>
              <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Processing...
            </>
          ) : (
            <>
              <span>🚀</span> Send
            </>
          )}
        </button>
      </div>

      {error && <p className="mt-3 text-sm text-coral">{error}</p>}
    </section>
  );
}
