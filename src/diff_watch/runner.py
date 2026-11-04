"""Run the watched command once and capture what it printed."""

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime

# CSI sequences (colours, cursor moves), OSC sequences (titles, links) and
# two-byte escapes. v0.1 strips them so they can't move the cursor around
# our screen; passing colours through is on the roadmap.
_ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[@-Z\\-_]")


@dataclass(frozen=True)
class Run:
    output: str
    exit_code: int
    started: datetime

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


def run_command(command: list[str], use_shell: bool = True) -> Run:
    """Run the command, merging stderr into stdout like a terminal would.

    With use_shell the words are joined with spaces and given to `sh -c`, so
    pipes and globs work. Without it they are run as they are.
    """
    started = datetime.now()
    argv = ["sh", "-c", " ".join(command)] if use_shell else command
    try:
        proc = subprocess.run(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except OSError as exc:
        return Run(f"dwatch: cannot run {command[0]}: {exc.strerror}\n", 127, started)
    output = proc.stdout.decode("utf-8", errors="replace")
    return Run(clean(output), proc.returncode, started)
