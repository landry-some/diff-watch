from datetime import datetime

from diff_watch.log import entry
from diff_watch.runner import Run

T1 = datetime(2026, 11, 3, 9, 0, 0)
T2 = datetime(2026, 11, 3, 9, 0, 2)


def test_first_entry_logs_the_whole_output():
    text = entry("df -h", None, Run("a\nb\n", 0, T1))
    assert text == (
        "=== 2026-11-03 09:00:00 | exit 0 | df -h\n"
        "--- (start)\n"
        "+++ 09:00:00\n"
        "@@ -0,0 +1,2 @@\n"
        "+a\n"
        "+b\n"
        "\n"
    )


def test_later_entries_are_unified_diffs():
    text = entry("df -h", Run("a\nb\nc\n", 0, T1), Run("a\nB\nc\n", 1, T2))
    assert text.splitlines() == [
        "=== 2026-11-03 09:00:02 | exit 1 | df -h",
        "--- 09:00:00",
        "+++ 09:00:02",
        "@@ -1,3 +1,3 @@",
        " a",
        "-b",
        "+B",
        " c",
        "",
    ]


def test_empty_first_output_logs_only_the_title():
    assert entry("true", None, Run("", 0, T1)) == "=== 2026-11-03 09:00:00 | exit 0 | true\n\n"
