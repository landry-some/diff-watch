import io
from datetime import datetime

import pytest

from diff_watch.cli import ALT_SCREEN_OFF, ALT_SCREEN_ON, parse_args, watch
from diff_watch.runner import Run


class FakeTTY(io.StringIO):
    def isatty(self):
        return True


def fake_runs(*outputs):
    """A run() stand-in that returns the given outputs in order."""
    calls = []

    def run(command, use_shell):
        calls.append((command, use_shell))
        return Run(outputs[len(calls) - 1], 0, datetime(2026, 1, 1))

    return run, calls


def stop_after(n):
    """A sleep() stand-in that raises Ctrl-C on the n-th call."""
    calls = []

    def sleep(seconds):
        calls.append(seconds)
        if len(calls) >= n:
            raise KeyboardInterrupt

    return sleep, calls


def test_parse_args_defaults_and_command():
    args = parse_args(["ls", "-l"])
    assert args.command == ["ls", "-l"]
    assert args.interval == 2.0
    assert args.use_shell is True


def test_parse_args_options_before_command():
    args = parse_args(["-n", "0.5", "-x", "--", "ls", "-n"])
    assert args.interval == 0.5
    assert args.use_shell is False
    assert args.command == ["ls", "-n"]


@pytest.mark.parametrize("argv", [[], ["-n", "0", "ls"], ["-n", "soon", "ls"]])
def test_parse_args_rejects_bad_input(argv, capsys):
    with pytest.raises(SystemExit) as exc:
        parse_args(argv)
    assert exc.value.code == 2


def test_loop_runs_until_ctrl_c_and_counts_changes():
    run, run_calls = fake_runs("a\n", "a\n", "b\n")
    sleep, sleep_calls = stop_after(3)
    out = io.StringIO()
    code = watch(parse_args(["-n", "1.5", "date"]), run=run, sleep=sleep, out=out, size=lambda: (80, 24))
    assert code == 0
    assert run_calls == [(["date"], True)] * 3
    assert sleep_calls == [1.5] * 3
    text = out.getvalue()
    assert "\x1b" not in text  # not a terminal: no escapes
    assert "0 changes" in text and "1 changes" in text


def test_loop_uses_alternate_screen_on_a_terminal():
    run, _ = fake_runs("hello\n")
    sleep, _ = stop_after(1)
    out = FakeTTY()
    watch(parse_args(["true"]), run=run, sleep=sleep, out=out, size=lambda: (40, 10))
    text = out.getvalue()
    assert text.startswith(ALT_SCREEN_ON)
    assert text.endswith(ALT_SCREEN_OFF)
    assert "hello" in text


def test_loop_highlights_changes_since_previous_run():
    run, _ = fake_runs("used 41%\n", "used 42%\n", "used 42%\n")
    sleep, _ = stop_after(3)
    out = FakeTTY()
    watch(parse_args(["df"]), run=run, sleep=sleep, out=out, size=lambda: (40, 10))
    frames = out.getvalue().split("\x1b[H")[1:]
    assert "\x1b[7m" not in frames[0]  # first run: nothing to compare with
    assert "used 4\x1b[7m2\x1b[0m%" in frames[1]
    assert "\x1b[7m" not in frames[2]  # unchanged since the run before


def test_no_diff_turns_highlighting_off():
    run, _ = fake_runs("a\n", "b\n")
    sleep, _ = stop_after(2)
    out = FakeTTY()
    watch(parse_args(["--no-diff", "x"]), run=run, sleep=sleep, out=out, size=lambda: (40, 10))
    assert "\x1b[7m" not in out.getvalue()
    assert "1 changes" in out.getvalue()


def test_cumulative_compares_with_the_first_run():
    run, _ = fake_runs("a b\n", "a X\n", "a X\n")
    sleep, _ = stop_after(3)
    out = FakeTTY()
    watch(parse_args(["-c", "x"]), run=run, sleep=sleep, out=out, size=lambda: (40, 10))
    frames = out.getvalue().split("\x1b[H")[1:]
    # The third run equals the second, but still differs from the first.
    assert "a \x1b[7mX\x1b[0m" in frames[1]
    assert "a \x1b[7mX\x1b[0m" in frames[2]
    assert "1 changes" in frames[2]
