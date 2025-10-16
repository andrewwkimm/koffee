"""Text translator for koffee."""

import logging

from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

logging.getLogger("transformers").setLevel(logging.ERROR)
log = logging.getLogger(__name__)


def translate_transcript(transcript: dict, target_language: str) -> list:
    """Gets a translated JSON file."""
    log.info("Translating transcript.")
    log.debug("target_language: " + repr(target_language))

    source_language = transcript["language"]
    log.debug("source_language: " + repr(source_language))

    for i in range(len(transcript["segments"])):
        text = transcript["segments"][i]["text"]
        translated_text = translate_text(text, source_language, target_language)
        transcript["segments"][i]["text"] = translated_text

    translated_transcript = transcript["segments"]
    log.debug(repr(translated_transcript))
    return translated_transcript


def translate_text(text: str, source_language: str, target_language: str) -> str:
    """Translates source language to target language."""
    model_name = "facebook/nllb-200-distilled-600M"

    languages = {
        "ko": "kor_Hang",
        "ja": "jpn_Jpan",
        "en": "eng_Latn",
        "es": "spa_Latn",
        "fr": "fra_Latn",
        "de": "deu_Latn",
        "zh": "zho_Hans",
    }

    source_language_code = languages.get(source_language, source_language)
    target_language_code = languages.get(target_language, target_language)

    tokenizer = AutoTokenizer.from_pretrained(model_name, src_lang=source_language_code)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

    tokenized_text = tokenizer(text, return_tensors="pt")
    translation = model.generate(
        **tokenized_text,
        forced_bos_token_id=tokenizer.convert_tokens_to_ids(target_language_code),
    )

    translated_text = tokenizer.decode(translation[0], skip_special_tokens=True)
    return translated_text
