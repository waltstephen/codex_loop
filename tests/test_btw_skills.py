from pathlib import Path

import pytest

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


# --- Tests for false-positive prevention ---


@pytest.mark.parametrize(
    "question",
    [
        "帮我看看这个函数怎么用",
        "show me how the loop works",
        "can you explain the readme structure",
        "open a discussion about the design",
        "看看这段代码有什么问题",
        "what does this .py module do",
        "tell me about the .md format",
    ],
)
def test_normal_questions_not_treated_as_file_request(tmp_path: Path, question: str) -> None:
    """Normal questions should NOT be detected as file requests."""
    readme = tmp_path / "README.md"
    readme.write_text("# hello")
    result = resolve_btw_skill_result(working_dir=str(tmp_path), question=question)
    assert result.is_file_request is False


def test_explicit_file_request_still_works(tmp_path: Path) -> None:
    """Explicit file name in question should still trigger file request."""
    config_file = tmp_path / "config.json"
    config_file.write_text("{}")
    result = resolve_btw_skill_result(
        working_dir=str(tmp_path),
        question="send me config.json",
    )
    assert result.is_file_request is True
    assert result.attachments
    assert result.attachments[0].path.endswith("config.json")


def test_explicit_readme_request_returns_readme(tmp_path: Path) -> None:
    """Asking for README.md explicitly should return it with priority boost."""
    readme = tmp_path / "README.md"
    readme.write_text("# project")
    other = tmp_path / "notes.md"
    other.write_text("notes")
    result = resolve_btw_skill_result(
        working_dir=str(tmp_path),
        question="发我 README.md",
    )
    assert result.is_file_request is True
    assert result.attachments
    assert result.attachments[0].path.endswith("README.md")


def test_readme_not_returned_for_generic_file_keyword(tmp_path: Path) -> None:
    """Generic file keyword should not return README when user didn't ask for it."""
    readme = tmp_path / "README.md"
    readme.write_text("# project")
    result = resolve_btw_skill_result(
        working_dir=str(tmp_path),
        question="给我文件",
    )
    # Even if is_file_request is True, README should not get priority boost
    if result.attachments:
        for att in result.attachments:
            assert "README priority" not in att.reason


def test_image_request_still_works(tmp_path: Path) -> None:
    """Image requests via imageRequestKeywords should still work."""
    assets = tmp_path / "assets"
    assets.mkdir()
    img = assets / "demo.png"
    img.write_bytes(b"png")
    result = resolve_btw_skill_result(
        working_dir=str(tmp_path),
        question="我要看看效果图",
    )
    assert result.is_file_request is True
    assert result.attachments
