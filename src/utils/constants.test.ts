import { describe, it, expect } from "vitest";
import {
  PLUGIN_NAME,
  DEFAULT_TRANSFER_PORT,
  YOUTUBE_CATEGORIES,
  PRIVACY_OPTIONS,
  RESOLUTION_OPTIONS,
  BITRATE_OPTIONS,
  FRAMERATE_OPTIONS,
} from "./constants";

describe("constants", () => {
  it("has correct plugin name", () => {
    expect(PLUGIN_NAME).toBe("DeckCast");
  });

  it("has a valid default transfer port", () => {
    expect(DEFAULT_TRANSFER_PORT).toBe(8420);
    expect(DEFAULT_TRANSFER_PORT).toBeGreaterThan(1023);
    expect(DEFAULT_TRANSFER_PORT).toBeLessThanOrEqual(65535);
  });
});

describe("YOUTUBE_CATEGORIES", () => {
  it("includes Gaming category", () => {
    expect(YOUTUBE_CATEGORIES["20"]).toBe("Gaming");
  });

  it("has string keys and values", () => {
    Object.entries(YOUTUBE_CATEGORIES).forEach(([key, val]) => {
      expect(typeof key).toBe("string");
      expect(typeof val).toBe("string");
      expect(val.length).toBeGreaterThan(0);
    });
  });

  it("has reasonable number of categories", () => {
    const count = Object.keys(YOUTUBE_CATEGORIES).length;
    expect(count).toBeGreaterThan(5);
    expect(count).toBeLessThan(50);
  });
});

describe("PRIVACY_OPTIONS", () => {
  it("has three options", () => {
    expect(PRIVACY_OPTIONS).toHaveLength(3);
  });

  it("includes public, unlisted, private", () => {
    const values = PRIVACY_OPTIONS.map((o) => o.value);
    expect(values).toContain("public");
    expect(values).toContain("unlisted");
    expect(values).toContain("private");
  });

  it("each option has label and value", () => {
    PRIVACY_OPTIONS.forEach((opt) => {
      expect(opt.label).toBeTruthy();
      expect(opt.value).toBeTruthy();
    });
  });
});

describe("RESOLUTION_OPTIONS", () => {
  it("includes 720p", () => {
    const labels = RESOLUTION_OPTIONS.map((o) => o.label);
    expect(labels).toContain("720p");
  });

  it("values are WxH format", () => {
    RESOLUTION_OPTIONS.forEach((opt) => {
      expect(opt.value).toMatch(/^\d+x\d+$/);
    });
  });
});

describe("BITRATE_OPTIONS", () => {
  it("values end with k", () => {
    BITRATE_OPTIONS.forEach((opt) => {
      expect(opt.value).toMatch(/^\d+k$/);
    });
  });
});

describe("FRAMERATE_OPTIONS", () => {
  it("includes 30 fps", () => {
    const values = FRAMERATE_OPTIONS.map((o) => o.value);
    expect(values).toContain(30);
  });

  it("values are numbers", () => {
    FRAMERATE_OPTIONS.forEach((opt) => {
      expect(typeof opt.value).toBe("number");
      expect(opt.value).toBeGreaterThan(0);
    });
  });
});
