export interface WhisperChunk {
  text: string;
  timestamp: [number, number];
}

export interface Segment {
  text: string;
  start: number;
  end: number;
}

export interface TranscriptionResult {
  segments: Segment[];
  language: string;
}

export const toSegments = (chunks: WhisperChunk[]): Segment[] =>
  chunks.map(({text, timestamp}) => ({
    text,
    start: timestamp[0],
    end: timestamp[1],
  }));