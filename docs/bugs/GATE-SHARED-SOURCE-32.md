# GATE-SHARED-SOURCE-32: The local gate always tested the main checkout, in one shared folder

## Status: 8 October 2026

Open. Local gate fixed 8 October 2026 (the developers' integration gate runner, not part of the
repository). Found when two gates ran at the same time and one engine step failed.

## Symptom

The local integration gate (preflight, Linux suite, host parity, engine build) always staged the
main checkout into one shared source folder, whatever branch or worktree the job asked it to gate.
A job gating its own branch therefore tested the main line. Gates running at the same time
collided in the shared source folder and in fixed temporary paths: one engine step failed with
`FileExistsError`, and a stale-directory cleanup could have removed another gate's staged source in
the middle of its run.

## Where

The local gate runner (source staging, temporary folders, report header). The repository's own
tests and hosted CI are unaffected.

## How it happened

The gate was written for one developer gating one checkout at a time. Parallel jobs on their own
branches and worktrees reused it without a way to name the source.

## Why it was not caught

Gate reports did not name the repository and commit they tested, so a report for the main line
looked like a report for the branch.

## Reproduction

Run two gates at once from two worktrees on different commits with the old runner: both stage the
main checkout into the same folder.

## Repair

Local gate runner, 8 October 2026: a repository selector (`REPO`, default the main checkout), a
staged source per gate number, temporary folders per gate, a refusal to reuse a gate number, and a
header line in every report naming the repository and commit gated.

Consequence: branch gates reported earlier on 8 October 2026 from worktrees without the selector
may have tested the main line instead of the branch. Merges were gated again on the merged main
line, which is what the register's results rely on.

Follow-up 1 (8 October 2026, same day): the per-gate temporary folders were not removed when a
gate finished. About 35 MB per gate number plus older leftovers filled the build container's
512 MB temporary file system; preflight and engine steps of later gates then failed with empty
logs (exit 1 although the preflight receipt had been written). Fixed in the local gate runner:
each step removes its own temporary folders when it ends, and the gate refuses to start with less
than 150 MB free.

Follow-up 2: that first cleanup also removed the engine build folder from the preflight step
while the engine step was still compiling ("getcwd() failed"). Fixed: only the engine step owns
the engine build folder. The next full gate after the fix was green in every step.

## Verification

Two gates ran concurrently on different sources: one on the main checkout at 2935df6, one on a
worktree at b03ca3f. Each staged its own source and named it in its header. The main-line gate was
green in every step, and the worktree gate found a real problem on its branch (a version bump
without the versioned emulator templates), which the old runner would have missed by testing the
main line.

## Prevention

Every gate report is checked for the header line (repository and commit) before its result is
used; a gate number is never reused.
A gate leaves no temporary folders behind and refuses to start when the temporary file system is
nearly full.
