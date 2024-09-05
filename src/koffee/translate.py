"""Text translator for koffee."""

from transformers import MarianMTModel, MarianTokenizer


def translate_transcription(transcription: dict) -> list:
    """Gets a translated JSON file."""
    language = transcription["language"]
    for i in range(len(transcription["segments"])):
        text = transcription["segments"][i]["text"]
        translated_text = translate_text(text, language)
        transcription["segments"][i]["text"] = translated_text

    translated_transcription = transcription["segments"]
    return translated_transcription


def translate_text(text: str, language: str) -> str:
    """Translates source language to target language."""
    model_name = f"Helsinki-NLP/opus-mt-{language}-en"
    model = MarianMTModel.from_pretrained(model_name)

    tokenizer = MarianTokenizer.from_pretrained(model_name)
    tokenized_text = tokenizer.prepare_seq2seq_batch([text], return_tensors="pt")

    translation = model.generate(**tokenized_text)
    translated_text = tokenizer.decode(translation[0], skip_special_tokens=True)
    return translated_text
