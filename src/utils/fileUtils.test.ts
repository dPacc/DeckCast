import { describe, it, expect } from "vitest";
import { formatFileSize, formatDuration, formatDate, generateTitle } from "./fileUtils";

describe("formatFileSize", () => {
  it("formats bytes", () => {
    expect(formatFileSize(500)).toBe("500 B");
  });

  it("formats kilobytes", () => {
    expect(formatFileSize(1024)).toBe("1.0 KB");
    expect(formatFileSize(2560)).toBe("2.5 KB");
  });

  it("formats megabytes", () => {
    expect(formatFileSize(1048576)).toBe("1.0 MB");
    expect(formatFileSize(5 * 1024 * 1024)).toBe("5.0 MB");
  });

  it("formats gigabytes", () => {
    expect(formatFileSize(1073741824)).toBe("1.00 GB");
    expect(formatFileSize(2.5 * 1024 * 1024 * 1024)).toBe("2.50 GB");
  });

  it("handles zero", () => {
    expect(formatFileSize(0)).toBe("0 B");
  });
});

describe("formatDuration", () => {
  it("formats seconds only", () => {
    expect(formatDuration(45)).toBe("0:45");
  });

  it("formats minutes and seconds", () => {
    expect(formatDuration(125)).toBe("2:05");
  });

  it("formats hours", () => {
    expect(formatDuration(3661)).toBe("1:01:01");
  });

  it("pads seconds with zero", () => {
    expect(formatDuration(60)).toBe("1:00");
    expect(formatDuration(63)).toBe("1:03");
  });

  it("handles zero", () => {
    expect(formatDuration(0)).toBe("0:00");
  });

  it("handles fractional seconds", () => {
    expect(formatDuration(90.7)).toBe("1:30");
  });
});

describe("formatDate", () => {
  it("returns a string containing year", () => {
    const result = formatDate(1700000000);
    expect(result).toContain("2023");
  });

  it("returns a non-empty string", () => {
    expect(formatDate(0).length).toBeGreaterThan(0);
  });
});

describe("generateTitle", () => {
  it("replaces {game} placeholder", () => {
    expect(generateTitle("{game} clip", "Portal 2")).toBe("Portal 2 clip");
  });

  it("replaces {date} placeholder", () => {
    const result = generateTitle("Clip from {date}", "Test");
    expect(result).toContain("Clip from ");
    expect(result).not.toContain("{date}");
  });

  it("replaces multiple placeholders", () => {
    const result = generateTitle("{game} - {date}", "Hades");
    expect(result).toContain("Hades");
    expect(result).not.toContain("{game}");
    expect(result).not.toContain("{date}");
  });

  it("handles no placeholders", () => {
    expect(generateTitle("Static Title", "Game")).toBe("Static Title");
  });
});
