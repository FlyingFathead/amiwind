# Build status folder: a file interface for stall alerts

_Last updated with AmiWind v0.0.66-dev2 (13 November 2026)._

Every build `tools/build.py` runs keeps a small status folder that any program can read to follow it and to catch a
stall, with no server and no library: `<workspace>/build/<run>/status/`. Before the first stage, while the run
folder does not exist yet (a build refused in its start-up leaves none), the same files are in
`<workspace>/build/.startup/<run>/status/`. A `--check` or `--plan` run creates nothing
in the workspace: it prints its `[stall]` lines in the log only, and writes the folder only into the folder the
environment variable `AMIWIND_STATUS_DIR` names (`$AMIWIND_STATUS_DIR/status/`). The folder is written from the
start of `build.py` (before the first stage: the entry check, the reuse preflight and the resource plan count too)
until the build ends. The format is a stable interface: fields are only added, and a change that breaks a reader
gets a new `format` value.

## heartbeat.json

Rewritten every few seconds, atomically (a temporary file renamed over the old one), so a reader never sees half of
it.

```json
{
 "format": "amiwind-build-status-1",
 "run": "2026_11_13_v0.0.66-dev2_full_1d5d76a",
 "status": "running",
 "phase": "chim",
 "elapsed_seconds": 1834.2,
 "cores_now": 1.02,
 "cores_planned": 22,
 "seconds_since_progress": 12.0,
 "stall": {"state": "under-cores", "since": 1500.0, "reason": "chim: 1.0 of 22 planned cores for 334 s"},
 "written_epoch": 1794600000.123
}
```

- `status`: `starting` (before the first stage), `running`, then `passed`, `failed`, `stopped` or `checked` (a check
  or plan run that ended).
- `phase`: the running stage or stages, or during the start-up the last line the builder printed.
- `cores_now` against `cores_planned`: the cores the build uses now and the cores it was given.
- `seconds_since_progress`: seconds since the last output of the running stages (the start-up: since its last line).
- `stall.state`: `ok`, `slow` (a stage past three times its recorded time), `under-cores` (under half of the planned
  cores for five minutes) or `stalled` (no progress for 20 minutes and almost no CPU); `since` is seconds into the
  build when the state began.
- `written_epoch`: when the file was written (Unix time). A heartbeat much older than a few seconds while `status`
  says the build runs means the builder itself is stuck or gone.

## stall.jsonl

One JSON line appended per stall incident (each time the state leaves `ok` or changes to another stall state):

```json
{"format": "amiwind-build-status-1", "time": "2026-11-13T21:40:12+0200", "epoch": 1794600012.5, "stage": "chim", "state": "stalled", "since": 2400.0, "reason": "chim: no progress for 1201 s at 0.00 cores", "resume": "build.py with the same options, --reuse-from <run> (its finished stages and units are kept)"}
```

## The catcher

`tools/stall_watch.py` (standard library only) follows both files:

    python3 tools/stall_watch.py RUN_DIR [--on-stall COMMAND] [--max-age SECONDS] [--exit-on-stall] [--once]

It prints each incident once, runs COMMAND once per incident with the state and the reason as its last two arguments,
and treats a heartbeat older than `--max-age` (default 120 s) as an incident of its own (`no-heartbeat`).
`--exit-on-stall` exits with code 3 at the first incident, so a loop or a CI job can wake on it; `--once` checks
what is there now and exits. The Toolkit monitor (its stall banner and `toolkit_serve.py --on-stall`) reads the same
files. Tests: `tests/test_build_stall.py`.
