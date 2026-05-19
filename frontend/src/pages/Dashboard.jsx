import { Link } from "react-router-dom";
import ChatPanel from "../components/ChatPanel";
import ContextViewer from "../components/ContextViewer";
import ReportPanel from "../components/ReportPanel";
import Sidebar from "../components/Sidebar";
import StatsCards from "../components/StatsCards";
import UploadPanel from "../components/UploadPanel";

export default function Dashboard(props) {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_right,_#fff1df,_#dff8ff_40%,_#f4f4f5_75%)] p-4 sm:p-6">
      {/* Header Navigation */}
      <div className="mx-auto mb-6 flex max-w-7xl items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold text-ink">RAG Dashboard</h1>
          <p className="text-sm text-ink/70">Upload files and ask questions</p>
        </div>
        <div className="flex items-center gap-3">
          {props.username && (
            <div className="flex items-center gap-2 rounded-2xl bg-white/70 px-4 py-2">
              <span className="text-sm font-medium text-ink">👤 {props.username}</span>
            </div>
          )}
          <Link
            to="/data-dashboard"
            className="rounded-2xl border border-accent bg-white px-4 py-2 text-sm font-medium text-accent transition-all hover:bg-accent hover:text-white hover:shadow-md"
          >
            📊 Data Dashboard
          </Link>
          <Link
            to="/analytics-dashboard"
            className="rounded-2xl bg-accent px-4 py-2 text-sm font-medium text-white transition-all hover:bg-accent/90 hover:shadow-lg"
          >
            📈 Analytics Dashboard
          </Link>
          {props.onLogout && (
            <button
              onClick={props.onLogout}
              className="rounded-2xl bg-coral px-4 py-2 text-sm font-medium text-white transition-all hover:bg-coral/90 hover:shadow-lg"
            >
              🚪 Logout
            </button>
          )}
        </div>
      </div>

      <div className="mx-auto grid max-w-7xl grid-cols-1 gap-4 lg:grid-cols-12">
        <div className="lg:col-span-3">
          <Sidebar docs={props.documents} />
        </div>

        <div className="space-y-4 lg:col-span-9">
          <StatsCards docs={props.documents} />

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <UploadPanel
              files={props.files}
              onPickFiles={props.onPickFiles}
              onUpload={props.onUpload}
              uploading={props.uploading}
              uploadResult={props.uploadResult}
              error={props.uploadError}
              storageStatus={props.storageStatus}
            />
            <ChatPanel
              chatHistory={props.chatHistory}
              question={props.question}
              setQuestion={props.setQuestion}
              onAsk={props.onAsk}
              loading={props.askLoading}
              error={props.askError}
              documents={props.documents}
              selectedFile={props.selectedFile}
              setSelectedFile={props.setSelectedFile}
            />
          </div>

          <ReportPanel
            docs={props.documents}
            deletingDocumentId={props.deletingDocumentId}
            onDeleteDocument={props.onDeleteDocument}
          />

          <ContextViewer chunks={props.retrievedChunks} />
        </div>
      </div>
    </div>
  );
}
