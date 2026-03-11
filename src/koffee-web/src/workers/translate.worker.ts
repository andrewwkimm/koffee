import {pipeline, env} from '@huggingface/transformers';
import type {Segment, TranslatedSegment, TranslateMessage, TranslateWorkerInbound} from '../lib/types';
import {getModelId} from '../lib/languages';

env.allowLocalModels = false;

export interface TranslationSingle {
  translation_text: string;
}

export type TranslationOutput = TranslationSingle[];

export const toTranslatedText = (output: TranslationOutput): string =>
  output[0].translation_text;

let translator: Awaited<ReturnType<typeof pipeline>> | null = null;
let loadedModelId: string | null = null;

const loadModel = async (sourceLanguage: string): Promise<void> => {
  const id = getModelId(sourceLanguage);

  if (!id) {
    throw new Error(`No translation model available for language: ${sourceLanguage}`);
  }

  if (translator && loadedModelId === id) return;

  console.log('[translate worker] loading model:', id);
  translator = await pipeline('translation', id, {device: 'wasm'});
  loadedModelId = id;
  console.log('[translate worker] model loaded:', id);
};

const post = (msg: TranslateMessage): void => {
  self.postMessage(msg);
};

// Track in-flight translations and whether done has been requested
let pendingCount = 0;
let doneRequested = false;

const checkDone = (): void => {
  if (doneRequested && pendingCount === 0) {
    console.log('[translate worker] all segments done, posting done');
    post({type: 'done'});
    doneRequested = false;
  }
};

const translateSegment = async (segment: Segment): Promise<void> => {
  pendingCount++;

  if (!translator) {
    post({
      type: 'error',
      payload: {
        code: 'MODEL_NOT_LOADED',
        message: 'Translation model not loaded',
        fatal: true,
      },
    });
    pendingCount--;
    checkDone();
    return;
  }

  try {
    const result = (await translator(segment.text)) as TranslationOutput;
    const translated = toTranslatedText(result);

    if (!translated) {
      post({
        type: 'error',
        payload: {
          code: 'EMPTY_TRANSLATION',
          message: 'Empty translation result',
          fatal: false,
        },
      });
      post({
        type: 'segment',
        payload: {
          original: segment.text,
          translated: segment.text,
          start: segment.start,
          end: segment.end,
        },
      });
    } else {
      post({
        type: 'segment',
        payload: {
          original: segment.text,
          translated,
          start: segment.start,
          end: segment.end,
        },
      });
    }
  } catch (err) {
    console.error('[translate worker] translation failed:', err);
    post({
      type: 'error',
      payload: {
        code: 'TRANSLATION_FAILED',
        message: err instanceof Error ? err.message : 'Translation failed',
        fatal: false,
      },
    });
    post({
      type: 'segment',
      payload: {
        original: segment.text,
        translated: segment.text,
        start: segment.start,
        end: segment.end,
      },
    });
  } finally {
    pendingCount--;
    checkDone();
  }
};

self.addEventListener(
  'message',
  async (e: MessageEvent<TranslateWorkerInbound>) => {
    const msg = e.data;
    console.log('[translate worker] message received:', msg.type);

    if (msg.type === 'init') {
      pendingCount = 0;
      doneRequested = false;
      try {
        await loadModel(msg.payload.sourceLanguage);
        console.log('[translate worker] posting ready');
        post({type: 'ready'});
      } catch (err) {
        console.error('[translate worker] model load failed:', err);
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

    if (msg.type === 'done') {
      console.log('[translate worker] received done, pending:', pendingCount);
      doneRequested = true;
      checkDone();
      return;
    }

    if (msg.type === 'segment') {
      void translateSegment(msg.payload);
      return;
    }
  },
);