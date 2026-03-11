from codex_autoloop.model_catalog import get_preset


def test_get_preset_cheap() -> None:
    preset = get_preset("cheap")
    assert preset is not None
    assert preset.main_model == "gpt-5-mini"
    assert preset.reviewer_model == "gpt-5-nano"


def test_get_preset_unknown() -> None:
    assert get_preset("does-not-exist") is None
