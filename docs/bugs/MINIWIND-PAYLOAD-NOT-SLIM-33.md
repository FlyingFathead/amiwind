# MINIWIND-PAYLOAD-NOT-SLIM-33: MiniWind #2 was built with the full movie and voice payload

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | MiniWind build line (v0.0.33-miniwind2) and its build mw2-033b |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | low: A Balmora-only playtest carries 17 videos (162 MB) and all 6,447 voices (207 MB) it never uses. |
| Family | Content silently missing from a build (`build-content-missing`) |
| Playtest version | MiniWind v0.0.33-dev1 #2 |
| From commit | source 2afe433, engine 2afe433, CHIM world 2afe433 |
| CHIM engine version | CHIM 0.1.0, engine 2afe433, world format 0.5 |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open.

## Symptom

The second AmiWind "MiniWind" Playtester Build (run mw2-033b, Balmora exterior on CHIM) staged all 17
Morrowind videos (intro 100 MB, other media 62 MB) and all 6,447 voice files (207 MB), although it starts
straight in Balmora and only Balmora's residents can speak.

## Where

The MiniWind build line (v0.0.33-miniwind2) and its build.

## How it happened

The exclude flags branch (`--exclude-video`, `--exclude-unreferenced voice,npcs`) was gated and listed as
ready, but it was not merged into the MiniWind line before the build started; MiniWind builds also do not
set those flags by default yet.

## Why it was not caught

Nothing compares a partial-area build's payload with what its areas can reference.

## Reproduction

Build `--miniwind --miniwind-scope exterior` from v0.0.33-miniwind2 2afe433 and list the media coverage of
the image.

## Repair

Planned: build the next MiniWind from the integration head that contains the exclude flags, with MiniWind
defaulting to `--exclude-video` and `--exclude-unreferenced voice,npcs` (music, the included NPCs' dialogue
pools and the shared sky are always kept).

## Verification

Pending: the next MiniWind's media coverage.

## Prevention

Every READY branch in the merge queue is merged into the build line before a playtest build starts.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Content silently missing from a build (`build-content-missing`). Every omission is receipted; payload and entity counts are compared with the last release; shipped features are on by default. See [families](README.md#families).

- [AUDIO-MISSING-SOURCES-32](AUDIO-MISSING-SOURCES-32.md): The image step reports missing sources for 7 voices and 2 effects
- [BUILD-DRESSING-EXCLUDED-32](BUILD-DRESSING-EXCLUDED-32.md): The repository builder drops lantern hooks and other dressing in Seyda Neen maps without a receipt
- [BUILD-EXTRA-TOWN-OPTIN-32](BUILD-EXTRA-TOWN-OPTIN-32.md): A default build leaves out the Vivec Arena preview that v0.0.32 ships
- [BUILD-FLORA-OPTIN-32](BUILD-FLORA-OPTIN-32.md): A from-scratch build without --tree-sprites leaves out the trees and grass every release ships
- [BUILD-HANDS-NOT-BUILT-32](BUILD-HANDS-NOT-BUILT-32.md): Per-race first-person hands are not built by the builder
- [BUILD-HARVEST-NOT-BUILT-32](BUILD-HARVEST-NOT-BUILT-32.md): Mushroom harvest data is not built by the builder
- [BUILD-NIGHT-TABLES-31](BUILD-NIGHT-TABLES-31.md): Repository image builds have no night lamp, glowing glass or location fog tables
- [BUILD-STANDALONE-STAGES-32](BUILD-STANDALONE-STAGES-32.md): Door overlay and interior section tools are outside the builder; their use in v0.0.31 is unverified
- [PLAYTEST-PAYLOAD-COVERAGE-32](PLAYTEST-PAYLOAD-COVERAGE-32.md): The v0.0.32-dev1 playtest has no first-person hands and no harvest
- [SEYDA-LANTERNS-MISSING-31](SEYDA-LANTERNS-MISSING-31.md): Seyda Neen lanterns light the night but are not in its maps
- TREE-SCALE-001 (no report page): Non-unit-scale tree sprites omitted; bounds too conservative

<!-- END GENERATED CATEGORY -->
