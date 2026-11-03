from datetime import datetime

from diff_watch.render import CLEAR_BELOW, HOME, REVERSE, RESET, clip, frame, header, paint
from diff_watch.runner import Run

RUN = Run("", 2, datetime(2026, 11, 3, 9, 5, 7))


def test_header_puts_status_on_the_right():
    top = header("df -h", 2.0, RUN, 4, 60)
    assert len(top) == 60
    assert top.startswith("Every 2s: df -h ")
    assert top.endswith("exit 2 | 4 changes | 09:05:07")


def test_header_shortens_a_long_command():
    top = header("x" * 100, 0.5, RUN, 0, 50)
    assert len(top) == 50
    assert top.startswith("Every 0.5s: xxx")
    assert "...  exit" not in top and "... exit 2" in top


def test_header_in_a_tiny_terminal_keeps_the_status():
    assert header("ls", 1, RUN, 0, 10) == "exit 2 | 0"


def test_clip_keeps_highlight_boundaries():
    line = [("ab", False), ("cd", True), ("ef", False)]
    assert clip(line, 3) == [("ab", False), ("c", True)]
    assert clip(line, 0) == []
    assert clip(line, 99) == line


def test_paint_reverses_highlighted_text():
    line = [("a", False), ("b", True)]
    assert paint(line, True) == f"a{REVERSE}b{RESET}"
    assert paint(line, False) == "ab"


def test_frame_clips_to_terminal_size():
    body = [[(f"line {i} " + "x" * 50, False)] for i in range(10)]
    out = frame("top", body, 12, 5)
    assert out.startswith(HOME) and out.endswith(CLEAR_BELOW)
    rows = out.removeprefix(HOME).removesuffix(CLEAR_BELOW).split("\n")
    assert [r.removesuffix("\x1b[K") for r in rows] == ["top", "", "line 0 xxxxx", "line 1 xxxxx", "line 2 xxxxx"]


def test_frame_without_ansi_is_plain_and_complete():
    body = [[("a" * 50, False)], [("b", True)]]
    assert frame("top", body, 10, 3, ansi=False) == "top\n\n" + "a" * 50 + "\nb\n"
