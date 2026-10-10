# Build audit and the local pipeline

The public GitHub Actions workflow (`.github/workflows/source-check.yml`) checks
the source on every push. Builds of the game itself need the owner's own
Morrowind data, so they cannot run there. A local pipeline runs the checks that
need a real build. Its generic part, the post-build audit, is in this repository
so anyone can run it on their own builds.

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
