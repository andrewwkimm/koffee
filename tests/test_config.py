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
        'source_language = "ko"\nsubtitle_format = "srt"\nprovider = "gemini"\n'
    )

    file_config = load_config_file(config_path)
    config = KoffeeConfig(**file_config)

    assert config.source_language == "ko"
    assert config.subtitle_format == "srt"
    assert config.provider == "gemini"
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
        KoffeeConfig(whisper_model="nonexistent-model")


def test_valid_whisper_model_is_accepted() -> None:
    """Tests that a known Whisper model is accepted."""
    config = KoffeeConfig(whisper_model="tiny")
    assert config.whisper_model == "tiny"


def test_non_positive_chunk_size_raises() -> None:
    """Tests that a zero or negative chunk_size raises a validation error."""
    with pytest.raises(ValueError, match="Size must be a positive integer"):
        KoffeeConfig(chunk_size=0)
    with pytest.raises(ValueError, match="Size must be a positive integer"):
        KoffeeConfig(chunk_size=-5)


def test_non_positive_context_size_raises() -> None:
    """Tests that a zero or negative context_size raises a validation error."""
    with pytest.raises(ValueError, match="Size must be a positive integer"):
        KoffeeConfig(context_size=0)
    with pytest.raises(ValueError, match="Size must be a positive integer"):
        KoffeeConfig(context_size=-3)


def test_zero_sleep_requests_is_accepted() -> None:
    """Tests that sleep_requests=0 is a valid no-delay setting."""
    config = KoffeeConfig(sleep_requests=0)
    assert config.sleep_requests == 0


def test_negative_sleep_requests_raises() -> None:
    """Tests that a negative sleep_requests raises a validation error."""
    with pytest.raises(ValueError, match="sleep_requests must be non-negative"):
        KoffeeConfig(sleep_requests=-1)


def test_api_key_falls_back_to_google_env_var(monkeypatch) -> None:
    """Tests that api_key falls back to GOOGLE_API_KEY for gemini backend."""
    monkeypatch.setenv("GOOGLE_API_KEY", "env-key-123")
    config = KoffeeConfig(provider="gemini")
    assert config.api_key == "env-key-123"


def test_api_key_falls_back_to_openai_env_var(monkeypatch) -> None:
    """Tests that api_key falls back to OPENAI_API_KEY for chatgpt backend."""
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key-123")
    config = KoffeeConfig(provider="chatgpt")
    assert config.api_key == "openai-key-123"


def test_api_key_falls_back_to_anthropic_env_var(monkeypatch) -> None:
    """Tests that api_key falls back to ANTHROPIC_API_KEY for claude backend."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-key-123")
    config = KoffeeConfig(provider="claude")
    assert config.api_key == "anthropic-key-123"


def test_api_key_not_resolved_for_whisper() -> None:
    """Tests that no env var is checked for the whisper backend."""
    config = KoffeeConfig(provider="whisper")
    assert config.api_key is None


def test_api_key_prefers_explicit_value(monkeypatch) -> None:
    """Tests that an explicit api_key takes precedence over the env var."""
    monkeypatch.setenv("GOOGLE_API_KEY", "env-key-123")
    config = KoffeeConfig(api_key="explicit-key", provider="gemini")
    assert config.api_key == "explicit-key"


def test_api_key_is_none_without_env_var(monkeypatch) -> None:
    """Tests that api_key is None when neither flag nor env var is set."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    config = KoffeeConfig()
    assert config.api_key is None


def test_prompt_defaults_to_none() -> None:
    """Tests that prompt defaults to None."""
    config = KoffeeConfig()
    assert config.prompt is None


def test_prompt_accepts_custom_value() -> None:
    """Tests that prompt accepts a custom string value."""
    custom_prompt = "You are a medical subtitle translator."
    config = KoffeeConfig(prompt=custom_prompt)
    assert config.prompt == custom_prompt


def test_prompt_from_config_file(tmp_path) -> None:
    """Tests that prompt can be loaded from a TOML config file."""
    config_path = tmp_path / "koffee.toml"
    config_path.write_text('prompt = "Translate formally."\n')

    file_config = load_config_file(config_path)
    config = KoffeeConfig(**file_config)

    assert config.prompt == "Translate formally."
