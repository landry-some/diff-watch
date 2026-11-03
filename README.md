# diff-watch

`dwatch` re-runs a command every few seconds, shows its output full-screen, and
highlights what changed since the previous run, down to the character. It can also
highlight everything that changed since it started, stop when the output changes or
the command fails, and write every change to a log file as a unified diff.

It's for people who keep an eye on something from a terminal (`df -h`, `ls -l build/`,
`git status`, a status endpoint via `curl`) and want to see what moved without staring
at the screen the whole time.

Built with Python 3.11+ and the standard library only (`subprocess`, `difflib`, ANSI
escape codes). Tests use pytest. Developed on Linux; it should work on macOS too.

## Install

```bash
git clone https://github.com/landry-some/diff-watch.git
cd diff-watch
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
```

## Run

```bash
dwatch df -h                         # every 2 seconds (the default)
dwatch -n 0.5 'ls -l | wc -l'        # every half second, shell syntax is fine
```

Press Ctrl-C to stop. The command runs through `sh -c` and its stdout and stderr
are shown together. Use `-x` to run it directly without a shell.

### What gets highlighted

Changes are shown in reverse video, compared with the previous run:

- a line that is new is highlighted whole;
- a line that changed shows only the changed characters (`used 4[2]%`), unless it
  changed so much that a character diff would be noise, then it's highlighted whole;
- removed lines simply disappear, as with `watch -d`.

With `-c` (`--cumulative`) the comparison is with the first run instead, so
everything that changed since you started `dwatch` stays highlighted:

```bash
dwatch -c 'ls -l ~/Downloads'
```

Lines are matched before characters, so one inserted line doesn't make everything
below it look changed. `--no-diff` turns highlighting off. The header shows the
interval, the command, the last exit code, how many runs changed the output so far,
and the time of the last run.

Escape sequences in the command's output (colours, cursor moves) are stripped for
now. Output longer or wider than the terminal is cut off.

## Test

```bash
pytest
```

## License

MIT, see [LICENSE](LICENSE).
