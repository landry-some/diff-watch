from diff_watch.diff import diff_line, highlight, mask


def test_unchanged_line_has_no_highlight():
    assert diff_line("same", "same") == [("same", False)]
    assert diff_line("", "") == []


def test_changed_characters_are_highlighted():
    assert diff_line("used 41%", "used 42%") == [("used 4", False), ("2", True), ("%", False)]


def test_inserted_characters_are_highlighted():
    assert diff_line("ab", "aXb") == [("a", False), ("X", True), ("b", False)]


def test_removed_characters_leave_the_rest_plain():
    assert diff_line("abcdef", "abdef") == [("abdef", False)]


def test_unrelated_line_is_highlighted_whole():
    assert diff_line("hello world", "zzzzzz") == [("zzzzzz", True)]


def test_inserted_line_does_not_shift_highlights():
    old = ["a", "b", "c"]
    new = ["a", "new", "b", "c"]
    assert highlight(old, new) == [[("a", False)], [("new", True)], [("b", False)], [("c", False)]]


def test_replaced_lines_get_a_character_diff():
    old = ["/dev/sda1  41%", "tmpfs  1%"]
    new = ["/dev/sda1  42%", "tmpfs  1%"]
    assert highlight(old, new) == [
        [("/dev/sda1  4", False), ("2", True), ("%", False)],
        [("tmpfs  1%", False)],
    ]


def test_extra_lines_in_a_replace_block_are_new():
    old = ["x1", "y"]
    new = ["x2", "x3", "y"]
    assert highlight(old, new) == [[("x", False), ("2", True)], [("x3", True)], [("y", False)]]


def test_removed_lines_are_not_shown():
    assert highlight(["a", "gone", "b"], ["a", "b"]) == [[("a", False)], [("b", False)]]


def test_first_output_against_nothing_is_all_new():
    assert highlight([], ["a", "b"]) == [[("a", True)], [("b", True)]]


def test_mask_removes_matches_line_by_line():
    import re

    assert mask("pid 12 up\npid 345 up", re.compile(r"\d+")) == "pid  up\npid  up"
    assert mask("a \n b", re.compile(r"\s+")) == "a\nb"  # never joins lines
    assert mask("same", None) == "same"


def test_ignored_parts_do_not_count_as_changes():
    import re

    ignore = re.compile(r"\d\d:\d\d")
    assert highlight(["at 10:00 ok"], ["at 10:01 ok"], ignore) == [[("at 10:01 ok", False)]]


def test_ignored_parts_are_never_highlighted():
    import re

    ignore = re.compile(r"\d\d:\d\d")
    assert highlight(["at 10:00 ok"], ["at 10:01 up"], ignore) == [
        [("at 10:01 ", False), ("up", True)]
    ]
    # A new line is highlighted whole, except for the ignored part.
    assert highlight([], ["new 10:02 x"], ignore) == [
        [("new ", True), ("10:02", False), (" x", True)]
    ]
