"""Tests for shared/api_logging.py — decorators and file logging."""

from __future__ import annotations

import logging

import pytest

from shared.api_logging import log_api_call, log_service_call


class _FakeRepo:
    """Minimal class to test logging decorators."""

    @log_api_call
    def get_items(self, year: int) -> list[dict]:
        return [{"name": "item1"}, {"name": "item2"}]

    @log_api_call
    def get_failing(self, key: int) -> list[dict]:
        raise ValueError("test error")

    @log_service_call
    def compute_stuff(self, data: list) -> dict:
        return {"result": len(data)}

    @log_service_call
    def compute_failing(self) -> None:
        raise RuntimeError("service error")


@pytest.fixture
def fake_repo():
    return _FakeRepo()


@pytest.fixture(autouse=True)
def _reset_logger_and_paths(tmp_path):
    """Reset the module-level logger and redirect log output to tmp_path."""
    import shared.api_logging as mod

    old_logger = mod._logger
    old_dir = mod._LOG_DIR
    old_file = mod._LOG_FILE

    # Clear the cached logger from Python's logging manager
    named_logger = logging.getLogger("f1_dashboard.api")
    named_logger.handlers.clear()

    mod._logger = None
    mod._LOG_DIR = str(tmp_path)
    mod._LOG_FILE = str(tmp_path / "api_calls.log")

    yield tmp_path

    # Close file handlers to release file locks (important on Windows)
    if mod._logger is not None:
        for h in mod._logger.handlers[:]:
            h.close()
            mod._logger.removeHandler(h)
    for h in named_logger.handlers[:]:
        h.close()
        named_logger.removeHandler(h)
    mod._logger = old_logger
    mod._LOG_DIR = old_dir
    mod._LOG_FILE = old_file


class TestLogApiCall:
    def test_returns_result(self, fake_repo, _reset_logger_and_paths):
        result = fake_repo.get_items(2024)
        assert result == [{"name": "item1"}, {"name": "item2"}]

    def test_logs_call_and_ok(self, fake_repo, _reset_logger_and_paths):
        fake_repo.get_items(2024)
        log_file = _reset_logger_and_paths / "api_calls.log"
        content = log_file.read_text()
        assert "CALL: _FakeRepo.get_items(2024)" in content
        assert "OK: _FakeRepo.get_items(2024) -> 2 items" in content

    def test_logs_failure(self, fake_repo, _reset_logger_and_paths):
        with pytest.raises(ValueError, match="test error"):
            fake_repo.get_failing(123)
        log_file = _reset_logger_and_paths / "api_calls.log"
        content = log_file.read_text()
        assert "FAIL: _FakeRepo.get_failing(123)" in content
        assert "ValueError" in content

    def test_preserves_function_name(self, fake_repo):
        assert fake_repo.get_items.__name__ == "get_items"


class TestLogServiceCall:
    def test_returns_result(self, fake_repo, _reset_logger_and_paths):
        result = fake_repo.compute_stuff([1, 2, 3])
        assert result == {"result": 3}

    def test_logs_service_call(self, fake_repo, _reset_logger_and_paths):
        fake_repo.compute_stuff([1, 2])
        log_file = _reset_logger_and_paths / "api_calls.log"
        content = log_file.read_text()
        assert "SERVICE CALL: _FakeRepo.compute_stuff" in content
        assert "SERVICE OK: _FakeRepo.compute_stuff" in content

    def test_logs_service_failure(self, fake_repo, _reset_logger_and_paths):
        with pytest.raises(RuntimeError, match="service error"):
            fake_repo.compute_failing()
        log_file = _reset_logger_and_paths / "api_calls.log"
        content = log_file.read_text()
        assert "SERVICE FAIL: _FakeRepo.compute_failing" in content
        assert "RuntimeError" in content

    def test_creates_log_directory(self, tmp_path):
        """Log directory is created on first use."""
        import shared.api_logging as mod

        new_dir = tmp_path / "nested" / "logs"
        mod._LOG_DIR = str(new_dir)
        mod._LOG_FILE = str(new_dir / "api_calls.log")
        mod._logger = None

        named_logger = logging.getLogger("f1_dashboard.api")
        named_logger.handlers.clear()

        repo = _FakeRepo()
        repo.compute_stuff([])

        assert new_dir.exists()
        assert (new_dir / "api_calls.log").exists()
