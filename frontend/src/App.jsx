import { useEffect, useState } from "react";
import { Routes, Route, Navigate, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";

import Dashboard from "./pages/Dashboard";
import DataDashboard from "./pages/DataDashboard";
import AnalyticsDashboard from "./pages/AnalyticsDashboard";
import Login from "./pages/Login";
import { askQuestion, deleteDocumentsByName, fetchDocuments, fetchStorageStatus, uploadFiles } from "./services/api";

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(null); // null = checking, false = not logged in, true = logged in
  const [username, setUsername] = useState("");
  const navigate = useNavigate();
  
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [uploadError, setUploadError] = useState("");

  const [question, setQuestion] = useState("");
  const [askLoading, setAskLoading] = useState(false);
  const [askError, setAskError] = useState("");
  const [chatHistory, setChatHistory] = useState([]);
  const [retrievedChunks, setRetrievedChunks] = useState([]);
  const [selectedFile, setSelectedFile] = useState("__all__");
  const [deletingDocumentId, setDeletingDocumentId] = useState("");

  const [documents, setDocuments] = useState({
    total_chunks: 0,
    primary_chunks: 0,
    secondary_chunks: 0,
    documents: [],
  });
  const [storageStatus, setStorageStatus] = useState({
    can_upload: true,
    upload_mode: "unknown",
    minio: { enabled: false, connected: false, endpoint: "", bucket: "" },
  });

  const normalizeDocuments = (data) => ({
    total_chunks: data?.total_chunks ?? data?.stats?.total_chunks ?? 0,
    primary_chunks: data?.primary_chunks ?? data?.stats?.primary_chunks ?? 0,
    secondary_chunks: data?.secondary_chunks ?? data?.stats?.secondary_chunks ?? 0,
    documents: Array.isArray(data?.documents) ? data.documents : [],
  });

  const loadDocuments = async () => {
    try {
      const data = await fetchDocuments();
      setDocuments(normalizeDocuments(data));
    } catch {
      setDocuments((prev) => prev);
    }
  };

  const loadStorageStatus = async () => {
    try {
      const data = await fetchStorageStatus();
      setStorageStatus({
        can_upload: Boolean(data?.can_upload),
        upload_mode: data?.upload_mode || "unknown",
        minio: {
          enabled: Boolean(data?.minio?.enabled),
          connected: Boolean(data?.minio?.connected),
          endpoint: data?.minio?.endpoint || "",
          bucket: data?.minio?.bucket || "",
        },
      });
    } catch {
      setStorageStatus((prev) => prev);
    }
  };

  useEffect(() => {
    // Check if user is already logged in
    const token = localStorage.getItem("access_token");
    const storedUsername = localStorage.getItem("username");
    
    if (token && storedUsername) {
      setIsAuthenticated(true);
      setUsername(storedUsername);
    } else {
      setIsAuthenticated(false);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated !== true) return; // Only load when authenticated (not null or false)
    
    loadDocuments();
    loadStorageStatus();

    // Keep dashboard stats/files fresh even if backend starts after frontend.
    const intervalId = setInterval(() => {
      loadDocuments();
      loadStorageStatus();
    }, 10000);

    return () => clearInterval(intervalId);
  }, []);

  const handleUpload = async () => {
    if (!files.length) return;

    if (storageStatus?.minio?.enabled && !storageStatus?.can_upload) {
      const errorMsg = `MinIO is enabled but not connected (${storageStatus?.minio?.endpoint || "unknown endpoint"}). Start MinIO and try again.`;
      setUploadError(errorMsg);
      toast.error(errorMsg);
      return;
    }

    setUploading(true);
    setUploadError("");
    const uploadToast = toast.loading(`Uploading ${files.length} file(s)...`);
    
    try {
      const data = await uploadFiles(files);
      setUploadResult(data);
      setFiles([]);
      await loadDocuments();
      toast.success(
        `Successfully indexed ${data.processed_files} file(s) with ${data.total_chunks || 0} chunks!`,
        { id: uploadToast }
      );
    } catch (error) {
      const errorMsg = error?.response?.data?.detail || "Upload failed";
      setUploadError(errorMsg);
      toast.error(errorMsg, { id: uploadToast });
    } finally {
      setUploading(false);
    }
  };

  const handleAsk = async () => {
    if (!question.trim()) return;

    const userQuestion = question.trim();
    setQuestion("");
    setAskError("");
    setAskLoading(true);
    setChatHistory((prev) => [...prev, { role: "user", text: userQuestion }]);
    toast.loading("Processing your question...", { id: "query" });

    try {
      const asksBroadList = /(\ball\b|\blist\b|\bnames of all\b|\bwhich all\b)/i.test(userQuestion);
      const topK = asksBroadList ? 20 : 6;
      const data = await askQuestion(userQuestion, topK, selectedFile);
      setChatHistory((prev) => [...prev, { role: "assistant", text: data.answer }]);
      setRetrievedChunks(data.retrieved_chunks || []);
      toast.success("Answer ready!", { id: "query" });
    } catch (error) {
      const message = error?.response?.data?.detail || "Query failed";
      setAskError(message);
      setChatHistory((prev) => [...prev, { role: "assistant", text: "I don't know based on the uploaded data." }]);
      toast.error(message, { id: "query" });
    } finally {
      setAskLoading(false);
    }
  };

  const handleDeleteDocument = async (_documentId, fileName) => {
    if (!fileName) return;

    const confirmed = window.confirm(`Delete ${fileName} from MongoDB and MinIO?`);
    if (!confirmed) return;

    setDeletingDocumentId(fileName);
    setUploadError("");
    const deleteToast = toast.loading(`Deleting ${fileName}...`);
    
    try {
      await deleteDocumentsByName(fileName);
      if (selectedFile === fileName) {
        setSelectedFile("__all__");
      }
      await loadDocuments();
      toast.success(`Successfully deleted ${fileName}`, { id: deleteToast });
    } catch (error) {
      const errorMsg = error?.response?.data?.detail || "Delete failed";
      setUploadError(errorMsg);
      toast.error(errorMsg, { id: deleteToast });
    } finally {
      setDeletingDocumentId("");
    }
  };

  const handleLogin = (data) => {
    setIsAuthenticated(true);
    setUsername(data.username);
  };

  const handleLogout = async () => {
    const token = localStorage.getItem("access_token");
    
    if (token) {
      try {
        const apiUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
        await fetch(`${apiUrl}/auth/logout`, {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${token}`,
          },
        });
      } catch (error) {
        console.error("Logout error:", error);
      }
    }
    
    // Clear local storage
    localStorage.removeItem("access_token");
    localStorage.removeItem("username");
    
    // Reset state
    setIsAuthenticated(false);
    setUsername("");
    
    toast.success("Logged out successfully");
    navigate("/login");
  };

  // Protected Route wrapper
  const ProtectedRoute = ({ children }) => {
    // Show nothing while checking auth status
    if (isAuthenticated === null) {
      return <div className="flex min-h-screen items-center justify-center">Loading...</div>;
    }
    
    if (!isAuthenticated) {
      return <Navigate to="/login" replace />;
    }
    return children;
  };

  return (
    <Routes>
      <Route path="/login" element={<Login onLogin={handleLogin} />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Dashboard
              files={files}
              onPickFiles={setFiles}
              onUpload={handleUpload}
              uploading={uploading}
              uploadResult={uploadResult}
              uploadError={uploadError}
              storageStatus={storageStatus}
              question={question}
              setQuestion={setQuestion}
              onAsk={handleAsk}
              askLoading={askLoading}
              askError={askError}
              chatHistory={chatHistory}
              retrievedChunks={retrievedChunks}
              documents={documents}
              selectedFile={selectedFile}
              setSelectedFile={setSelectedFile}
              deletingDocumentId={deletingDocumentId}
              onDeleteDocument={handleDeleteDocument}
              username={username}
              onLogout={handleLogout}
            />
          </ProtectedRoute>
        }
      />
      <Route
        path="/data-dashboard"
        element={
          <ProtectedRoute>
            <DataDashboard
              documents={documents}
              onRefresh={loadDocuments}
              username={username}
              onLogout={handleLogout}
            />
          </ProtectedRoute>
        }
      />
      <Route
        path="/analytics-dashboard"
        element={
          <ProtectedRoute>
            <AnalyticsDashboard
              documents={documents}
              onRefresh={loadDocuments}
              username={username}
              onLogout={handleLogout}
            />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
