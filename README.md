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

The interval is the pause after each run, so a command that takes a second runs
every 3 seconds with the default `-n 2`. With `-p` (`--precise`) runs start every
`-n` seconds instead, counting the time the command takes; one that takes longer
than the interval is followed straight away.

For commands that can hang, `--timeout SECONDS` kills a run that takes longer
(along with anything it started). What it printed so far is kept, the header shows
`timed out` instead of the exit code, and the run counts as exit code 124, like
`timeout(1)`, so `-e` stops on it.

```bash
dwatch --timeout 5 'curl -sS http://flaky.local/status'
```

### Stopping on its own

```bash
dwatch -g 'ls ~/Downloads'           # stop when the output changes
dwatch -e -n 10 'curl -fsS localhost:8080/health'   # stop when the command fails
dwatch --count 5 uptime              # stop after 5 runs
```

| Option | Stops after the run where | dwatch exits with |
|---|---|---|
| `-g`, `--exit-on-change` | the output differs from the run before | 0 |
| `-e`, `--exit-on-error` | the command exits non-zero | the command's exit code |
| `--count N` | N runs are done | 0 |

When it stops this way, the last screen is printed again after the terminal is
restored, so it stays in your scrollback. Ctrl-C always exits with 0.

When stdout isn't a terminal (piped or redirected), nothing is cleared or
highlighted: each run is printed in full, header first.

### Keeping a log of changes

```bash
dwatch --log changes.log 'ls -l build/'
```

`--log FILE` appends to FILE (it's never overwritten): first the output of the
first run, then a unified diff each time the output changes. Each entry starts
with a `===` line giving the date, time, exit code and command:

```
=== 2026-11-03 13:18:48 | exit 0 | echo fixed; date +%S
--- 13:18:47
+++ 13:18:48
@@ -1,2 +1,2 @@
 fixed
-47
+48
```

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
now, and tabs are expanded to 8-column stops so columns line up. Output longer or
wider than the terminal is cut off.

### Ignoring noisy parts

```bash
dwatch --ignore '\d\d:\d\d:\d\d' 'ps -o pid,stat,time,cmd'
dwatch --ignore 'pid=\d+' --ignore 'took \d+ms' ./status.sh
```

`--ignore REGEX` (Python regex syntax, repeatable) leaves the text it matches
out when runs are compared, line by line. A run where only ignored parts moved
doesn't count as a change: it's not highlighted, not counted in the header, not
logged and doesn't stop `-g`. The ignored text is still shown, just never
highlighted.

## Test

```bash
pytest
```

## Plans

Planned work (colour pass-through, pause and scroll keys, wide-character fixes,
more tests) is listed with estimates in [ROADMAP.md](ROADMAP.md).

## License

MIT, see [LICENSE](LICENSE).
