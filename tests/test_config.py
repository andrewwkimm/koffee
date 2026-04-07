"""Tests for config file loading."""

import pytest

from koffee.data.config import KoffeeConfig, load_config_file


def test_load_config_file_returns_empty_when_not_found(tmp_path) -> None:
    """Tests that an empty dict is returned when no config file exists."""
    result = load_config_file(tmp_path / "nonexistent.toml")
    assert result == {}


def test_load_config_file_reads_toml(tmp_path) -> None:
    """Tests that a valid TOML file is parsed correctly."""
    config_path = tmp_path / "koffee.toml"
    config_path.write_text('source_language = "ko"\nsubtitle_format = "srt"\n')

    result = load_config_file(config_path)

    assert result["source_language"] == "ko"
    assert result["subtitle_format"] == "srt"


def test_load_config_file_searches_default_paths(tmp_path, monkeypatch) -> None:
    """Tests that load_config_file searches cwd for koffee.toml."""
    config_path = tmp_path / "koffee.toml"
    config_path.write_text('target_language = "fr"\n')
    monkeypatch.setattr("koffee.data.config.CONFIG_SEARCH_PATHS", [config_path])

    result = load_config_file()

    assert result["target_language"] == "fr"


def test_config_file_values_apply_to_koffee_config(tmp_path) -> None:
    """Tests that config file values override KoffeeConfig defaults."""
    config_path = tmp_path / "koffee.toml"
    config_path.write_text(
        'source_language = "ko"\n'
        'subtitle_format = "srt"\n'
        'translation_backend = "gemini"\n'
    )

    file_config = load_config_file(config_path)
    config = KoffeeConfig(**file_config)

    assert config.source_language == "ko"
    assert config.subtitle_format == "srt"
    assert config.translation_backend == "gemini"
    # Defaults should still apply for unset fields
    assert config.target_language == "en"
    assert config.device == "auto"


def test_invalid_language_code_raises() -> None:
    """Tests that an invalid language code raises a validation error."""
    with pytest.raises(ValueError, match="Unsupported language code"):
        KoffeeConfig(target_language="enn")


def test_invalid_source_language_code_raises() -> None:
    """Tests that an invalid source language code raises a validation error."""
    with pytest.raises(ValueError, match="Unsupported language code"):
        KoffeeConfig(source_language="xyz")


def test_auto_source_language_is_accepted() -> None:
    """Tests that 'auto' is a valid source language."""
    config = KoffeeConfig(source_language="auto")
    assert config.source_language == "auto"


def test_invalid_model_raises() -> None:
    """Tests that an unknown Whisper model raises a validation error."""
    with pytest.raises(ValueError, match="Unknown Whisper model"):
        KoffeeConfig(model="nonexistent-model")


def test_valid_model_is_accepted() -> None:
    """Tests that a known Whisper model is accepted."""
    config = KoffeeConfig(model="tiny")
    assert config.model == "tiny"


def test_api_key_falls_back_to_env_var(monkeypatch) -> None:
    """Tests that api_key falls back to the GOOGLE_API_KEY environment variable."""
    monkeypatch.setenv("GOOGLE_API_KEY", "env-key-123")
    config = KoffeeConfig()
    assert config.api_key == "env-key-123"


def test_api_key_prefers_explicit_value(monkeypatch) -> None:
    """Tests that an explicit api_key takes precedence over the env var."""
    monkeypatch.setenv("GOOGLE_API_KEY", "env-key-123")
    config = KoffeeConfig(api_key="explicit-key")
    assert config.api_key == "explicit-key"


def test_api_key_is_none_without_env_var(monkeypatch) -> None:
    """Tests that api_key is None when neither flag nor env var is set."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    config = KoffeeConfig()
    assert config.api_key is None


def test_translation_prompt_defaults_to_none() -> None:
    """Tests that translation_prompt defaults to None."""
    config = KoffeeConfig()
    assert config.translation_prompt is None


def test_translation_prompt_accepts_custom_value() -> None:
    """Tests that translation_prompt accepts a custom string value."""
    custom_prompt = "You are a medical subtitle translator."
    config = KoffeeConfig(translation_prompt=custom_prompt)
    assert config.translation_prompt == custom_prompt


def test_translation_prompt_from_config_file(tmp_path) -> None:
    """Tests that translation_prompt can be loaded from a TOML config file."""
    config_path = tmp_path / "koffee.toml"
    config_path.write_text('translation_prompt = "Translate formally."\n')

    file_config = load_config_file(config_path)
    config = KoffeeConfig(**file_config)

    assert config.translation_prompt == "Translate formally."
