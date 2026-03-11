export interface Segment {
  text: string;
  start: number;
  end: number;
}

export interface TranslatedSegment {
  original: string;
  translated: string;
  start: number;
  end: number;
}

export interface TranscriptionResult {
  segments: Segment[];
  language: string;
}

// Worker message types

export type WhisperMessage =
  | {type: 'segment'; payload: Segment}
  | {type: 'done'; payload: {language: string}}
  | {type: 'error'; payload: {code: string; message: string; fatal: boolean}};

export type TranslateMessage =
  | {type: 'segment'; payload: TranslatedSegment}
  | {type: 'done'}
  | {type: 'error'; payload: {code: string; message: string; fatal: boolean}};

// App -> worker init message
export interface TranslateInitPayload {
  sourceLanguage: string;
  targetLanguage: string;
}

export type TranslateWorkerInbound =
  | {type: 'init'; payload: TranslateInitPayload}
  | {type: 'segment'; payload: Segment};