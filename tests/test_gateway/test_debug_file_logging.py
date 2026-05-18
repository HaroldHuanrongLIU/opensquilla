from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from opensquilla.gateway.boot import _setup_file_logging
from opensquilla.gateway.config import GatewayConfig


def _remove_debug_handlers() -> None:
    root = logging.getLogger()
    for handler in list(root.handlers):
        if getattr(handler, "_opensquilla_debug_file_handler", False):
            root.removeHandler(handler)
            handler.close()


def test_setup_file_logging_uses_rotation_without_forcing_root_debug(tmp_path, monkeypatch) -> None:
    _remove_debug_handlers()
    root = logging.getLogger()
    opensquilla_logger = logging.getLogger("opensquilla")
    original_root_level = root.level
    original_opensquilla_level = opensquilla_logger.level
    monkeypatch.setenv("OPENSQUILLA_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("OPENSQUILLA_LOG_LEVEL", "INFO")

    try:
        _setup_file_logging(
            GatewayConfig(
                log_level="DEBUG",
                log_file_max_bytes=4096,
                log_file_backup_count=2,
            )
        )

        handlers = [
            handler
            for handler in root.handlers
            if getattr(handler, "_opensquilla_debug_file_handler", False)
        ]
        assert len(handlers) == 1
        handler = handlers[0]
        assert isinstance(handler, RotatingFileHandler)
        assert handler.level == logging.INFO
        assert handler.maxBytes == 4096
        assert handler.backupCount == 2
        assert getattr(handler, "baseFilename").endswith("debug.log")
        assert root.level == original_root_level
        assert opensquilla_logger.level == logging.INFO
    finally:
        _remove_debug_handlers()
        root.setLevel(original_root_level)
        opensquilla_logger.setLevel(original_opensquilla_level)


def test_setup_file_logging_can_be_disabled(tmp_path, monkeypatch) -> None:
    _remove_debug_handlers()
    opensquilla_logger = logging.getLogger("opensquilla")
    original_opensquilla_level = opensquilla_logger.level
    monkeypatch.setenv("OPENSQUILLA_LOG_DIR", str(tmp_path))
    monkeypatch.delenv("OPENSQUILLA_LOG_FILE_ENABLED", raising=False)
    monkeypatch.delenv("OPENSQUILLA_LOG_LEVEL", raising=False)

    _setup_file_logging(GatewayConfig(log_file_enabled=False))
    assert not (tmp_path / "debug.log").exists()

    _setup_file_logging(GatewayConfig(log_level="INFO"))
    assert opensquilla_logger.level == logging.INFO
    assert (tmp_path / "debug.log").exists()
    _setup_file_logging(GatewayConfig(log_file_enabled=False))

    handlers = [
        handler
        for handler in logging.getLogger().handlers
        if getattr(handler, "_opensquilla_debug_file_handler", False)
    ]
    assert handlers == []
    assert opensquilla_logger.level == original_opensquilla_level
