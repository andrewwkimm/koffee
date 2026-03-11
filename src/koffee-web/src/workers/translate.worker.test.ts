import { describe, it, expect } from "vitest";
import { toTranslatedText } from "./translate.worker";

interface TranslationSingle {
  translation_text: string;
}

type TranslationOutput = TranslationSingle[];

describe("toTranslatedText", () => {
  it("extracts translation_text from pipeline output", () => {
    const output: TranslationOutput = [{ translation_text: "Hola mundo" }];

    expect(toTranslatedText(output)).toBe("Hola mundo");
  });

  it("returns the first translation when multiple are present", () => {
    const output: TranslationOutput = [
      { translation_text: "Hola mundo" },
      { translation_text: "Hola mundo alternativo" },
    ];

    expect(toTranslatedText(output)).toBe("Hola mundo");
  });

  it("handles empty translation text", () => {
    const output: TranslationOutput = [{ translation_text: "" }];

    expect(toTranslatedText(output)).toBe("");
  });
});
