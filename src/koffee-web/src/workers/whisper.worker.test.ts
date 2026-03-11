import { describe, it, expect } from "vitest";
import { toSegments } from "./whisper.worker";

interface WhisperChunk {
  text: string;
  timestamp: [number, number];
}

describe("toSegments", () => {
  it("maps whisper chunks to segments with correct text and timestamps", () => {
    const chunks: WhisperChunk[] = [
      { text: "Hello world", timestamp: [0, 2.5] },
      { text: "How are you", timestamp: [2.5, 5.0] },
    ];

    expect(toSegments(chunks)).toEqual([
      { text: "Hello world", start: 0, end: 2.5 },
      { text: "How are you", start: 2.5, end: 5.0 },
    ]);
  });

  it("returns empty array for empty chunks", () => {
    expect(toSegments([])).toEqual([]);
  });

  it("preserves order of chunks", () => {
    const chunks: WhisperChunk[] = [
      { text: "Third", timestamp: [4.0, 6.0] },
      { text: "First", timestamp: [0.0, 2.0] },
      { text: "Second", timestamp: [2.0, 4.0] },
    ];

    const result = toSegments(chunks);

    expect(result[0].text).toBe("Third");
    expect(result[1].text).toBe("First");
    expect(result[2].text).toBe("Second");
  });

  it("handles a single chunk", () => {
    const chunks: WhisperChunk[] = [
      { text: "Only segment", timestamp: [0, 3.0] },
    ];

    expect(toSegments(chunks)).toEqual([
      { text: "Only segment", start: 0, end: 3.0 },
    ]);
  });
});
