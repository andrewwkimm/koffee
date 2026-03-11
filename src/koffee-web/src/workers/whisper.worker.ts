import type { Segment, WhisperMessage } from "../lib/types";

export interface WhisperChunk {
  text: string;
  timestamp: [number, number];
}

export const toSegments = (chunks: WhisperChunk[]): Segment[] =>
  chunks.map(({ text, timestamp }) => ({
    text,
    start: timestamp[0],
    end: timestamp[1],
  }));

// Worker plumbing comes in Phase 5 implementation
export type { WhisperMessage };
