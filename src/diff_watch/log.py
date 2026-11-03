"""Append each change in the output to a log file as a unified diff."""

from difflib import unified_diff

from .runner import Run


def entry(command: str, old: Run | None, new: Run) -> str:
    """One log entry: a title line, then the diff from the old output to the new.

    The first run has nothing to compare with, so its whole output is logged as
    added lines. That gives the log a starting point to read the diffs against.
    """
    title = f"=== {new.started:%Y-%m-%d %H:%M:%S} | exit {new.exit_code} | {command}"
    old_lines = old.lines if old else []
    old_name = f"{old.started:%H:%M:%S}" if old else "(start)"
    lines = unified_diff(old_lines, new.lines, old_name, f"{new.started:%H:%M:%S}", lineterm="")
    return "\n".join([title, *lines]) + "\n\n"
