const SUPPORTED_TYPES = new Set(["csv", "excel", "xlsx", "pdf"]);

const TYPE_ALIASES = {
  xls: "excel",
  xlsx: "excel",
};

const TYPE_PRIORITY = {
  csv: 1,
  excel: 2,
  pdf: 3,
};

function typeFromExtension(fileName = "") {
  const lower = String(fileName).toLowerCase();
  if (lower.endsWith(".csv")) return "csv";
  if (lower.endsWith(".xlsx") || lower.endsWith(".xls")) return "excel";
  if (lower.endsWith(".pdf")) return "pdf";
  return "unknown";
}

export function normalizeSourceType(value, fileName = "") {
  const raw = String(value || "").toLowerCase().trim();
  if (!raw) return typeFromExtension(fileName);
  return TYPE_ALIASES[raw] || raw;
}

export function isSupportedRagDocument(doc) {
  const fileName = doc?.file_name || doc?.filename || "";
  const normalizedType = normalizeSourceType(doc?.source_type || doc?.file_type, fileName);
  return SUPPORTED_TYPES.has(normalizedType);
}

export function getFilteredRagDocuments(rawDocuments) {
  const docs = Array.isArray(rawDocuments) ? rawDocuments : [];

  return docs
    .filter((doc) => doc && (doc.file_name || doc.filename))
    .map((doc) => {
      const fileName = doc.file_name || doc.filename;
      const sourceType = normalizeSourceType(doc.source_type || doc.file_type, fileName);
      return {
        ...doc,
        file_name: fileName,
        source_type: sourceType,
      };
    })
    .filter(isSupportedRagDocument)
    .sort((a, b) => {
      const typeDiff = (TYPE_PRIORITY[a.source_type] || 99) - (TYPE_PRIORITY[b.source_type] || 99);
      if (typeDiff !== 0) return typeDiff;
      return a.file_name.localeCompare(b.file_name);
    });
}

export function dedupeByFileName(docs) {
  return Array.from(new Map((docs || []).map((doc) => [doc.file_name, doc])).values());
}
