export interface Language {
  code: string;
  label: string;
  modelId: string;
}

// Only includes languages with verified Xenova ONNX-converted MarianMT models
export const SUPPORTED_LANGUAGES: Language[] = [
  { code: "es", label: "Spanish", modelId: "Xenova/opus-mt-es-en" },
  { code: "fr", label: "French", modelId: "Xenova/opus-mt-fr-en" },
  { code: "de", label: "German", modelId: "Xenova/opus-mt-de-en" },
  { code: "zh", label: "Chinese", modelId: "Xenova/opus-mt-zh-en" },
  { code: "ja", label: "Japanese", modelId: "Xenova/opus-mt-ja-en" },
  { code: "ru", label: "Russian", modelId: "Xenova/opus-mt-ru-en" },
  { code: "ar", label: "Arabic", modelId: "Xenova/opus-mt-ar-en" },
  { code: "it", label: "Italian", modelId: "Xenova/opus-mt-it-en" },
  { code: "pt", label: "Portuguese", modelId: "Xenova/opus-mt-pt-en" },
  { code: "ko", label: "Korean", modelId: "Xenova/opus-mt-ko-en" },
];

export const getModelId = (sourceLanguage: string): string | null => {
  const lang = SUPPORTED_LANGUAGES.find((l) => l.code === sourceLanguage);
  return lang?.modelId ?? null;
};
