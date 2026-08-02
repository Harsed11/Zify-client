import os

import pytest

import vpn_configurator.core.logger as logger


def _fresh_module(monkeypatch, tmp_path):
    monkeypatch.setattr(logger, "LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr(logger, "LOG_PATH", str(tmp_path / "logs" / "app.log"))
    monkeypatch.setattr(logger, "_logger", None)
    logger._logger = None


def test_log_writes_file(monkeypatch, tmp_path):
    _fresh_module(monkeypatch, tmp_path)
    logger.log("hello world", "INFO")
    content = (tmp_path / "logs" / "app.log").read_text(encoding="utf-8")
    assert "hello world" in content
    assert "[INFO]" in content


def test_log_levels_map(monkeypatch, tmp_path):
    _fresh_module(monkeypatch, tmp_path)
    logger.log("debug msg", "DEBUG")
    logger.log("warn msg", "WARN")
    logger.log("err msg", "ERROR")
    content = (tmp_path / "logs" / "app.log").read_text(encoding="utf-8")
    assert "[DEBUG] debug msg" in content
    assert "[WARNING] warn msg" in content
    assert "[ERROR] err msg" in content


def test_log_unknown_level_defaults_to_info(monkeypatch, tmp_path):
    _fresh_module(monkeypatch, tmp_path)
    logger.log("custom tag", "SUB")
    content = (tmp_path / "logs" / "app.log").read_text(encoding="utf-8")
    assert "[INFO] custom tag" in content


def test_rotation_creates_backups(monkeypatch, tmp_path):
    _fresh_module(monkeypatch, tmp_path)
    monkeypatch.setattr(logger, "MAX_BYTES", 300)
    monkeypatch.setattr(logger, "BACKUP_COUNT", 2)
    logger._logger = None
    for i in range(60):
        logger.log(f"line number {i} " * 10, "INFO")
    files = sorted(os.listdir(tmp_path / "logs"))
    assert "app.log" in files
    backups = [f for f in files if f.startswith("app.log.")]
    assert len(backups) >= 1
