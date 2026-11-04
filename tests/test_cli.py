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


def run_with_codes(*results):
    """A run() stand-in returning (output, exit_code) pairs in order."""
    calls = []

    def run(command, use_shell):
        calls.append(command)
        output, code = results[len(calls) - 1]
        return Run(output, code, datetime(2026, 1, 1))

    return run, calls


def never_stop():
    return stop_after(10**6)


def test_exit_on_change_stops_after_the_changed_run():
    run, calls = run_with_codes(("a\n", 0), ("a\n", 0), ("b\n", 0), ("c\n", 0))
    sleep, sleeps = never_stop()
    code = watch(parse_args(["-g", "x"]), run=run, sleep=sleep, out=io.StringIO(), size=lambda: (40, 10))
    assert code == 0
    assert len(calls) == 3
    assert len(sleeps) == 2  # no sleep after the last run


def test_exit_on_error_returns_the_command_exit_code():
    run, calls = run_with_codes(("ok\n", 0), ("boom\n", 4), ("ok\n", 0))
    sleep, _ = never_stop()
    code = watch(parse_args(["-e", "x"]), run=run, sleep=sleep, out=io.StringIO(), size=lambda: (40, 10))
    assert code == 4
    assert len(calls) == 2


def test_errors_are_ignored_without_e():
    run, calls = run_with_codes(("boom\n", 4), ("boom\n", 4))
    sleep, _ = never_stop()
    code = watch(parse_args(["--count", "2", "x"]), run=run, sleep=sleep, out=io.StringIO(), size=lambda: (40, 10))
    assert code == 0
    assert len(calls) == 2


def test_count_stops_after_n_runs():
    run, calls = run_with_codes(*[("same\n", 0)] * 5)
    sleep, sleeps = never_stop()
    code = watch(parse_args(["--count", "3", "x"]), run=run, sleep=sleep, out=io.StringIO(), size=lambda: (40, 10))
    assert code == 0
    assert len(calls) == 3 and len(sleeps) == 2


def test_last_screen_is_printed_again_after_leaving_the_alternate_screen():
    run, _ = run_with_codes(("a\n", 0), ("final\n", 0))
    sleep, _ = never_stop()
    out = FakeTTY()
    watch(parse_args(["-g", "x"]), run=run, sleep=sleep, out=out, size=lambda: (40, 10))
    after = out.getvalue().split(ALT_SCREEN_OFF)[1]
    assert after.endswith("\n\nfinal\n")
    assert "\x1b" not in after


@pytest.mark.parametrize("value", ["0", "-1", "two"])
def test_count_must_be_positive(value):
    with pytest.raises(SystemExit):
        parse_args(["--count", value, "x"])


def test_log_gets_the_first_run_and_each_change_only():
    run, _ = run_with_codes(("a\n", 0), ("a\n", 0), ("b\n", 0))
    sleep, _ = never_stop()
    log = io.StringIO()
    watch(parse_args(["--count", "3", "x"]), run=run, sleep=sleep, out=io.StringIO(), size=lambda: (40, 10), log=log)
    entries = log.getvalue().split("\n\n")
    assert entries[-1] == ""
    assert len(entries) == 3  # first run, the change, trailing empty piece
    assert "+a" in entries[0]
    assert "-a" in entries[1] and "+b" in entries[1]


def test_main_writes_the_log_file(tmp_path):
    from diff_watch.cli import main

    path = tmp_path / "changes.log"
    path.write_text("older entry\n")
    assert main(["--count", "1", "--log", str(path), "echo", "hi"]) == 0
    text = path.read_text()
    assert text.startswith("older entry\n===")  # appended, not overwritten
    assert "+hi\n" in text


def test_main_reports_an_unwritable_log(tmp_path, capsys):
    from diff_watch.cli import main

    assert main(["--log", str(tmp_path / "no" / "such" / "dir.log"), "true"]) == 2
    assert "cannot open log file" in capsys.readouterr().err


def test_closed_pipe_exits_quietly():
    import subprocess
    import sys

    proc = subprocess.Popen(
        [sys.executable, "-m", "diff_watch.cli", "-n", "0.05", "seq 1 2000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    proc.stdout.readline()
    proc.stdout.close()  # like `| head -1` exiting
    _, err = proc.communicate(timeout=10)
    assert proc.returncode == 141
    assert err == b""


def test_ignore_leaves_matches_out_of_the_comparison():
    run, calls = run_with_codes(("t=1 ok\n", 0), ("t=2 ok\n", 0), ("t=3 bad\n", 0), ("t=4 x\n", 0))
    sleep, _ = never_stop()
    out = FakeTTY()
    code = watch(parse_args(["-g", "--ignore", r"t=\d+", "x"]), run=run, sleep=sleep, out=out, size=lambda: (40, 10))
    assert code == 0
    assert len(calls) == 3  # the t=2 run didn't count as a change
    frames = out.getvalue().split("\x1b[H")[1:]
    assert "\x1b[7m" not in frames[1]
    assert "\nt=3" in frames[2] and "bad\x1b[0m" in frames[2]  # t=3 itself not highlighted


def test_ignore_can_be_given_more_than_once():
    args = parse_args(["--ignore", r"\d+", "--ignore", "pid", "x"])
    assert args.ignore.sub("", "pid 42 a") == "  a"
    assert parse_args(["x"]).ignore is None


def test_ignore_rejects_a_bad_regex(capsys):
    with pytest.raises(SystemExit) as exc:
        parse_args(["--ignore", "(", "x"])
    assert exc.value.code == 2
    assert "bad regex" in capsys.readouterr().err
