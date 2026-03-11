import type { TranslatedSegment, TranslateMessage } from "../lib/types";

export interface TranslationSingle {
  translation_text: string;
}

export type TranslationOutput = TranslationSingle[];

export const toTranslatedText = (output: TranslationOutput): string =>
  output[0].translation_text;

// Worker plumbing comes in Phase 5 implementation
export type { TranslatedSegment, TranslateMessage };
