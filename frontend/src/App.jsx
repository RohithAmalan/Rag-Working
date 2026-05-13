import { useEffect, useState } from "react";

import Dashboard from "./pages/Dashboard";
import { askQuestion, fetchDocuments, uploadFiles } from "./services/api";

export default function App() {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [uploadError, setUploadError] = useState("");

  const [question, setQuestion] = useState("");
  const [askLoading, setAskLoading] = useState(false);
  const [askError, setAskError] = useState("");
  const [chatHistory, setChatHistory] = useState([]);
  const [retrievedChunks, setRetrievedChunks] = useState([]);

  const [documents, setDocuments] = useState({
    total_chunks: 0,
    primary_chunks: 0,
    secondary_chunks: 0,
    documents: [],
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

  useEffect(() => {
    loadDocuments();

    // Keep dashboard stats/files fresh even if backend starts after frontend.
    const intervalId = setInterval(() => {
      loadDocuments();
    }, 10000);

    return () => clearInterval(intervalId);
  }, []);

  const handleUpload = async () => {
    if (!files.length) return;
    setUploading(true);
    setUploadError("");
    try {
      const data = await uploadFiles(files);
      setUploadResult(data);
      setFiles([]);
      await loadDocuments();
    } catch (error) {
      setUploadError(error?.response?.data?.detail || "Upload failed");
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

    try {
      const data = await askQuestion(userQuestion, 6);
      setChatHistory((prev) => [...prev, { role: "assistant", text: data.answer }]);
      setRetrievedChunks(data.retrieved_chunks || []);
    } catch (error) {
      const message = error?.response?.data?.detail || "Query failed";
      setAskError(message);
      setChatHistory((prev) => [...prev, { role: "assistant", text: "I don't know based on the uploaded data." }]);
    } finally {
      setAskLoading(false);
    }
  };

  return (
    <Dashboard
      files={files}
      onPickFiles={setFiles}
      onUpload={handleUpload}
      uploading={uploading}
      uploadResult={uploadResult}
      uploadError={uploadError}
      question={question}
      setQuestion={setQuestion}
      onAsk={handleAsk}
      askLoading={askLoading}
      askError={askError}
      chatHistory={chatHistory}
      retrievedChunks={retrievedChunks}
      documents={documents}
    />
  );
}
