from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ModelPreset:
    name: str
    main_model: str
    main_reasoning_effort: str
    reviewer_model: str
    reviewer_reasoning_effort: str
    note: str


@dataclass(frozen=True)
class ModelEntry:
    model: str
    category: str
    note: str


MODEL_ENTRIES: list[ModelEntry] = [
    ModelEntry("gpt-5.4", "general", "Current strongest general model available in local Codex cache."),
    ModelEntry("gpt-5.3-codex", "codex", "Current strongest codex-optimized model in local cache."),
    ModelEntry("gpt-5.2-codex", "codex", "Previous codex-optimized model."),
    ModelEntry("gpt-5.1-codex", "codex", "Balanced codex model."),
    ModelEntry("gpt-5.1-codex-max", "codex", "Long-running high-cost coding model."),
    ModelEntry("gpt-5-codex", "codex", "Older codex-optimized model."),
    ModelEntry("gpt-5.1-codex-mini", "cheap", "Cheaper codex-focused model."),
    ModelEntry("gpt-5-codex-mini", "cheap", "Older cheaper codex-focused model."),
]


DEFAULT_MODEL_PRESET = "codex-xhigh"


MODEL_PRESETS: list[ModelPreset] = [
    ModelPreset(
        name="quality",
        main_model="gpt-5.4",
        main_reasoning_effort="high",
        reviewer_model="gpt-5.4",
        reviewer_reasoning_effort="high",
        note="Highest-quality default with high reasoning for both agents.",
    ),
    ModelPreset(
        name="codex52-xhigh",
        main_model="gpt-5.2-codex",
        main_reasoning_effort="xhigh",
        reviewer_model="gpt-5.2-codex",
        reviewer_reasoning_effort="xhigh",
        note="Codex 5.2 with maximum reasoning for both agents.",
    ),
    ModelPreset(
        name="quality-xhigh",
        main_model="gpt-5.4",
        main_reasoning_effort="xhigh",
        reviewer_model="gpt-5.4",
        reviewer_reasoning_effort="xhigh",
        note="Highest-quality preset with maximum reasoning on both agents.",
    ),
    ModelPreset(
        name="balanced",
        main_model="gpt-5.3-codex",
        main_reasoning_effort="high",
        reviewer_model="gpt-5.1-codex",
        reviewer_reasoning_effort="medium",
        note="Strong coding quality with cheaper reviewer.",
    ),
    ModelPreset(
        name="codex-xhigh",
        main_model="gpt-5.3-codex",
        main_reasoning_effort="xhigh",
        reviewer_model="gpt-5.3-codex",
        reviewer_reasoning_effort="xhigh",
        note="Pure codex-focused preset with maximum reasoning on both agents.",
    ),
    ModelPreset(
        name="cheap",
        main_model="gpt-5.1-codex-mini",
        main_reasoning_effort="medium",
        reviewer_model="gpt-5-codex-mini",
        reviewer_reasoning_effort="low",
        note="Lower-cost pairing for long background loops.",
    ),
    ModelPreset(
        name="max",
        main_model="gpt-5.1-codex-max",
        main_reasoning_effort="xhigh",
        reviewer_model="gpt-5.3-codex",
        reviewer_reasoning_effort="high",
        note="Most expensive long-horizon pairing.",
    ),
]


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="codex-autoloop-models",
        description="List supported model presets and common model names for codex-autoloop.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args()

    if args.json:
        payload = {
            "models": [asdict(item) for item in MODEL_ENTRIES],
            "presets": [asdict(item) for item in MODEL_PRESETS],
        }
        print(json.dumps(payload, ensure_ascii=True, indent=2))
        return

    print("Model presets:")
    for preset in MODEL_PRESETS:
        print(
            f"- {preset.name}: main={preset.main_model}/{preset.main_reasoning_effort}, "
            f"reviewer={preset.reviewer_model}/{preset.reviewer_reasoning_effort} "
            f"({preset.note})"
        )
    print("")
    print("Common model names:")
    for item in MODEL_ENTRIES:
        print(f"- {item.model}: [{item.category}] {item.note}")


def get_preset(name: str) -> ModelPreset | None:
    normalized = name.strip().lower()
    for preset in MODEL_PRESETS:
        if preset.name == normalized:
            return preset
    return None


if __name__ == "__main__":
    main()
