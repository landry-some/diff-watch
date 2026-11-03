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
are shown together.

## Test

```bash
pytest
```

## License

MIT, see [LICENSE](LICENSE).
