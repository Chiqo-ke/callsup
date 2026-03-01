from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MODULES = {
    "platform": {
        "service_name": "svc-platform",
        "env_prefix": "CALLSUP_PLATFORM_",
    },
    "audio_engine": {
        "service_name": "svc-audio-engine",
        "env_prefix": "CALLSUP_AUDIO_ENGINE_",
    },
    "intelligence_engine": {
        "service_name": "svc-intelligence-engine",
        "env_prefix": "CALLSUP_INTELLIGENCE_ENGINE_",
    },
    "knowledge_ops": {
        "service_name": "svc-knowledge-ops",
        "env_prefix": "CALLSUP_KNOWLEDGE_OPS_",
    },
}
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
SEMVER_V = re.compile(r"^v\d+\.\d+\.\d+$")


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def main() -> int:
    errors: list[str] = []

    common_path = ROOT / "schemas" / "common.json"
    if not common_path.exists():
        errors.append("Missing shared schema: schemas/common.json")
    else:
        common = _load_json(common_path)
        defs = common.get("definitions", {})
        segment = defs.get("TranscriptSegment", {})
        speaker_enum = (
            segment.get("properties", {})
            .get("speaker", {})
            .get("enum", [])
        )
        required = set(segment.get("required", []))
        expected_required = {
            "business_id",
            "conv_id",
            "segment_id",
            "start_ts",
            "end_ts",
            "text",
        }
        if speaker_enum != ["customer", "agent"]:
            errors.append("schemas/common.json: TranscriptSegment.speaker enum must be [customer, agent]")
        if required != expected_required:
            errors.append(
                "schemas/common.json: TranscriptSegment.required must be exactly "
                "[business_id, conv_id, segment_id, start_ts, end_ts, text]"
            )

    for module, cfg in MODULES.items():
        module_dir = ROOT / module
        openapi_path = module_dir / "openapi.yaml"
        resources_path = module_dir / "resources.json"

        if not openapi_path.exists():
            errors.append(f"{module}: missing openapi.yaml")
            continue
        if not resources_path.exists():
            errors.append(f"{module}: missing resources.json")
            continue

        openapi = _load_yaml(openapi_path)
        resources = _load_json(resources_path)

        openapi_version = str(openapi.get("openapi", ""))
        if not openapi_version.startswith("3.0"):
            errors.append(f"{module}: openapi must be 3.0.x")

        info_version = str(openapi.get("info", {}).get("version", ""))
        if not SEMVER.match(info_version):
            errors.append(f"{module}: info.version must be semantic version without 'v' (e.g. 0.1.0)")

        expected_service_name = cfg["service_name"]
        if resources.get("service_name") != expected_service_name:
            errors.append(f"{module}: resources.service_name must be {expected_service_name}")
        if resources.get("k8s_service_name") != expected_service_name:
            errors.append(f"{module}: resources.k8s_service_name must be {expected_service_name}")
        if resources.get("openapi_path") != "/openapi.yaml":
            errors.append(f"{module}: resources.openapi_path must be /openapi.yaml")

        resources_version = str(resources.get("version", ""))
        if not SEMVER_V.match(resources_version):
            errors.append(f"{module}: resources.version must be semantic with leading 'v' (e.g. v0.1.0)")
        elif info_version and resources_version != f"v{info_version}":
            errors.append(f"{module}: resources.version must equal v + openapi.info.version")

        env_vars = resources.get("env_vars_required")
        if not isinstance(env_vars, list) or not env_vars:
            errors.append(f"{module}: resources.env_vars_required must be a non-empty array")
        else:
            prefix = cfg["env_prefix"]
            invalid_env = [name for name in env_vars if not str(name).startswith(prefix)]
            if invalid_env:
                errors.append(
                    f"{module}: env vars must start with {prefix}. Invalid: {', '.join(map(str, invalid_env))}"
                )

        if module == "audio_engine":
            text = openapi_path.read_text(encoding="utf-8")
            if "../schemas/common.json#/definitions/TranscriptSegment" not in text:
                errors.append(
                    "audio_engine: transcript endpoint must reference ../schemas/common.json#/definitions/TranscriptSegment"
                )

    if errors:
        print("Contract validation failed:\n")
        for item in errors:
            print(f"- {item}")
        return 1

    print("Contract validation passed for all modules.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
