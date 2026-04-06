"""Tests for config file loading."""

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
