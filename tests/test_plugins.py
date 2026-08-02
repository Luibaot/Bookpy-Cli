from pathlib import Path

from bookpy_cli.providers.plugins import load_custom_providers


def test_loads_custom_provider_from_file() -> None:
    template = Path("examples/open_catalog_provider.py").resolve()
    providers, errors = load_custom_providers([f"{template}:OpenCatalogProvider"], timeout=5)
    assert not errors
    assert providers[0].name == "my_open_catalog"


def test_reports_invalid_custom_provider_without_crashing() -> None:
    providers, errors = load_custom_providers(["not_a_module:Provider"], timeout=5)
    assert not providers
    assert errors
