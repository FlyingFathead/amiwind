# aw: the master builder command line

`tools/aw.py` is the first part of the master builder: one owner of the shared build
state (gate numbers, worktrees, run names, results) so that several workers on one machine
never pick the same gate number, never share a worktree by accident and never read a red
gate as green. Python 3.10 or newer, standard library only, no game data.

<!-- contents start -->
## Contents

- [Config](#config)
- [Leases](#leases)
  - [Core leases](#core-leases)
- [Gates](#gates)
- [Entry check](#entry-check)
- [Request and result forms](#request-and-result-forms)
- [Build requests](#build-requests)
- [Broadcast](#broadcast)
- [Perf database step](#perf-database-step)

<!-- contents end -->

    python3 tools/aw.py [--config FILE] enter
    python3 tools/aw.py [--config FILE] gate --repo PATH [--commit C] [--reason R] [--range NAME] [--number N]
    python3 tools/aw.py [--config FILE] status [--json]
    python3 tools/aw.py [--config FILE] lease gate|worktree|run-name|renew|release|list ...
    python3 tools/aw.py [--config FILE] submit REQUEST.json [--dry-run]
    python3 tools/aw.py [--config FILE] request --kind build|gate|... --repo PATH --commit C --purpose P --reason R ...
    python3 tools/aw.py [--config FILE] announce --kind builder-bug|builder-update --ids ID,... --summary TEXT [--hold]
    python3 tools/aw.py [--config FILE] inbox [--job NAME] [--all]
    python3 tools/aw.py [--config FILE] reply MSG_ID --none | --proposal TEXT | --commit REPO:SHA | --defer TEXT
    python3 tools/aw.py [--config FILE] publish --commit SHA --contains TEXT [--fixes ID,...] [--closes MSG_ID,...]
    python3 tools/aw.py [--config FILE] sync-version

## Config

All locations come from a JSON config file, given with `--config FILE` or the environment
variable `AMIWIND_AW_CONFIG`; the tool holds no paths of its own. Relative paths are read
relative to the config file.

    {"schema": "aw-config-1",
     "state_dir": "aw-state",
     "working_version_file": "WORKING_VERSION.json",
     "integration_ref": "integration/latest",
     "gate": {"command": ["bash", "/path/to/gate-runner.sh", "{number}"],
              "out_dir": "/path/to/gate-folder",
              "ranges": {"team-a": [100, 119], "team-b": [120, 139]},
              "default_range": "team-a",
              "env": {}},
     "lease_ttl_s": {"gate": 21600, "worktree": 86400, "run-name": 86400},
     "lock_stale_s": 300,
     "integration_head_file": "integration-head.txt",
     "build": {"image": "amiwind-builder:TAG", "user": "1000:1000",
               "volume": "build-volume", "mount": "/vol",
               "inputs_volume": "game-data-volume", "inputs_mount": "/owned",
               "workspace": "/vol/ws", "source_dir": "{mount}/src/{series}-{commit}",
               "tools_dir": "/opt/amiwind-tools", "cpus": 24, "memory": "44g", "jobs": 24,
               "check_cpus": 4, "container_prefix": "aw",
               "recipes_dir": "{mount}/src/recipes", "save_recipe": true,
               "default_flags": [["--chim-native-towns", "on"], ["--live-logs"]],
               "trials_log": "trials/TRIALS.jsonl",
               "ingest": {"image": "IMAGE", "mounts": ["/host/notes:/c"],
                          "command": ["python3", "/c/ingest.py", "{run_dir}", "--label", "{run_name}"]}},
     "broadcast": {"merge_queue_file": "merge-queue.md", "reply_within_min": 30,
                   "pool_working_version_files": ["/vol/WORKING_VERSION.json"],
                   "publishers": ["coordinator"], "auto_join": true},
     "perf_db": {"command": ["bash", "/path/to/perf-db-wrapper.sh", "post", "--kind", "{kind}",
                             "--run", "{run_name}", "--result", "{result}", "--run-dir", "{run_dir}"],
                 "timeout_s": 900}}

`integration_head_file` is the publisher's note of the integration head: its newest `PUBLISHED (...): <hash>`
line and the `CONTAINS ...` lines under it. `build` is needed only for build requests (see below);
`recipes_dir` is where a request's build recipe is staged in the build volume (default
`{mount}/src/recipes`) and `save_recipe` (default true) lets every passed build check in its recipe.
`broadcast` switches the builder broadcast on (see "Broadcast"); `perf_db` adds the
[perf database step](#perf-database-step).

`state_dir` holds the lease register (`aw-state.json`), its lock file, the result files
(`results/`), console logs (`logs/`) and the trial log (`aw-trials.jsonl`, one JSON line
per request, result, lease, renewal, release and broken stale lock).

## Leases

The register is one JSON file, rewritten atomically and only while holding an exclusive
lock file (created with `O_EXCL`; held for milliseconds). A lock older than `lock_stale_s`
seconds is moved aside, logged, and taken over.

- **gate**: the lowest number of the requested range that was never leased before and has
  no outputs in the gate folder (`par-N-*`, `preflight-N`, `suite-N`, `engine-N`,
  `source-N`). A number is spent once leased, even after release. An exhausted range is
  refused (exit 3).
- **worktree**: one holder per path; another requester is refused until the lease is
  released or has expired.
- **run-name**: `YYYY_MM_DD_vX.Y.Z[-suffix]_<purpose>[-<reason>][-tryN]_<gitshort>` from
  the host date, the repository's `VERSION` and its `HEAD`; a name already handed out gets
  `-try2`, `-try3`, ...

`aw lease renew ID` extends a lease by its time-to-live, `aw lease release ID` ends it,
`aw lease list [--all]` shows the register.

**Finished jobs** leave the register on their own, so a broadcast's acknowledgements can
complete: `aw lease done` (with the job's `--requester` or `AW_REQUESTER`) ends every lease
the job holds (its core lease gives the cores back to the running builds), and every listing,
broadcast and status ends the worktree lease of a job whose worktree is gone, or whose HEAD is
merged into the integration ref with a clean worktree and no lease renewal or commit for
`lease_idle_s.worktree` seconds (default 2 h). Each such end is logged in the trial log with its
reason, and the lease keeps it (`expired_because`).

### Core leases

The machine has a fixed number of threads and a fixed amount of memory, and every build the
master builder starts gets a **core lease** that holds both: no oversubscription, ever (the sum
of the core leases never exceeds the host's threads, the sum of the memory leases never exceeds
the containers' memory less a host reserve).

- **Host**: `build.host_threads` in the config (default: the host's CPU count). Each running
  gate holds `build.gate_cores` (default 4); each build gets at least `build.min_cores`
  (default 2). A build that cannot get its minimum is refused (`core lease: no cores free`);
  submit it again when a build has ended.
- **Priority**: `options.priority` of the request (`aw request --priority`), else `release`
  for purposes starting with `release` or `rcN`, else `dev`. Release-critical outranks dev,
  dev outranks optional or experimental builds (weights 3 : 2 : 1).
- **Memory**: each build leases what it asks for (`options.memory`, else `build.memory`) out of
  `build.host_memory_gib` (the memory Docker's machine has) less `build.memory_reserve_gib`
  (default 4) and `build.gate_memory_gib` (default 6) for each running gate. Memory is never
  squeezed: a build whose memory does not fit waits.
  The default `build.memory` is sized down so that a build fits beside one running gate; an
  explicit `--memory` that fits only while no gate runs is kept, with a note. A request for more
  than the host leases at all is refused at once ("can never fit"), never queued. A waiting request
  reads the config again at every poll, so a changed lease size or gate reserve reaches it
  (AW-LEASE-MEMORY-DEADLOCK-36).
- **Queue**: a build that does not fit (cores or memory) waits in the queue instead of starting,
  checked every `build.queue_poll_s` (default 30 s) for up to `build.queue_timeout_s` (default
  6 h; then it is refused). The queue goes by priority, then by arrival: a request never starts
  while an earlier one of the same or a higher priority still waits.
- **Plan**: every build gets its minimum, then one core at a time goes to the build with the
  fewest cores per priority weight, never more than it asked for (`options.cpus` or
  `options.jobs`, else `build.cpus`). The build runs with `--jobs`, `docker --cpus` and
  `docker --memory` equal to its lease.
- **Rebalance**: when a build starts, the running builds whose share moved are resized with
  `docker update --cpus`; when a build ends, its cores go back to the builds still running the
  same way, and so do gates: when a gate starts the running builds make room, when it ends they
  grow back (AW-LEASE-NO-GROW-36). Their worker pools keep the size they started with; only the
  CPU quota follows (resizing the pools through the builder's jobs file is the open repair).
- **Result and status**: the build result's `cores` block names the priority, the cores
  wanted and leased, the host and the rebalances; `aw status` lists every core lease and the
  machine totals (`core leases: N of 24 threads to K build(s), G held by gates, F free`;
  `memory leases: M of H GiB (R reserved for the host), F free; queued: Q`) and the queue.
- Since `--jobs` is the lease, the builder's own underuse verdicts and the
  [perf guard](BUILD_PROFILE.md#perf-guard) judge each section against the cores the build
  actually had, not against the whole machine.

## Gates

`aw gate` checks the request first (checkout `HEAD` is `--commit` if given, no uncommitted
files unless `--allow-dirty`, `VERSION` equals the working version unless
`--accept-version-mismatch REASON`, `HEAD` contains the integration head), leases a gate
number and a run name, runs the configured gate command with `REPO=<repo>` in its
environment, and then judges the gate from its output files, not from the command's exit
status. The gate passes only when every step line says `-exit=0` (preflight, suite, host
parity Linux and Windows, engine), the suite receipt says `successful` with tests run and
no failures or errors, and the engine build has no compiler warnings. A missing step
counts as failed.

The result is written as `results/<run name>.json` in the `aw-result-1` form and `aw gate`
exits 0 (passed), 1 (failed), 2 (refused) or 3 (no gate number available). Both leases are
released when the gate ends.

## Entry check

`aw enter` runs the entry check of the source tree it belongs to (`tools/entry_check.py`):
`VERSION` against the working version, the integration head (the configured git ref and
the working-version record) contained in `HEAD`, every builder module loaded from this
tree, and no `PYTHONPATH` entry pointing into another builder tree. Exit 0 = ok, 1 =
refused.

## Request and result forms

`config/schemas/aw-request-1.json` and `config/schemas/aw-result-1.json` (JSON Schema)
describe the request (kind `gate`, `build`, `miniwind`, `chimport-region` or `smoke`;
repository, commit, purpose, full version, reason, requester, host time
`YYYY-MM-DD HH:MM:SS +ZZZZ`) and the result (status `passed`, `failed` or `refused`;
numbers, steps, failed steps, artifacts, logs, timings, reuse summary, lease ids). `aw`
validates every document against them before writing it. Gates and builds run; see
"Build requests" for the other kinds.

## Build requests

`aw submit REQUEST.json` hands the build server one request in the `aw-request-1` form;
`aw request --kind ... --repo ... --commit ... --purpose ... --reason ...` writes the request
from its options and submits it (`--write-only` only writes it). The answer is
`results/<run name>.json` in the `aw-result-1` form; the exit code is 0 (passed), 1
(failed) or 2 (refused). A request that does not match the form is refused with every
reason and nothing runs. Every request, result and trial line carries the host time, the
full version, the commit, the requester and the reason.

    {"schema": "aw-request-1", "id": "req-...", "kind": "build", "repo": "/path/to/checkout",
     "commit": "dd757fa", "purpose": "full", "version": "v0.0.36-dev3", "reason": "sea ring",
     "requester": "worker-a", "time": "2026-10-10 18:00:00 +0300",
     "options": {"flags": ["--no-npc-gallery", "--chim-regions", "@/vol/in/cells.csv"],
                 "reuse_from": "/vol/ws/build/2026_10_10_v0.0.36-dev2_full_642c1ea",
                 "inputs": [{"path": "/vol/in/cells.csv", "sha256": "...", "role": "cells"}]},
     "override": {"reason": "...", "allow": ["version-mismatch"]}}

The options of each kind are in the schema's `$defs`. Kind `gate` runs `aw gate`; kind
`build` is described here; `chimport-region` and `smoke` have a fixed request form and are
refused as not implemented yet.

Kind `miniwind` is a MiniWind build of one test spot through the same path as kind `build`
(every check below, the run name, the storage pool, the result, the trial line and the perf
ingest). `options.preset` names a preset recipe `config/recipes/miniwind/PRESET.json` of the
requested commit (a commit from before the recipes: a row of its `config/miniwind-presets.json`;
an unknown name is refused with the list); the server hands the builder
`--miniwind-preset PRESET`, which builds from that recipe, records the recipe's SHA-256 in the
result (`recipe.requested`) (and `--miniwind-description` from `options.description`), so the
flags may not name `--miniwind`, `--miniwind-preset`, `--miniwind-description` or a preset
alias. Other MiniWind options go in the flags, for example `--miniwind-town vivec_arena`. The
purpose is `miniwind-<scene>`; `--purpose miniwind` becomes `miniwind-PRESET`:

    aw request --kind miniwind --repo <checkout> --commit <gated head> --purpose miniwind --preset vivec-arena-pit --reason "arena on CHIM" --reuse-from /vol/ws8/build/<run>

A build request is checked first, in this order; any failure refuses it before the build:

1. **Commit and version:** the commit exists in the repository; the request's version is
   that commit's `VERSION`; it equals the working version (unless `override.allow`
   names `version-mismatch`; the builder then gets `--accept-version-mismatch` with the
   reason).
2. **Builder head:** the commit contains the integration head (the configured git ref,
   the working-version record and the published head). A request from an older builder
   is refused as `STALE BUILDER` with the merge command; `aw status` shows the published
   head and what it contains.
3. **Options:** options the server sets itself (`--name`, `--workspace`, `--reuse-from`,
   `--reuse-mode`, `--storage-pool`, `--developer-mode`, `--data-files`, `--tools-dir`,
   `--jobs`, `--source-commit`, `--accept-rebuild`, `--accept-version-mismatch`,
   `--any-run-name`) are refused; say them in the request instead. Retired options
   (`--legacy-area`, `--chim-native-towns off`) are refused unless `override.allow` names
   `retired-flags` - an A/B test of a historical regression: the run name then carries
   `ab-regression`. The config's `default_flags` are added when the request does not name
   that option.
4. **Run name:** `YYYY_MM_DD_vX.Y.Z[-suffix]_<purpose>-<reason>_<git>`; a name already in
   the register or in the workspace's build folder gets `-try2`, `-try3`, ...
5. **Source:** the commit (never a working tree) is exported with `git archive` into the
   build volume once per commit and its `VERSION` read back.
6. **Input files:** every file in `options.inputs` is hashed in the build volume and must
   match its SHA-256; the result records them.
7. **Developer-mode check:** the build command itself with `--check`: the builder's own
   entry block (version, imports, run name) and its reuse preflight, computed in the
   build's own environment, plus the build preflight (cache ownership, game data), with
   no stage run. A reuse preflight with rebuilds the source diff does not explain ("keys
   too broad") or with unexpected rebuilds is refused unless `override.allow` names
   `unexplained-rebuilds` (the builder then gets `--accept-rebuild`). The source diff
   against the reuse source's commit (the hash at the end of its run name, or
   `options.reuse_from_commit`) is recorded with the result.

Then the build runs in the configured image with `--pull never`, no network, the build
user, `PYTHONPATH` from the exported source, `--developer-mode`, `--storage-pool on` and,
with a reuse source, `--reuse-mode pool`. Afterwards the server reads the run's
`build-state.json` (status, stages reused and rebuilt, failed stage), appends one line
to the configured trial log, runs the configured perf ingest and writes the result. After
a build that passed, and only then, it marks the run's stair-walk records as checked
(`tools/stair_records.py promote --run RUN --request ID`), so later builds may reuse them;
the result's `stair_walk` counts the records marked and the maps and frames the build
reused and walked; `aw status` shows those counts with each recent build. The step `perf-guard` reads the
verdict the builder's perf guard wrote (`tools/perf_guard.py show RUN --json`, result field `perf_guard`): a failed
guard fails the result (failed stage `perf-guard`; the build's stages passed, so its stair walks are still marked),
and `aw status` shows the verdict and the waivers ([Perf guard](BUILD_PROFILE.md#perf-guard)). Hashed stair walks
are mandatory: once the published builder head has the records layer (`tools/stair_records.py`),
a build of a commit without it is refused until the published builder is merged, and
`--stair-walk-cache full` (every map and frame walked again) is refused unless the request
carries `override.allow` `stair-walk-full` with a reason; such a run is a regression or
beta test, and its name says `regression-beta-test`. Like the perf ingest, the marking never fails a build that passed; when it
fails, its step says why and the records stay candidates. Every build also gets its request
id (`AMIWIND_AW_REQUEST`), which its stair-walk records carry.
`--dry-run` (or `options.dry_run`) checks the request and prints every command without
running any of them; no run name is spent.

**Build recipes** ([BUILD_RECIPES.md](BUILD_RECIPES.md)): `aw request --kind build --recipe FILE`
sends a recipe instead of (or next to) `--flags`. The request carries the recipe's text byte
for byte with its SHA-256 (`options.recipe`); its input files become declared inputs (step 6),
so they must be paths in the build volume. The server refuses a recipe that sets a retired
option (as for flags, unless `override.allow` names `retired-flags`), a recipe input with a
relative path, and a commit whose builder has no recipes. The recipe is staged into
`recipes_dir` as `<run name>.json` (its SHA-256 checked there) and given to the builder with
`--recipe`; flags sent with it win over the recipe, and the builder prints and records each
difference. Every build of a builder with recipes also gets `--save-recipe
<run folder>/build-recipe.json` (never the `--check` step, which writes nothing); after a
passed build the server fills in `checked_with` (AmiWind and CHIM version, the commit, the run,
the host time and the SHA-256 of the result file) and writes the verified recipe next to the
result as `results/<run name>.recipe.json`; the result's `recipe` field names it and the recipe
the request carried.

## Broadcast

The master builder also tells every worker about the builder itself: when a builder error is
found, every worker is asked for its own fix or proposal before one shared fix is chosen, and
when a new builder head is published, every worker is told to merge it at its next checkpoint.
The address list is the set of active worktree leases: each holder is one worker. With a
`broadcast` section in the config, `aw gate` and `aw request` take or renew the lease of the
worktree they run on (`"auto_join": false` turns that off; `aw lease worktree PATH` works
always). Messages use the `aw-message-1` form (`config/schemas/aw-message-1.json`: id, kind,
host time, version, integration head, bug IDs, summary, hold, reply-by time, sender); the
register `aw-broadcast.json` in the state folder holds every message once with each
recipient's read time and replies, and each recipient gets a copy in `inbox/<job>/`.

- **Call for fixes:** `aw announce --kind builder-bug --ids BUILD-X-36,BUILD-Y-36 --summary
  "..." --hold` sends one message to every lease holder except the sender, with a reply-by
  time (`--reply-within MINUTES`, default `broadcast.reply_within_min` or 30). Kind
  `builder-update` announces a planned builder change and asks for merge requests and ideas.
  With `--hold`, every build request (`aw request --kind build`) is refused until the call
  closes; gates are still allowed. A build that must run anyway names `build-hold` in
  `override.allow` with a reason, which the result records.
- **Inbox:** `aw inbox` (the job name from `--job` or `AW_REQUESTER`) prints the unread
  messages and marks them read; `--all` also shows the read ones; open build holds are
  always listed. Workers run it at every checkpoint.
- **Reply:** `aw reply msg-3 --none` (no fix from this job), `--proposal "TEXT"`,
  `--commit REPO:SHA` (a fix commit; it must resolve in that checkout) or `--defer "why;
  when"`. The answer is recorded under the message and, when `broadcast.merge_queue_file` is
  set, one line is appended to that file: host time, version, job, message, answer.
- **Publish:** `aw publish --commit SHA --contains "what it brings"` (only the requesters in
  `broadcast.publishers`, when that list is set) checks first that the commit passed a gate:
  the newest passed gate result of that commit in the trial log, whose file must still have
  the SHA-256 recorded when the gate wrote it, with no failures, no engine warnings and no
  uncommitted files (`--gate-result FILE --gate-sha256 HEX` names one explicitly). It also
  refuses a commit that does not contain the current integration head. Then it moves the
  integration ref (compare-and-swap), writes a `PUBLISHED (aw gate N PASSED)` entry with the
  `CONTAINS` line on top of the integration head note, updates the working-version record
  (version from the commit's `VERSION`, head, time) and writes the same bytes to every
  `broadcast.pool_working_version_files` copy in the build volume (one container per file,
  `--pull never`, no network, the build user; each copy read back by its SHA-256). Calls
  whose bug IDs are all in `--fixes` or named in `--contains`, and calls named in
  `--closes`, are closed and their holds lifted. Finally a `new-builder` message goes to
  every lease holder: the new head, what it contains, the proposals received (or "no fix
  proposals came in: well, here is the new version"), and how to merge it or reply. A
  publish that closes a `builder-bug` or held call, or is given `--hold-level`, is a
  hold-level builder fix. If a build volume copy could not be written, the publish reports
  failed (exit 1) and `aw sync-version` writes the copies again.
- **Stale bases:** after a publish, `aw gate` and `aw request` refuse a commit that does not
  contain the published head (`STALE BUILDER`, with the merge command and the reply
  command). A worker that cannot merge yet answers the new-builder message with `--defer
  "why; when"`; its gates then run on the older base and the result records the reason.
  A hold-level builder fix still refuses that worker's builds until it merged.
- **Status:** `aw status` lists the open calls (who answered, who did not, holds) and, for the
  last new-builder message, each holder's state: merged (its worktree contains the head),
  deferred with the reason, or waiting.

Every message, reply and publish is also a line in the trial log with the host time, the
version, the commit and the requester.

## Perf database step

With a `perf_db` section in the config, every result `aw` writes (gate, build, refusal; not a dry
run) is followed by one run of `perf_db.command`, a command template filled with `{kind}`,
`{run_name}`, `{result}` (the result file) and `{run_dir}` (the build's run folder, empty for
gates). It runs after the result file is final, so the [perf database](PERF_DATABASE.md) reads
the file exactly as written; the step never changes the result or its status. Its last output
lines are printed with the prefix `aw perf-db:`, its exit code goes into the trial log (event
`perf-db`), and a failure prints `aw perf-db: FAILED (exit N) ...` on stderr. `"enabled": false`
switches the step off without removing it; `timeout_s` (default 900) bounds it. The command is
typically a small wrapper that starts a throwaway container running `tools/perf_db.py ingest`
with the result, the run folder and the ledgers (see
[Running it in a container](PERF_DATABASE.md#running-it-in-a-container)).
