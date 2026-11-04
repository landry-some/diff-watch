"""Run the watched command once and capture what it printed."""

import os
import re
import signal
import subprocess
from dataclasses import dataclass
from datetime import datetime

# CSI sequences (colours, cursor moves), OSC sequences (titles, links) and
# two-byte escapes. v0.1 strips them so they can't move the cursor around
# our screen; passing colours through is on the roadmap.
_ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[@-Z\\-_]")


# What `timeout(1)` exits with when it has to stop the command.
TIMEOUT_EXIT = 124


@dataclass(frozen=True)
class Run:
    output: str
    exit_code: int
    started: datetime
    timed_out: bool = False

    @property
    def status(self) -> str:
        return "timed out" if self.timed_out else f"exit {self.exit_code}"

    @property
    def lines(self) -> list[str]:
        """Output split into lines, without an empty one for the final newline."""
        return self.output.removesuffix("\n").split("\n") if self.output else []


def clean(text: str) -> str:
    """Drop escape sequences and carriage returns, and expand tabs to spaces.

    Tabs are expanded to 8-column stops so a highlighted or clipped line keeps
    its columns lined up: one tab is one character to the diff but several on
    screen.
    """
    text = _ANSI.sub("", text).replace("\r\n", "\n").replace("\r", "")
    return text.expandtabs(8)


def run_command(command: list[str], use_shell: bool = True, timeout: float | None = None) -> Run:
    """Run the command, merging stderr into stdout like a terminal would.

    With use_shell the words are joined with spaces and given to `sh -c`, so
    pipes and globs work. Without it they are run as they are.

    With a timeout the command gets its own process group, so that when time
    runs out everything it started is killed, not only the shell. The output
    printed until then is kept and the run gets exit code 124.
    """
    started = datetime.now()
    argv = ["sh", "-c", " ".join(command)] if use_shell else command
    try:
        proc = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=timeout is not None,
        )
    except OSError as exc:
        return Run(f"dwatch: cannot run {command[0]}: {exc.strerror}\n", 127, started)
    timed_out = False
    try:
        raw, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_group(proc)
        raw, _ = proc.communicate()
    except BaseException:
        # Ctrl-C or SIGTERM: don't leave the command running. A separate
        # process group doesn't get the terminal's SIGINT, so kill all of it.
        if timeout is not None:
            _kill_group(proc)
        else:
            proc.kill()
        proc.wait()
        raise
    output = clean(raw.decode("utf-8", errors="replace"))
    if timed_out:
        return Run(output, TIMEOUT_EXIT, started, timed_out=True)
    return Run(output, proc.returncode, started)


def _kill_group(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
