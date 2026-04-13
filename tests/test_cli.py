"""Tests for retryctl.cli."""

import pytest
from unittest.mock import patch, MagicMock

from retryctl.cli import build_parser, main
from retryctl.runner import CommandResult


class TestBuildParser:
    def test_defaults(self):
        parser = build_parser()
        args = parser.parse_args(["echo", "hello"])
        assert args.max_attempts == 3
        assert args.delay == 1.0
        assert args.strategy == "fixed"
        assert args.verbose is False

    def test_custom_flags(self):
        parser = build_parser()
        args = parser.parse_args(["-n", "5", "-s", "exponential", "-d", "2.0", "mycommand"])
        assert args.max_attempts == 5
        assert args.strategy == "exponential"
        assert args.delay == 2.0

    def test_invalid_strategy(self):
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["-s", "invalid_strategy", "cmd"])


class TestMain:
    def _make_result(self, returncode=0, stdout="", stderr="", attempts=1):
        return CommandResult(returncode=returncode, stdout=stdout, stderr=stderr, attempts=attempts)

    def test_exits_with_zero_on_success(self):
        with patch("sys.argv", ["retryctl", "echo", "hi"]):
            with patch("retryctl.cli.run_command", return_value=self._make_result(0, stdout="hi\n")):
                with pytest.raises(SystemExit) as exc:
                    main()
        assert exc.value.code == 0

    def test_exits_with_nonzero_on_failure(self):
        with patch("sys.argv", ["retryctl", "false"]):
            with patch("retryctl.cli.run_command", return_value=self._make_result(1)):
                with pytest.raises(SystemExit) as exc:
                    main()
        assert exc.value.code == 1

    def test_no_command_exits_with_error(self):
        with patch("sys.argv", ["retryctl"]):
            with pytest.raises(SystemExit) as exc:
                main()
        assert exc.value.code != 0

    def test_passes_config_correctly(self):
        with patch("sys.argv", ["retryctl", "-n", "5", "-s", "linear", "mycommand"]):
            with patch("retryctl.cli.run_command", return_value=self._make_result(0)) as mock_run:
                with pytest.raises(SystemExit):
                    main()
        config = mock_run.call_args[0][1]
        assert config.max_attempts == 5
        assert config.backoff_strategy == "linear"
