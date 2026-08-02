from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path

from bookpy_cli.providers.base import Provider


def load_custom_providers(
    specifications: list[str], timeout: float
) -> tuple[list[Provider], list[str]]:
    """Load user-authorized providers declared as ``module_or_file:ClassName``."""

    providers: list[Provider] = []
    errors: list[str] = []
    for specification in specifications:
        try:
            provider = _load_provider(specification, timeout)
        except (AttributeError, ImportError, TypeError, ValueError) as error:
            errors.append(f"{specification}: {error}")
        else:
            providers.append(provider)
    return providers, errors


def _load_provider(specification: str, timeout: float) -> Provider:
    module_reference, separator, class_name = specification.partition(":")
    if not separator or not module_reference or not class_name:
        raise ValueError("use module_or_file:ProviderClass")
    module = _load_module(module_reference)
    factory = getattr(module, class_name)
    provider = factory(timeout=timeout)
    if not isinstance(provider, Provider):
        raise TypeError(f"{class_name} must inherit from bookpy_cli.providers.Provider")
    return provider


def _load_module(reference: str) -> object:
    path = Path(reference).expanduser()
    if path.suffix == ".py" or path.exists():
        if not path.is_file():
            raise ValueError(f"provider file does not exist: {path}")
        module_name = f"bookpy_custom_{path.stem}"
        module_spec = importlib.util.spec_from_file_location(module_name, path)
        if module_spec is None or module_spec.loader is None:
            raise ImportError(f"could not load provider file: {path}")
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        return module
    return importlib.import_module(reference)
