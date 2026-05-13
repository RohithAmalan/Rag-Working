import ChatPanel from "../components/ChatPanel";
import ContextViewer from "../components/ContextViewer";
import ReportPanel from "../components/ReportPanel";
import Sidebar from "../components/Sidebar";
import StatsCards from "../components/StatsCards";
import UploadPanel from "../components/UploadPanel";

export default function Dashboard(props) {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_right,_#fff1df,_#dff8ff_40%,_#f4f4f5_75%)] p-4 sm:p-6">
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
            />
            <ChatPanel
              chatHistory={props.chatHistory}
              question={props.question}
              setQuestion={props.setQuestion}
              onAsk={props.onAsk}
              loading={props.askLoading}
              error={props.askError}
            />
          </div>

          <ReportPanel docs={props.documents} />

          <ContextViewer chunks={props.retrievedChunks} />
        </div>
      </div>
    </div>
  );
}
