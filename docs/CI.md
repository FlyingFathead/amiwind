# Build audit and the local pipeline

_Last updated with AmiWind v0.0.54 (27 October 2026)._

The public GitHub Actions workflow (`.github/workflows/source-check.yml`) checks
the source on every push, in parallel jobs: the cached public tools, the test
suite in shards, then the asset-free dry-run image (its jobs are described in
[CI_DRY_RUN.md](CI_DRY_RUN.md)). Builds of the game itself need the user's own
Morrowind data, so they cannot run there. A local pipeline runs the checks that
need a real build. Its generic part, the post-build audit, is in this repository
so anyone can run it on their own builds.

## The hosted jobs and their names

GitHub shows every job under its displayed name. The release publisher waits
for exactly these names at the commit on `main`, so a change to this list is
told to the maintainer, with the old and new names, before the release is
pushed. The job ids in the workflow file stay the same; only a matrix job's
displayed name is built from its matrix value.

| Displayed name | Job id | What it does |
|---|---|---|
| `tools` | `tools` | Restores the bootstrapped public tools from the Actions cache and checks them file by file (a changed installer key bootstraps from nothing). |
| `source-checks` | `source-checks` | The source allowlist and the quick checks. |
| `Test suite part 1 of 6` to `Test suite part 6 of 6` | `tests` | The whole test suite in six parallel shards (`tools/run_tests.py --shard I/6`): whole modules balanced by `tests/module-timings.json`, every module in exactly one shard. Together the six parts run each module once. |
| `dry-run` | `dry-run` | After the tests: the engine compile, the boot-notice image and its package. |
| `docker-builder` | `docker-builder` | Builds the tools-only Docker image and validates the Linux container builder. |
| `host-launcher-parity (ubuntu-24.04)`, `host-launcher-parity (windows-2022)` | `host-launcher-parity` | The shared host contract and the real Windows launcher checks. |
| `tools-from-nothing` | `tools-from-nothing` | Tags, the weekly schedule and manual runs only: the from-nothing bootstrap and the dry-run image without any cache. Not required at a `main` commit. |

Before v0.0.54 the six test parts had no name of their own and GitHub showed
them as `tests (1)` to `tests (6)`.

## Post-build audit: `tools/build_audit.py`

It reads one builder run folder (`build-state.json`, `build-summary.json`, the
stage output manifests under `profile/`) and changes nothing.

```
python3 tools/build_audit.py RUN [--json]
python3 tools/build_audit.py RUN --compare REFERENCE_RUN [--ignore GLOB ...] [--json]
```

Exit status: 0 = nothing needs attention, 1 = at least one finding marked
`wake` (or, with `--compare`, a difference), 2 = not a builder run.

What it checks:

| Check | Finding | Why |
|---|---|---|
| Reuse audit | `unexpected-rebuild` | With `--reuse-from`, every stage that was not reused gets a class. Expected: its inputs changed, it is never reused (engine, image), or the old run did not pass it. Unexpected: the old output manifest is missing or unusable, old outputs changed, a stage's reuse was refused because of write attribution, an unknown reason, or a source change limited to files that must never key a conversion stage (the release file list, documentation). A reuse report from the builder (`reuse-report.json`), when present, states the expectation itself. |
| End summary | `summary-mismatch`, `summary-missing`, `output-hash`, `compiler-warnings`, `media-coverage` | The final status agrees with the stages; a passed build has a summary with the output's SHA-256, zero compiler warnings and complete media coverage. |
| Time to fail | `build-failed`, `late-failure` | Where a failed build stopped and after how long. A failure later than `--late-after` seconds (default 600) means a check ran late that could have run first. |
| Exclude effect | `exclude-no-effect`, `exclude-late` | `--exclude-video` left no video in the payload; a media stage with `--exclude-unreferenced` that is not reused stays under `--media-ceiling` seconds (default 300). |

`--compare` checks two runs file by file: the paths and SHA-256 of every
stage's outputs (from the stage output manifests) and the final output hash.
This is how a from-scratch build is checked against a release build: every
difference is a bug, except paths named with `--ignore` (documented build-time
stamps).

## The local pipeline (overview)

The pipeline itself uses private paths and runs on the maintainer's machine; it
is not part of this repository. What it does:

- A new commit on a branch that is ready to merge gets the fast checks
  (seconds) and then the full gate, in a queue with a fixed number of slots.
- A new head of the integration line is gated, then published together with
  the list of fixes it contains.
- A builder error serious enough to waste build time at scale puts every build
  on hold until the published head contains its fix.
- After every builder run, the audit above runs and its timings go into the
  build profile ledger.
- Every night, a second build machine (pull-based: it fetches signed jobs and
  posts results back) builds the game from scratch, compares the payload with
  the latest release file by file, and times a MiniWind sandbox build. When no
  second machine is set up, the same jobs can run locally.
