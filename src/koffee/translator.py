"""Text translator for koffee."""

import logging

from transformers import MarianMTModel, MarianTokenizer


log = logging.getLogger(__name__)


def translate_transcript(transcript: dict) -> list:
    """Gets a translated JSON file."""
    log.info("Translating transcript.")
    language = transcript["language"]
    for i in range(len(transcript["segments"])):
        text = transcript["segments"][i]["text"]
        translated_text = translate_text(text, language)
        transcript["segments"][i]["text"] = translated_text

    translated_transcript = transcript["segments"]
    return translated_transcript


def translate_text(text: str, language: str) -> str:
    """Translates source language to target language."""
    model_name = f"Helsinki-NLP/opus-mt-{language}-en"
    model = MarianMTModel.from_pretrained(model_name)

    tokenizer = MarianTokenizer.from_pretrained(model_name)
    tokenized_text = tokenizer([text], return_tensors="pt")

    translation = model.generate(**tokenized_text)

    translated_text = tokenizer.decode(translation[0], skip_special_tokens=True)
    return translated_text
