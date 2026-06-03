import { describe, it, expect } from "vitest";
import {
  normalizeSourceType,
  isSupportedRagDocument,
  getFilteredRagDocuments,
  dedupeByFileName,
} from "./ragDocuments";

describe("ragDocuments utility functions", () => {
  describe("normalizeSourceType", () => {
    it("should normalize valid types correctly", () => {
      expect(normalizeSourceType("csv")).toBe("csv");
      expect(normalizeSourceType(" CSV ")).toBe("csv");
      expect(normalizeSourceType("pdf")).toBe("pdf");
    });

    it("should handle aliases correctly", () => {
      expect(normalizeSourceType("xls")).toBe("excel");
      expect(normalizeSourceType("xlsx")).toBe("excel");
    });

    it("should infer type from filename if value is empty", () => {
      expect(normalizeSourceType("", "data.csv")).toBe("csv");
      expect(normalizeSourceType(null, "report.pdf")).toBe("pdf");
      expect(normalizeSourceType(undefined, "sheet.xlsx")).toBe("excel");
    });

    it("should return raw type if not empty but unrecognized", () => {
      expect(normalizeSourceType("word")).toBe("word");
    });
  });

  describe("isSupportedRagDocument", () => {
    it("should return true for supported documents", () => {
      expect(isSupportedRagDocument({ file_name: "test.csv", source_type: "csv" })).toBe(true);
      expect(isSupportedRagDocument({ filename: "data.pdf", file_type: "pdf" })).toBe(true);
      expect(isSupportedRagDocument({ file_name: "sheet.xlsx", source_type: "excel" })).toBe(true);
    });

    it("should return false for unsupported documents", () => {
      expect(isSupportedRagDocument({ file_name: "test.txt", source_type: "text" })).toBe(false);
      expect(isSupportedRagDocument({ file_name: "image.png" })).toBe(false);
      expect(isSupportedRagDocument(null)).toBe(false);
    });
  });

  describe("getFilteredRagDocuments", () => {
    it("should filter out unsupported documents and map fields", () => {
      const rawDocs = [
        { file_name: "valid.csv", source_type: "csv" },
        { filename: "invalid.txt", file_type: "text" },
        { file_name: "valid2.pdf", source_type: "pdf" },
      ];

      const result = getFilteredRagDocuments(rawDocs);
      expect(result).toHaveLength(2);
      expect(result.map(d => d.file_name)).toEqual(["valid.csv", "valid2.pdf"]);
    });

    it("should sort by priority (csv > excel > pdf)", () => {
      const rawDocs = [
        { file_name: "z_file.pdf", source_type: "pdf" },
        { file_name: "a_file.csv", source_type: "csv" },
        { file_name: "m_file.xlsx", source_type: "excel" },
      ];

      const result = getFilteredRagDocuments(rawDocs);
      expect(result.map(d => d.source_type)).toEqual(["csv", "excel", "pdf"]);
      expect(result.map(d => d.file_name)).toEqual(["a_file.csv", "m_file.xlsx", "z_file.pdf"]);
    });

    it("should handle empty or invalid arrays", () => {
      expect(getFilteredRagDocuments([])).toEqual([]);
      expect(getFilteredRagDocuments(null)).toEqual([]);
    });
  });

  describe("dedupeByFileName", () => {
    it("should remove duplicates based on file_name", () => {
      const docs = [
        { file_name: "test.csv", value: 1 },
        { file_name: "other.pdf", value: 2 },
        { file_name: "test.csv", value: 3 }, // duplicate filename
      ];

      const result = dedupeByFileName(docs);
      expect(result).toHaveLength(2);
      expect(result.map(d => d.file_name)).toEqual(["test.csv", "other.pdf"]);
      // It should keep the last occurrence based on the Map behavior in the implementation
      expect(result.find(d => d.file_name === "test.csv")?.value).toBe(3);
    });

    it("should handle empty or null inputs", () => {
      expect(dedupeByFileName([])).toEqual([]);
      expect(dedupeByFileName(null)).toEqual([]);
    });
  });
});
