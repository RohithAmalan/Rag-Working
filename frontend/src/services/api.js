import axios from "axios";
import { API_CONFIG } from "../config/constants";

const api = axios.create({
  baseURL: API_CONFIG.baseURL,
  timeout: API_CONFIG.timeout,
});

export const uploadFiles = async (files) => {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  const { data } = await api.post("/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
};

export const askQuestion = async (question, topK = 6, selectedFile = "") => {
  const payload = { question, top_k: topK };
  if (selectedFile && selectedFile !== "__all__") {
    payload.selected_file = selectedFile;
  }
  const { data } = await api.post("/query", payload);
  return data;
};

export const fetchDocuments = async () => {
  const { data } = await api.get("/documents");
  return data;
};

export const fetchStorageStatus = async () => {
  const { data } = await api.get("/storage-status");
  return data;
};

export const deleteDocument = async (documentId) => {
  const { data } = await api.delete(`/documents/${documentId}`);
  return data;
};

export const deleteDocumentsByName = async (fileName) => {
  const { data } = await api.delete(`/documents/by-name/${encodeURIComponent(fileName)}`);
  return data;
};

export const fetchFilePreview = async (fileName, page = 1, pageSize = 100, sheetName = null) => {
  const params = { page, page_size: pageSize };
  if (sheetName) {
    params.sheet_name = sheetName;
  }
  const { data } = await api.get(`/documents/preview/${encodeURIComponent(fileName)}`, { params });
  return data;
};

export const fetchFileAnalytics = async (fileName, sheetName = null) => {
  const params = {};
  if (sheetName) {
    params.sheet_name = sheetName;
  }
  const { data } = await api.get(`/documents/analytics/${encodeURIComponent(fileName)}`, { params });
  return data;
};

export default api;
