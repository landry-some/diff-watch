# Roadmap

What comes after v0.1, with rough estimates. Total: about 32.5 hours.

## Features

- [ ] Pass the command's own ANSI colours through instead of stripping them, and diff on the visible text (5h)
- [ ] Pause/freeze key (`space`) and quit key (`q`) without Ctrl-C (2h)
- [ ] Scroll through output longer than the terminal (arrow keys / PgUp / PgDn) (4h)
- [ ] `--precise`: keep a fixed start-to-start interval instead of sleeping after each run (1h)
- [ ] `--beep` and `--notify`: bell or desktop notification when the output changes (1.5h)
- [ ] `--ignore REGEX`: mask noisy parts (timestamps, PIDs) before diffing (2h)

## Bugs and edge cases

- [ ] Wide characters (CJK, emoji) break width clipping and highlight alignment (2h)
- [x] Expand tabs before diffing and clipping so columns line up (1h)
- [ ] Redraw immediately on terminal resize (SIGWINCH) (1h)
- [ ] `--timeout SECONDS` for commands that hang, shown as a status in the header (1.5h)

## Refactors

- [ ] Move rendering to a small screen model (rows of styled cells) so clipping and highlighting share one code path (2h)
- [ ] Split the main loop into a state object so key handling and resize fit in cleanly (1.5h)

## Tests

- [ ] End-to-end tests of the loop with a fake clock and fake terminal (2h)
- [ ] Tests for Ctrl-C, SIGTERM and terminal restore (1.5h)
- [ ] Run the test suite on macOS and Windows (CI matrix) and fix what breaks (2h)

## Docs

- [ ] Man page and more `--help` examples (1.5h)
- [ ] README section comparing with `watch -d`, plus a short recorded demo (1h)
