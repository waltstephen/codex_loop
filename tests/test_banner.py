import io
import re

from codex_autoloop import banner


class _TtyStream(io.StringIO):
    def isatty(self) -> bool:
        return True


class _PipeStream(io.StringIO):
    def isatty(self) -> bool:
        return False


def test_should_print_banner_only_for_init_subcommand(monkeypatch) -> None:
    monkeypatch.delenv("ARGUSBOT_BANNER", raising=False)
    stream = _TtyStream()

    assert banner.should_print_banner(subcommand="init", stream=stream) is True
    assert banner.should_print_banner(subcommand=None, stream=stream) is False
    assert banner.should_print_banner(subcommand="status", stream=stream) is False


def test_should_print_banner_respects_force_flag_for_init(monkeypatch) -> None:
    monkeypatch.setenv("ARGUSBOT_BANNER", "force")
    stream = _PipeStream()

    assert banner.should_print_banner(subcommand="init", stream=stream) is True
    assert banner.should_print_banner(subcommand="status", stream=stream) is False


def test_select_banner_lines_chooses_large_when_terminal_is_wide(monkeypatch) -> None:
    monkeypatch.setenv("ARGUSBOT_BANNER_COLUMNS", "120")
    lines = banner.select_banner_lines(stream=_TtyStream())
    assert lines == banner._BANNER_LARGE_LINES


def test_select_banner_lines_chooses_medium_when_terminal_is_mid(monkeypatch) -> None:
    monkeypatch.setenv("ARGUSBOT_BANNER_COLUMNS", "56")
    lines = banner.select_banner_lines(stream=_TtyStream())
    assert lines == banner._BANNER_MEDIUM_LINES


def test_select_banner_lines_chooses_small_when_terminal_is_narrow(monkeypatch) -> None:
    monkeypatch.setenv("ARGUSBOT_BANNER_COLUMNS", "20")
    lines = banner.select_banner_lines(stream=_TtyStream())
    assert lines == banner._BANNER_SMALL_LINES


def test_print_banner_trims_lines_to_terminal_columns(monkeypatch) -> None:
    monkeypatch.setenv("ARGUSBOT_BANNER_COLUMNS", "8")
    stream = _TtyStream()
    banner.print_banner(stream=stream, use_color=False)
    output_lines = [line for line in stream.getvalue().splitlines() if line]
    assert output_lines
    assert all(len(line) <= 8 for line in output_lines)


def test_print_banner_trims_lines_with_color(monkeypatch) -> None:
    monkeypatch.setenv("ARGUSBOT_BANNER_COLUMNS", "8")
    stream = _TtyStream()
    banner.print_banner(stream=stream, use_color=True)
    output_lines = [line for line in stream.getvalue().splitlines() if line]
    assert output_lines
    ansi = re.compile(r"\x1b\[[0-9;]*m")
    plain_lines = [ansi.sub("", line) for line in output_lines]
    assert all(len(line) <= 8 for line in plain_lines)
