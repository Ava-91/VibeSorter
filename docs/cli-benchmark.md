# `vibesorter benchmark` command design

The public CLI benchmark should wrap `vibesorter.benchmark.benchmark` and expose:

- folder
- `--no-recursive`
- `--repeats N`
- `--json`

The command is intentionally read-only. The engine and its stable result schema are separated from presentation so the CLI, tests, and future interfaces share the same measurement logic.
