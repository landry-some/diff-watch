"""Command-line entry point: parse options and run the watch loop."""

import argparse
import shutil
import signal
import sys
import time
from collections.abc import Callable
from typing import TextIO

from . import __version__
from .diff import highlight
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dwatch",
        description="Re-run a command on an interval and highlight what changed.",
    )
    parser.add_argument("-n", "--interval", type=positive_float, default=2.0, metavar="SECONDS",
                        help="seconds to wait between runs (default: 2)")
    parser.add_argument("-x", "--exec", dest="use_shell", action="store_false",
                        help="run the command directly instead of through sh -c")
    parser.add_argument("--no-diff", dest="diff", action="store_false",
                        help="don't highlight changes")
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
    return args


def watch(
    args: argparse.Namespace,
    *,
    run: Callable[[list[str], bool], Run] = run_command,
    sleep: Callable[[float], None] = time.sleep,
    out: TextIO = sys.stdout,
    size: Callable[[], tuple[int, int]] = lambda: tuple(shutil.get_terminal_size()),
) -> int:
    """Run the command forever (until Ctrl-C), redrawing after each run."""
    command_text = " ".join(args.command)
    tty = out.isatty()
    previous: Run | None = None
    changes = 0
    if tty:
        out.write(ALT_SCREEN_ON)
    try:
        while True:
            current = run(args.command, args.use_shell)
            if previous is not None and current.output != previous.output:
                changes += 1
            width, height = size()
            top = header(command_text, args.interval, current, changes, width)
            if args.diff and previous is not None:
                body = highlight(previous.lines, current.lines)
            else:
                body = plain(current.lines)
            out.write(frame(top, body, width, height, ansi=tty))
            out.flush()
            previous = current
            sleep(args.interval)
    except KeyboardInterrupt:
        return 0
    finally:
        if tty:
            out.write(ALT_SCREEN_OFF)
            out.flush()


def _exit_on_sigterm(signum, frame):
    # Raise instead of dying so watch() still leaves the alternate screen.
    raise SystemExit(128 + signum)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    signal.signal(signal.SIGTERM, _exit_on_sigterm)
    return watch(args)


if __name__ == "__main__":
    sys.exit(main())
