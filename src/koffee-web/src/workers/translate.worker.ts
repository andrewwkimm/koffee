export interface TranslationSingle {
  translation_text: string;
}

export type TranslationOutput = TranslationSingle[];

export const toTranslatedText = (output: TranslationOutput): string =>
  output[0].translation_text;