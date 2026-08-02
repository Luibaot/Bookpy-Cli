from __future__ import annotations

import json
from pathlib import Path

from platformdirs import user_config_dir, user_data_dir

from bookpy_cli.models import DEFAULT_PROVIDER_NAMES, AppConfig

APP_NAME = "bookpy-cli"


def config_dir() -> Path:
    return Path(user_config_dir(APP_NAME))


def data_dir() -> Path:
    return Path(user_data_dir(APP_NAME))


def config_path() -> Path:
    return config_dir() / "config.json"


def load_config() -> AppConfig:
    path = config_path()
    if not path.exists():
        config_dir().mkdir(parents=True, exist_ok=True)
        config = AppConfig()
        save_config(config)
        return config
    raw = json.loads(path.read_text())
    config = AppConfig.model_validate(raw)
    if raw.get("config_version", 1) < config.config_version:
        config.enabled_providers = list(
            dict.fromkeys([*DEFAULT_PROVIDER_NAMES, *config.enabled_providers])
        )
        save_config(config)
    return config


def save_config(config: AppConfig) -> None:
    config_dir().mkdir(parents=True, exist_ok=True)
    config_path().write_text(json.dumps(config.model_dump(), indent=2) + "\n")
