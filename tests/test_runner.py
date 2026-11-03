from diff_watch.runner import Run, clean, run_command


def test_shell_joins_words_and_merges_stderr():
    run = run_command(["echo out;", "echo err >&2;", "exit 3"])
    assert run.output == "out\nerr\n"
    assert run.exit_code == 3


def test_exec_mode_does_not_use_a_shell():
    run = run_command(["echo", "a;b", "$HOME"], use_shell=False)
    assert run.output == "a;b $HOME\n"
    assert run.exit_code == 0


def test_missing_program_is_reported_as_output():
    run = run_command(["no-such-program-dwatch"], use_shell=False)
    assert run.exit_code == 127
    assert "cannot run no-such-program-dwatch" in run.output


def test_clean_strips_escapes_and_carriage_returns():
    raw = "\x1b[31mred\x1b[0m\r\n\x1b]0;title\x07ok\rdone"
    assert clean(raw) == "red\nokdone"


def test_lines_ignores_final_newline():
    from datetime import datetime

    now = datetime.now()
    assert Run("a\nb\n", 0, now).lines == ["a", "b"]
    assert Run("a\n\n", 0, now).lines == ["a", ""]
    assert Run("", 0, now).lines == []
