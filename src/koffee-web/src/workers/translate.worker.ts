import { pipeline, env } from "@huggingface/transformers";
import type {
  Segment,
  TranslatedSegment,
  TranslateMessage,
  TranslateWorkerInbound,
} from "../lib/types";
import { getModelId } from "../lib/languages";

env.allowLocalModels = false;

// --- Types ---

export interface TranslationSingle {
  translation_text: string;
}

export type TranslationOutput = TranslationSingle[];

// --- Pure helpers (exported for testing) ---

export const toTranslatedText = (output: TranslationOutput): string =>
  output[0].translation_text;

// --- Model singleton ---

let translator: Awaited<ReturnType<typeof pipeline>> | null = null;
let loadedModelId: string | null = null;

const loadModel = async (sourceLanguage: string): Promise<void> => {
  const id = getModelId(sourceLanguage);

  if (!id) {
    throw new Error(
      `No translation model available for language: ${sourceLanguage}`,
    );
  }

  if (translator && loadedModelId === id) return;

  translator = await pipeline('translation', id, {device: 'wasm'});
  loadedModelId = id;
};

// --- Worker message handling ---

const post = (msg: TranslateMessage): void => {
  self.postMessage(msg);
};

self.addEventListener(
  "message",
  async (e: MessageEvent<TranslateWorkerInbound>) => {
    const msg = e.data;

    if (msg.type === 'init') {
      try {
        await loadModel(msg.payload.sourceLanguage);
        post({type: 'ready'});
      } catch (err) {
        post({
          type: 'error',
          payload: {
            code: 'MODEL_LOAD_FAILED',
            message: err instanceof Error ? err.message : 'Failed to load translation model',
            fatal: true,
          },
        });
      }
      return;
    }

    if (msg.type === "segment") {
      const segment: Segment = msg.payload;

      if (!translator) {
        post({
          type: "error",
          payload: {
            code: "MODEL_NOT_LOADED",
            message: "Translation model not loaded",
            fatal: true,
          },
        });
        return;
      }

      try {
        const result = (await translator(segment.text)) as TranslationOutput;
        const translated = toTranslatedText(result);

        if (!translated) {
          // Non-fatal — substitute original text and continue
          post({
            type: "error",
            payload: {
              code: "EMPTY_TRANSLATION",
              message: "Empty translation result",
              fatal: false,
            },
          });

          const translatedSegment: TranslatedSegment = {
            original: segment.text,
            translated: segment.text,
            start: segment.start,
            end: segment.end,
          };
          post({ type: "segment", payload: translatedSegment });
          return;
        }

        const translatedSegment: TranslatedSegment = {
          original: segment.text,
          translated,
          start: segment.start,
          end: segment.end,
        };

        post({ type: "segment", payload: translatedSegment });
      } catch (err) {
        // Non-fatal — substitute original text and continue
        post({
          type: "error",
          payload: {
            code: "TRANSLATION_FAILED",
            message: err instanceof Error ? err.message : "Translation failed",
            fatal: false,
          },
        });

        const translatedSegment: TranslatedSegment = {
          original: segment.text,
          translated: segment.text,
          start: segment.start,
          end: segment.end,
        };
        post({ type: "segment", payload: translatedSegment });
      }
      return;
    }
  },
);
