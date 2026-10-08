# BUILD-STANDALONE-STAGES-32: Door overlay and interior section tools are outside the builder; their use in v0.0.31 is unverified

## Status: 8 October 2026

Closed: neither tool's output is in v0.0.31, so no builder step is missing for this release.
Found by the builder defaults audit (every option and stage compared with the v0.0.31 payload).

## Symptom

`tools/prepare_original_door_overlay.py` and `tools/prepare_interior_sections.py` are standalone and
not called by the builder. Whether any v0.0.31 map depends on them is not yet known.

## Where

The two tools above.

## How it happened

Same as the other standalone stages.

## Why it was not caught

Release images were patched from earlier images instead of being built from scratch
(BUILD-NOT-FROM-SCRATCH-32), so a missing builder stage never showed.

## Reproduction

A from-scratch build with the repository builder; compare its payload with v0.0.31.

## Repair

No builder change needed. Checked against the v0.0.31 image:

- `prepare_interior_sections.py` writes `interior-sections.txt`, section maps with appended IDs
  and their harvest and door banks. v0.0.31 ships none of them (no `interior-sections.txt`, no
  appended interior maps): the tool's output is not in the release.
- `prepare_original_door_overlay.py` adds original exterior entrance doors to world maps (it
  refuses town maps). All 2,724 maps of v0.0.31 were scanned for entities bound to the 1,108
  original exterior entrances: none of the 2,532 world maps has one. The 102 maps that have
  them are Seyda Neen, Balmora and the intro docks, whose doors come from the normal town
  conversion.

Both tools stay standalone experiments. `config/release-features.json` would show any of their
output in a payload as files no feature explains.

## Verification

- Release payload (v0.0.31, all three partitions) read file by file: no section files or appended
  interior maps; entity scan of every map for original exterior entrance references as above.
- `tests/test_release_coverage.py`: every shipped file class belongs to a feature with default
  builder steps; neither tool is one of them.

## Prevention

`config/release-features.json` maps every file class v0.0.31 ships to a feature and its default
builder steps; `tests/test_release_coverage.py` fails when a shipped class has no feature or a
feature's step is not in the default build, and its list of known builder gaps may only shrink.
`tools/payload_coverage.py check` compares a built payload or staged image with the release, by
feature, for the from-scratch gate.
