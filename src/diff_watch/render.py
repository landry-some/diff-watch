"""Turn a run into one screenful of text with ANSI escapes."""

from .runner import Run

# A line is a list of (text, highlighted) segments.
Segment = tuple[str, bool]
StyledLine = list[Segment]

HOME = "\x1b[H"
CLEAR_LINE_END = "\x1b[K"
CLEAR_BELOW = "\x1b[J"
REVERSE = "\x1b[7m"
RESET = "\x1b[0m"


def plain(lines: list[str]) -> list[StyledLine]:
    return [[(line, False)] for line in lines]


def header(command: str, interval: float, run: Run, changes: int, width: int) -> str:
    """Left: interval and command. Right: exit code, change count and time.

    The command is cut short first if the two sides don't fit together.
    """
    left = f"Every {interval:g}s: {command}"
    right = f"exit {run.exit_code} | {changes} changes | {run.started:%H:%M:%S}"
    room = width - len(right) - 1
    if room < 1:
        return right[:width]
    if len(left) > room:
        left = left[:room] if room <= 3 else left[: room - 3] + "..."
    return left.ljust(room) + " " + right


def clip(line: StyledLine, width: int) -> StyledLine:
    """Keep at most `width` characters of a styled line."""
    out: StyledLine = []
    left = width
    for text, hl in line:
        if left <= 0:
            break
        piece = text[:left]
        if piece:
            out.append((piece, hl))
            left -= len(piece)
    return out


def paint(line: StyledLine, color: bool) -> str:
    if not color:
        return "".join(text for text, _ in line)
    return "".join(f"{REVERSE}{text}{RESET}" if hl else text for text, hl in line)


def frame(top: str, body: list[StyledLine], width: int, height: int, ansi: bool = True) -> str:
    """Build a full redraw: header, blank line, then as much body as fits.

    Lines are overwritten in place and the rest of the screen cleared, which
    flickers less than clearing the whole screen first. With ansi=False (output
    is not a terminal) it returns the header and the whole body as plain text.
    """
    if not ansi:
        return "\n".join([top, ""] + [paint(line, False) for line in body]) + "\n"
    rows = [top[:width], ""]
    for line in body[: max(height - 2, 0)]:
        rows.append(paint(clip(line, width), True))
    return HOME + (CLEAR_LINE_END + "\n").join(rows) + CLEAR_LINE_END + CLEAR_BELOW
