import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
  timeout: 60000,
});

export const uploadFiles = async (files) => {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  const { data } = await api.post("/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
};

export const askQuestion = async (question, topK = 6) => {
  const { data } = await api.post("/query", { question, top_k: topK });
  return data;
};

export const fetchDocuments = async () => {
  const { data } = await api.get("/documents");
  return data;
};

export default api;
