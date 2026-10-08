# BUILD-NOT-FROM-SCRATCH-32: five releases shipped without the public builder being able to build them

## Status: 8 October 2026

Open. Found by the first from-scratch build with the repository builder. The repair
is a process rule plus two builder fixes in progress.

## Symptom

The repository builder could not build the game from the owner's own data from
scratch since v0.0.28: its `bsp` stage stops on the Seyda Neen full-town map
([BUILD-SEYDA-HULL2-32](BUILD-SEYDA-HULL2-32.md), since v0.0.28) and its actor stage
crashes ([BUILD-ACTOR-CONTACT-CALL-32](BUILD-ACTOR-CONTACT-CALL-32.md), since v0.0.27).
v0.0.28, v0.0.29, v0.0.30 and v0.0.31 were released anyway.

## Where

The release process: how playtest and release images were produced.

## How it happened

Every image since v0.0.28 was the previous image with overlays: new maps and a new
engine copied onto older disks by private scripts (for example v0.0.30-dev1 was the
v0.0.29 image plus a rebuilt Temple map; v0.0.31 was the dev6 disks plus a new engine and
lamp table). Builder stages whose outputs were reused never ran again, so the broken
stages stayed hidden. The source releases themselves were complete and correct as code.

## Why it was not caught

- Hosted CI builds only the asset-free dry run (engine and a boot notice image), never
  the whole game from real data, and cannot (no game data on CI).
- No rule required a from-scratch build before a release until 8 October 2026.
- The release gate compared the release with its own receipts, not with a fresh build.

## Reproduction

Run `tools/build.py` from scratch with your own Morrowind data on any version from
v0.0.28 to v0.0.32-dev at 0aeda94.

## Repair

- The two builder breaks are fixed properly (shared mechanism and stage smoke tests), see
  their pages.
- Rule: a from-scratch build with the repository builder before every release and after
  any converter or builder change, recorded with date, commit, duration and result; a
  release must be reproducible by that build (release gate from v0.0.32).
- Our own development builds use the repository builder (no private patch-up of older
  images).

## Verification

Pending: a from-scratch build that completes, and a v0.0.32 image produced by it.

## Prevention

The from-scratch rule above, plus builder stage smoke tests on synthetic data in the
suite so a stale call fails the gate, not the first real build.
