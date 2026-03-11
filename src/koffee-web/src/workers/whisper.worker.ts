import { pipeline, env } from "@huggingface/transformers";
import type { Segment, WhisperMessage } from "../lib/types";

env.allowLocalModels = false;

// TODO: per-chunk streaming not supported in Transformers.js v3 —
// segments are posted after full transcription completes.
// Revisit when upstream adds stable chunk callback support.

const MODEL = "onnx-community/whisper-small";

// --- Types ---

export interface WhisperChunk {
  text: string;
  timestamp: [number, number];
}

interface WhisperOutput {
  text: string;
  chunks: WhisperChunk[];
  language?: string;
}

// --- Pure helpers (exported for testing) ---

export const toSegments = (chunks: WhisperChunk[]): Segment[] =>
  chunks.map(({ text, timestamp }) => ({
    text,
    start: timestamp[0],
    end: timestamp[1],
  }));

// --- Model singleton ---

let transcriber: Awaited<ReturnType<typeof pipeline>> | null = null;

const loadModel = async (): Promise<void> => {
  transcriber = await pipeline(
    'automatic-speech-recognition',
    MODEL,
    {device: 'wasm'},
  );
};

// --- Audio decoding ---

const decodeAudio = async (file: File): Promise<Float32Array> => {
  const arrayBuffer = await file.arrayBuffer();
  // 16kHz required by Whisper
  const audioContext = new AudioContext({ sampleRate: 16000 });
  const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
  // Take first channel — Whisper expects mono
  return audioBuffer.getChannelData(0);
};

// --- Worker message handling ---

const post = (msg: WhisperMessage): void => {
  self.postMessage(msg);
};

self.addEventListener("message", async (e: MessageEvent) => {
  const { type, payload } = e.data;

  if (type !== "start") return;

  try {
    await loadModel();
  } catch (err) {
    post({
      type: "error",
      payload: {
        code: "MODEL_LOAD_FAILED",
        message:
          err instanceof Error ? err.message : "Failed to load Whisper model",
        fatal: true,
      },
    });
    return;
  }

  let audio: Float32Array;

  try {
    audio = await decodeAudio(payload.file);
  } catch (err) {
    post({
      type: "error",
      payload: {
        code: "AUDIO_DECODE_FAILED",
        message: err instanceof Error ? err.message : "Failed to decode audio",
        fatal: true,
      },
    });
    return;
  }

  try {
    const result = (await transcriber!(audio, {
      return_timestamps: true,
      chunk_length_s: 30,
      stride_length_s: 5,
    })) as WhisperOutput;

    const segments = toSegments(result.chunks ?? []);

    for (const segment of segments) {
      post({ type: "segment", payload: segment });
    }

    post({
      type: "done",
      payload: { language: result.language ?? "en" },
    });
  } catch (err) {
    post({
      type: "error",
      payload: {
        code: "TRANSCRIPTION_FAILED",
        message: err instanceof Error ? err.message : "Transcription failed",
        fatal: true,
      },
    });
  }
});
