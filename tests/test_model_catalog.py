from codex_autoloop.model_catalog import get_preset


def test_get_preset_cheap() -> None:
    preset = get_preset("quality")
    assert preset is not None
    assert preset.main_model == "gpt-5.4"
    assert preset.main_reasoning_effort == "high"
    assert preset.reviewer_model == "gpt-5.4"
    assert preset.reviewer_reasoning_effort == "high"


def test_get_preset_unknown() -> None:
    assert get_preset("does-not-exist") is None
