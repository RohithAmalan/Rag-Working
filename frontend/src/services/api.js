import axios from "axios";
import { API_CONFIG, STORAGE_KEYS } from "../config/constants";
import keycloak from "../keycloak";

const api = axios.create({
  baseURL: API_CONFIG.baseURL,
  timeout: API_CONFIG.timeout,
});

// Add auth token to all requests
api.interceptors.request.use(
  (config) => {
    // Prefer Keycloak in-memory token (if client is using Keycloak SSO in this app).
    // Fallback to stored access token in localStorage for legacy / form-based login flows.
    const kcToken = keycloak?.token;
    const storedToken = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN);
    const token = kcToken || storedToken;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export const uploadFiles = async (files) => {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  const { data } = await api.post("/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 0,
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
