import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import DashboardSidebar from "../components/DashboardSidebar";
import FileDataViewer from "../components/FileDataViewer";
import { fetchFilePreview } from "../services/api";

export default function DataDashboard({ documents, onRefresh }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileData, setFileData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [currentSheet, setCurrentSheet] = useState(null);
  const [pageSize] = useState(100);

  // Load file data when file is selected or page/sheet changes
  useEffect(() => {
    if (!selectedFile) {
      setFileData(null);
      return;
    }

    const loadFileData = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchFilePreview(selectedFile, currentPage, pageSize, currentSheet);
        setFileData(data);
      } catch (err) {
        console.error("Failed to load file data:", err);
        setError(err.response?.data?.detail || "Failed to load file data");
        setFileData(null);
      } finally {
        setLoading(false);
      }
    };

    loadFileData();
  }, [selectedFile, currentPage, currentSheet, pageSize]);

  const handleSelectFile = (fileName) => {
    setSelectedFile(fileName);
    setCurrentPage(1);
    setCurrentSheet(null);
    setError(null);
  };

  const handlePageChange = (newPage) => {
    setCurrentPage(newPage);
  };

  const handleSheetChange = (newSheet) => {
    setCurrentSheet(newSheet);
    setCurrentPage(1); // Reset to first page when changing sheets
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-sand via-white to-accent/5 p-6">
      {/* Header Navigation */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-bold text-ink">Data Dashboard</h1>
          <p className="text-sm text-ink/70">Browse and explore your uploaded files</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={onRefresh}
            className="rounded-2xl border border-ink/20 bg-white px-4 py-2 text-sm font-medium text-ink transition-all hover:border-accent hover:bg-sand hover:shadow-md"
          >
            🔄 Refresh Files
          </button>
          <Link
            to="/analytics-dashboard"
            className="rounded-2xl border border-accent bg-white px-4 py-2 text-sm font-medium text-accent transition-all hover:bg-accent hover:text-white hover:shadow-md"
          >
            📈 Analytics Dashboard
          </Link>
          <Link
            to="/"
            className="rounded-2xl bg-accent px-4 py-2 text-sm font-medium text-white transition-all hover:bg-accent/90 hover:shadow-lg"
          >
            ← Back to RAG
          </Link>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-12 gap-6">
        {/* Sidebar - 3 columns */}
        <div className="col-span-12 lg:col-span-3">
          <DashboardSidebar
            documents={documents}
            selectedFile={selectedFile}
            onSelectFile={handleSelectFile}
          />
        </div>

        {/* Main Data Viewer - 9 columns */}
        <div className="col-span-12 lg:col-span-9">
          {loading && (
            <div className="animate-rise rounded-3xl border border-white/70 bg-white/75 p-8 shadow-card backdrop-blur">
              <div className="flex items-center justify-center">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-accent border-t-transparent"></div>
                <p className="ml-3 text-ink/70">Loading file data...</p>
              </div>
            </div>
          )}

          {error && (
            <div className="animate-rise rounded-3xl border border-red-200 bg-red-50/75 p-6 shadow-card backdrop-blur">
              <div className="flex items-center">
                <span className="text-2xl">⚠️</span>
                <div className="ml-3">
                  <p className="font-semibold text-red-900">Error loading file</p>
                  <p className="mt-1 text-sm text-red-700">{error}</p>
                </div>
              </div>
            </div>
          )}

          {!loading && !error && (
            <FileDataViewer
              fileData={fileData}
              onPageChange={handlePageChange}
              onSheetChange={handleSheetChange}
            />
          )}
        </div>
      </div>
    </div>
  );
}
