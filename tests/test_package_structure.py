from __future__ import annotations

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION_DIR = ROOT / "custom_components" / "llm_local_intents"
SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


def test_package_contains_minimal_llm_platform() -> None:
    """The package contains the local-intent runtime and LLM platform."""
    assert INTEGRATION_DIR.is_dir()
    assert (INTEGRATION_DIR / "__init__.py").is_file()
    assert (INTEGRATION_DIR / "const.py").is_file()
    assert (INTEGRATION_DIR / "llm.py").is_file()
    assert (INTEGRATION_DIR / "llm_tools.py").is_file()
    assert (INTEGRATION_DIR / "catalog.py").is_file()
    assert (INTEGRATION_DIR / "intent_adapter.py").is_file()
    assert (INTEGRATION_DIR / "prompt.py").is_file()
    assert (INTEGRATION_DIR / "schema.py").is_file()
    assert (INTEGRATION_DIR / "brand" / "icon.png").is_file()
    assert not (INTEGRATION_DIR / "config_flow.py").exists()
    assert not (INTEGRATION_DIR / "prompts").exists()
    assert not (INTEGRATION_DIR / "translations").exists()

    manifest = json.loads(
        (INTEGRATION_DIR / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["domain"] == "llm_local_intents"
    assert manifest["name"] == "LLM Local Intents"
    assert manifest["config_flow"] is False
    assert manifest["after_dependencies"] == ["intent_script"]
    manifest_keys = list(manifest)
    assert manifest_keys[:2] == ["domain", "name"]
    assert manifest_keys[2:] == sorted(manifest_keys[2:])
    assert SEMVER_PATTERN.fullmatch(manifest["version"])
    assert manifest["version"] == "0.1.0"


def test_release_and_hacs_metadata_match_integration() -> None:
    """Release Please and HACS metadata point to the new integration."""
    manifest = json.loads(
        (INTEGRATION_DIR / "manifest.json").read_text(encoding="utf-8")
    )
    release_manifest = json.loads(
        (ROOT / ".release-please-manifest.json").read_text(encoding="utf-8")
    )
    release_config = json.loads(
        (ROOT / "release-please-config.json").read_text(encoding="utf-8")
    )
    hacs = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))

    assert release_manifest["."] == manifest["version"]
    package_config = release_config["packages"]["."]
    assert {
        extra_file["path"]: extra_file["jsonpath"]
        for extra_file in package_config["extra-files"]
    } == {"custom_components/llm_local_intents/manifest.json": "$.version"}
    assert hacs["name"] == "LLM Local Intents"
