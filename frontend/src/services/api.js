import axios from "axios";
import { API_CONFIG, STORAGE_KEYS } from "../config/constants";
import keycloak from "../keycloak";

const API_CANDIDATE_PORTS = [8000, 8001, 8002];
const RESOLVE_TIMEOUT_MS = 1500;

let resolvedBaseURL = API_CONFIG.baseURL || "";
let resolvingBaseURLPromise = null;

function buildCandidateBaseUrls() {
  const candidates = [];

  if (API_CONFIG.baseURL) {
    candidates.push(API_CONFIG.baseURL);
  }

  if (typeof window !== "undefined") {
    const protocol = window.location.protocol;
    const hostname = window.location.hostname || "localhost";
    API_CANDIDATE_PORTS.forEach((port) => {
      candidates.push(`${protocol}//${hostname}:${port}`);
    });
  }

  return [...new Set(candidates.filter(Boolean))];
}

async function isHealthyApi(baseUrl) {
  if (typeof fetch === "undefined") {
    return true;
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), RESOLVE_TIMEOUT_MS);

  try {
    const response = await fetch(`${baseUrl}/health`, {
      method: "GET",
      signal: controller.signal,
    });
    return response.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(timeoutId);
  }
}

async function resolveApiBaseUrl() {
  if (resolvingBaseURLPromise) {
    return resolvingBaseURLPromise;
  }

  resolvingBaseURLPromise = (async () => {
    if (resolvedBaseURL && (await isHealthyApi(resolvedBaseURL))) {
      return resolvedBaseURL;
    }

    const candidates = buildCandidateBaseUrls();
    for (const candidate of candidates) {
      if (await isHealthyApi(candidate)) {
        resolvedBaseURL = candidate;
        return resolvedBaseURL;
      }
    }

    resolvedBaseURL = candidates[0] || "http://localhost:8000";
    return resolvedBaseURL;
  })();

  try {
    return await resolvingBaseURLPromise;
  } finally {
    resolvingBaseURLPromise = null;
  }
}

const api = axios.create({
  baseURL: API_CONFIG.baseURL,
  timeout: API_CONFIG.timeout,
});

// Add auth token to all requests
api.interceptors.request.use(
  async (config) => {
    config.baseURL = await resolveApiBaseUrl();

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

// Handle 401 (token expired/invalid) — clear stale token and redirect to login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      // Clear stale credentials from storage
      localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
      localStorage.removeItem(STORAGE_KEYS.USERNAME);
      localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
      localStorage.removeItem(STORAGE_KEYS.USER_ROLES);
      // Redirect to login — session has expired or backend was restarted
      window.location.href = "/login";
    }
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
