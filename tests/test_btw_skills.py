from pathlib import Path

from codex_autoloop.btw_skills import load_btw_file_return_skill_config, resolve_btw_skill_result


def test_load_btw_file_return_skill_config() -> None:
    config = load_btw_file_return_skill_config()
    assert config.name == "btw-file-return"
    assert ".png" in config.image_extensions
    assert "效果图" in config.image_request_keywords


def test_resolve_btw_skill_result_finds_image(tmp_path: Path) -> None:
    assets = tmp_path / "assets"
    assets.mkdir()
    image = assets / "preview_effect.png"
    image.write_bytes(b"png")
    result = resolve_btw_skill_result(
        working_dir=str(tmp_path),
        question="我要看看效果图",
    )
    assert result.is_file_request is True
    assert result.attachments
    assert result.attachments[0].path.endswith("preview_effect.png")


def test_resolve_btw_skill_result_finds_repo_image_fixture() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    fixture = repo_root / "tests" / "assets" / "argusbot-preview.png"
    assert fixture.exists()
    result = resolve_btw_skill_result(
        working_dir=str(repo_root),
        question="show me image files",
    )
    assert result.is_file_request is True
    assert result.attachments
    assert any(item.path.endswith("argusbot-preview.png") for item in result.attachments)
