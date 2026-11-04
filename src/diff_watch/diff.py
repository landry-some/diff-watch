"""Mark which parts of the new output differ from the old output."""

import re
from difflib import SequenceMatcher

from .render import StyledLine

# Below this similarity a changed line is highlighted as a whole: a
# character diff of two unrelated lines is mostly noise.
MIN_RATIO = 0.5


def _merge(segments: list[tuple[str, bool]]) -> StyledLine:
    out: StyledLine = []
    for text, hl in segments:
        if not text:
            continue
        if out and out[-1][1] == hl:
            out[-1] = (out[-1][0] + text, hl)
        else:
            out.append((text, hl))
    return out


def diff_line(old: str, new: str) -> StyledLine:
    """Highlight the characters of `new` that are not in `old`."""
    if old == new:
        return _merge([(new, False)])
    matcher = SequenceMatcher(None, old, new, autojunk=False)
    if matcher.ratio() < MIN_RATIO:
        return _merge([(new, True)])
    segments = []
    for tag, _, _, j1, j2 in matcher.get_opcodes():
        # 'delete' has an empty slice of `new`, so it adds nothing.
        segments.append((new[j1:j2], tag != "equal"))
    return _merge(segments)


def mask(text: str, ignore: re.Pattern[str] | None) -> str:
    """Remove the parts of `text` that `ignore` matches, for comparing.

    The pattern is applied line by line, the same way highlighting sees it.
    """
    if ignore is None:
        return text
    return "\n".join(ignore.sub("", line) for line in text.split("\n"))


def _unmark(line: StyledLine, ignore: re.Pattern[str]) -> StyledLine:
    """Clear the highlight on the parts of a line that `ignore` matches."""
    text = "".join(piece for piece, _ in line)
    flags = [hl for piece, hl in line for _ in piece]
    for match in ignore.finditer(text):
        flags[match.start() : match.end()] = [False] * (match.end() - match.start())
    return _merge([(char, hl) for char, hl in zip(text, flags)])


def highlight(old: list[str], new: list[str], ignore: re.Pattern[str] | None = None) -> list[StyledLine]:
    """Style every line of `new`: unchanged, partly changed or new.

    Lines are matched first, so an inserted line doesn't make every line
    below it look changed. Lines replaced one-for-one get a character diff.
    Removed lines are not shown, as in `watch -d`.

    With `ignore`, lines are matched with the parts it matches removed, and
    those parts are never highlighted.
    """
    styled: list[StyledLine] = []
    matcher = SequenceMatcher(
        None, [mask(line, ignore) for line in old], [mask(line, ignore) for line in new], autojunk=False
    )
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        for k, line in enumerate(new[j1:j2]):
            if tag == "equal":
                styled.append(_merge([(line, False)]))
                continue
            if tag == "replace" and i1 + k < i2:
                result = diff_line(old[i1 + k], line)
            else:
                result = _merge([(line, True)])
            styled.append(_unmark(result, ignore) if ignore else result)
    return styled
