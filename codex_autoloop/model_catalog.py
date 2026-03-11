from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ModelPreset:
    name: str
    main_model: str
    reviewer_model: str
    note: str


@dataclass(frozen=True)
class ModelEntry:
    model: str
    category: str
    note: str


MODEL_ENTRIES: list[ModelEntry] = [
    ModelEntry("gpt-5.2-codex", "codex", "Strongest current coding-focused model."),
    ModelEntry("gpt-5.1-codex", "codex", "Balanced coding model."),
    ModelEntry("gpt-5.1-codex-max", "codex", "Long-running high-cost coding model."),
    ModelEntry("gpt-5-codex", "codex", "Previous coding-focused model."),
    ModelEntry("gpt-5.2", "general", "Frontier general model, strong but expensive."),
    ModelEntry("gpt-5.1", "general", "Strong general reasoning model."),
    ModelEntry("gpt-5", "general", "Previous GPT-5 generation."),
    ModelEntry("gpt-5-mini", "cheap", "Good lower-cost model for well-defined tasks."),
    ModelEntry("gpt-5-nano", "cheap", "Cheapest fast model; good for reviewer/status roles."),
]


MODEL_PRESETS: list[ModelPreset] = [
    ModelPreset(
        name="balanced",
        main_model="gpt-5.1-codex",
        reviewer_model="gpt-5-mini",
        note="Balanced quality/cost for most coding loops.",
    ),
    ModelPreset(
        name="cheap",
        main_model="gpt-5-mini",
        reviewer_model="gpt-5-nano",
        note="Lowest-cost useful pairing for long loops.",
    ),
    ModelPreset(
        name="strong",
        main_model="gpt-5.2-codex",
        reviewer_model="gpt-5-mini",
        note="Stronger coding quality while keeping reviewer cost lower.",
    ),
    ModelPreset(
        name="max",
        main_model="gpt-5.1-codex-max",
        reviewer_model="gpt-5-mini",
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
            f"- {preset.name}: main={preset.main_model}, reviewer={preset.reviewer_model} "
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
