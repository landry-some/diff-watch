"""Command-line entry point: parse options and run the watch loop."""

import argparse
import os
import re
import shutil
import signal
import sys
import time
from collections.abc import Callable
from typing import TextIO

from . import __version__
from .diff import highlight, mask
from .log import entry
from .render import frame, header, plain
from .runner import Run, run_command

ALT_SCREEN_ON = "\x1b[?1049h\x1b[?25l"  # switch to the alternate screen, hide cursor
ALT_SCREEN_OFF = "\x1b[?25h\x1b[?1049l"


def positive_float(text: str) -> float:
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {text!r}") from None
    if value <= 0:
        raise argparse.ArgumentTypeError("must be greater than 0")
    return value


def positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a whole number: {text!r}") from None
    if value <= 0:
        raise argparse.ArgumentTypeError("must be greater than 0")
    return value


def regex(text: str) -> re.Pattern[str]:
    try:
        return re.compile(text)
    except re.error as exc:
        raise argparse.ArgumentTypeError(f"bad regex {text!r}: {exc}") from None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dwatch",
        description="Re-run a command on an interval and highlight what changed.",
    )
    parser.add_argument("-n", "--interval", type=positive_float, default=2.0, metavar="SECONDS",
                        help="seconds to wait between runs (default: 2)")
    parser.add_argument("--timeout", type=positive_float, metavar="SECONDS",
                        help="kill the command if a run takes longer than SECONDS")
    parser.add_argument("-x", "--exec", dest="use_shell", action="store_false",
                        help="run the command directly instead of through sh -c")
    parser.add_argument("-c", "--cumulative", action="store_true",
                        help="highlight everything that differs from the first run")
    parser.add_argument("--no-diff", dest="diff", action="store_false",
                        help="don't highlight changes")
    parser.add_argument("-g", "--exit-on-change", action="store_true",
                        help="stop as soon as the output changes")
    parser.add_argument("-e", "--exit-on-error", action="store_true",
                        help="stop when the command exits non-zero, with its exit code")
    parser.add_argument("--count", type=positive_int, metavar="N",
                        help="stop after N runs")
    parser.add_argument("--ignore", type=regex, action="append", default=[], metavar="REGEX",
                        help="leave out text matching REGEX when comparing runs (repeatable)")
    parser.add_argument("--log", metavar="FILE",
                        help="append each change to FILE as a unified diff")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="the command to watch")
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        parser.error("no command given")
    args.ignore = re.compile("|".join(f"(?:{p.pattern})" for p in args.ignore)) if args.ignore else None
    return args


def stop_code(args: argparse.Namespace, current: Run, changed: bool, runs: int) -> int | None:
    """The exit code to stop with after this run, or None to keep going."""
    if args.exit_on_error and current.exit_code != 0:
        return current.exit_code
    if args.exit_on_change and changed:
        return 0
    if args.count is not None and runs >= args.count:
        return 0
    return None


def watch(
    args: argparse.Namespace,
    *,
    run: Callable[..., Run] = run_command,
    sleep: Callable[[float], None] = time.sleep,
    out: TextIO = sys.stdout,
    size: Callable[[], tuple[int, int]] = lambda: tuple(shutil.get_terminal_size()),
    log: TextIO | None = None,
) -> int:
    """Run the command until Ctrl-C or an exit condition, redrawing each time.

    Returns the exit code for dwatch itself. When an exit condition stops it on a
    terminal, the last screen is printed again after leaving the alternate
    screen, so it stays visible in the scrollback.
    """
    command_text = " ".join(args.command)
    tty = out.isatty()
    first: Run | None = None
    previous: Run | None = None
    changes = runs = 0
    last_top, last_body = "", []
    code = None
    if tty:
        out.write(ALT_SCREEN_ON)
    try:
        while code is None:
            current = run(args.command, args.use_shell, timeout=args.timeout)
            runs += 1
            changed = previous is not None and (
                mask(current.output, args.ignore) != mask(previous.output, args.ignore)
            )
            changes += changed
            if log is not None and (previous is None or changed):
                log.write(entry(command_text, previous, current))
                log.flush()
            width, height = size()
            last_top = header(command_text, args.interval, current, changes, width)
            base = first if args.cumulative else previous
            if args.diff and base is not None:
                last_body = highlight(base.lines, current.lines, args.ignore)
            else:
                last_body = plain(current.lines)
            out.write(frame(last_top, last_body, width, height, ansi=tty))
            out.flush()
            previous = current
            first = first or current
            code = stop_code(args, current, changed, runs)
            if code is None:
                sleep(args.interval)
    except KeyboardInterrupt:
        return 0
    finally:
        if tty:
            out.write(ALT_SCREEN_OFF)
            out.flush()
    if tty:
        out.write(frame(last_top, last_body, 0, 0, ansi=False))
        out.flush()
    return code


def _exit_on_sigterm(signum, frame):
    # Raise instead of dying so watch() still leaves the alternate screen.
    raise SystemExit(128 + signum)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    signal.signal(signal.SIGTERM, _exit_on_sigterm)
    log = None
    if args.log is not None:
        try:
            log = open(args.log, "a", encoding="utf-8")
        except OSError as exc:
            print(f"dwatch: cannot open log file {args.log}: {exc.strerror}", file=sys.stderr)
            return 2
    try:
        return watch(args, log=log)
    except BrokenPipeError:
        # The reader went away (e.g. `dwatch ... | head`). Point stdout at
        # /dev/null so Python's final flush doesn't print a second error.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 141  # 128 + SIGPIPE, what a shell reports for this case
    finally:
        if log is not None:
            log.close()


if __name__ == "__main__":
    sys.exit(main())
