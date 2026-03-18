from pathlib import Path

import pytest

from codex_autoloop import copilot_proxy


def test_codex_config_overrides_include_copilot_provider() -> None:
    config = copilot_proxy.CopilotProxyConfig(
        enabled=True,
        proxy_dir="/tmp/copilot-proxy",
        port=19090,
    )
    args = copilot_proxy.codex_config_overrides(config)
    assert args == [
        "-c",
        'model_provider="copilot"',
        "-c",
        'model_providers.copilot.name="GitHub Copilot"',
        "-c",
        'model_providers.copilot.base_url="http://127.0.0.1:19090/v1"',
        "-c",
        'model_providers.copilot.wire_api="responses"',
        "-c",
        "model_providers.copilot.requires_openai_auth=false",
    ]


def test_resolve_proxy_dir_accepts_explicit_checkout(tmp_path: Path) -> None:
    proxy_dir = tmp_path / "copilot-proxy"
    proxy_dir.mkdir()
    (proxy_dir / "proxy.mjs").write_text("// test", encoding="utf-8")
    assert copilot_proxy.resolve_proxy_dir(str(proxy_dir)) == proxy_dir.resolve()


def test_resolve_proxy_dir_detects_managed_checkout(monkeypatch, tmp_path: Path) -> None:
    managed_dir = tmp_path / ".argusbot" / "tools" / "copilot-proxy"
    managed_dir.mkdir(parents=True)
    (managed_dir / "proxy.mjs").write_text("// test", encoding="utf-8")
    monkeypatch.setattr(copilot_proxy.Path, "home", lambda: tmp_path)
    assert copilot_proxy.resolve_proxy_dir() == managed_dir.resolve()


def test_bootstrap_proxy_checkout_clones_and_runs_setup(monkeypatch, tmp_path: Path) -> None:
    target_dir = tmp_path / ".argusbot" / "tools" / "copilot-proxy"
    calls: list[tuple[list[str], str | None]] = []

    def fake_run(cmd, cwd=None, check=None):
        calls.append((cmd, cwd))
        if cmd[0] == "/usr/bin/git":
            target_dir.mkdir(parents=True, exist_ok=True)
            (target_dir / "proxy.mjs").write_text("// proxy", encoding="utf-8")
            (target_dir / "setup.mjs").write_text("// setup", encoding="utf-8")
        return object()

    monkeypatch.setattr(copilot_proxy.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(copilot_proxy.subprocess, "run", fake_run)

    resolved = copilot_proxy.bootstrap_proxy_checkout(target_dir=target_dir)

    assert resolved == target_dir.resolve()
    assert calls == [
        (
            [
                "/usr/bin/git",
                "clone",
                copilot_proxy.DEFAULT_COPILOT_PROXY_REPO_URL,
                str(target_dir.resolve()),
            ],
            None,
        ),
        (
            [
                "/usr/bin/node",
                str((target_dir / "setup.mjs").resolve()),
            ],
            str(target_dir.resolve()),
        ),
    ]


def test_ensure_proxy_running_starts_process_until_healthy(monkeypatch, tmp_path: Path) -> None:
    proxy_dir = tmp_path / "copilot-proxy"
    proxy_dir.mkdir()
    (proxy_dir / "proxy.mjs").write_text("// test", encoding="utf-8")
    config = copilot_proxy.CopilotProxyConfig(enabled=True, proxy_dir=str(proxy_dir), port=18080)

    health_checks = iter([False, False, True])
    started: list[list[str]] = []

    monkeypatch.setattr(copilot_proxy, "proxy_is_healthy", lambda cfg: next(health_checks))
    monkeypatch.setattr(copilot_proxy.shutil, "which", lambda name: "/usr/bin/node")
    monkeypatch.setattr(copilot_proxy.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(
        copilot_proxy.subprocess,
        "Popen",
        lambda cmd, **kwargs: started.append(cmd) or object(),
    )

    copilot_proxy.ensure_proxy_running(config, startup_timeout_seconds=5)

    assert started == [["/usr/bin/node", str(proxy_dir / "proxy.mjs"), "--port", "18080"]]


def test_ensure_proxy_running_raises_when_proxy_dir_missing(monkeypatch) -> None:
    config = copilot_proxy.CopilotProxyConfig(enabled=True, proxy_dir="/missing/proxy", port=18080)
    monkeypatch.setattr(copilot_proxy, "proxy_is_healthy", lambda cfg: False)
    with pytest.raises(RuntimeError):
        copilot_proxy.ensure_proxy_running(config, startup_timeout_seconds=1)


def test_build_codex_runner_skips_proxy_overrides_for_claude_backend() -> None:
    config = copilot_proxy.CopilotProxyConfig(
        enabled=True,
        proxy_dir="/tmp/copilot-proxy",
        port=18080,
    )
    runner = copilot_proxy.build_codex_runner(
        backend="claude",
        runner_bin="claude",
        config=config,
    )
    assert runner.backend == "claude"
    assert runner.codex_bin == "claude"
    assert runner.default_extra_args == []
    assert runner.before_exec is None
