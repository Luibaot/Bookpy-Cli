import json

from bookpy_cli.config import load_config
from bookpy_cli.models import DEFAULT_PROVIDER_NAMES


def test_load_config_migrates_existing_provider_list(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("bookpy_cli.config.config_dir", lambda: tmp_path)
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"enabled_providers": ["gutenberg", "open_library", "local"]}))
    config = load_config()
    assert config.config_version == 3
    assert config.enabled_providers == DEFAULT_PROVIDER_NAMES
