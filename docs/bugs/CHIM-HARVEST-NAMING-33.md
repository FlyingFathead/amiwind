# CHIM-HARVEST-NAMING-33: A town-wide CHIM harvest catalogue does not fit the name and size limits

## Status: 8 October 2026

Open; decided. Found while planning harvest for CHIM frame maps (branch v0.0.33-chim-format).

## Symptom

A town-wide frame map would need one catalogue named `harvest-<town>-chim.txt`, but:

- the builder's harvest gate accepts only map names matching `[a-z0-9_]{1,24}`;
- `harvest-vivec_telvanni-chim.txt` is 31 characters, over the 30-character FFS file name rule;
- merging a town's 64 region catalogues into one may exceed the per-file limits of the harvest
  runtime (64 nodes, 256 edges, 8 models).

## Where

`tools/harvest_build.py` (name gate), the harvest runtime (`engine/aga/src/aw_harvest.h` limits),
CHIM frame maps.

## How it happened

Harvest catalogues are per map; a CHIM frame spans many legacy region maps.

## Why it was not caught

First design pass of harvest under CHIM.

## Reproduction

Name and count check for a town-wide catalogue (Vivec Telvanni canton).

## Repair

Decision (8 October 2026): under CHIM the harvest runtime keeps loading the town's per-region
catalogues, by region, on the engine side. No merged catalogue and no new file names.

Frame map entities: a CHIM frame map carries only `worldspawn` (with `_chim_frame`), the `aw_npc`
entities and one `info_player_start`; any other entity class is refused with an accounting report
([CHIM-PAYLOAD-PARITY-33](CHIM-PAYLOAD-PARITY-33.md)).

## Verification

Pending: CHIM engine loads the per-region catalogues for a frame.

## Prevention

The builder's harvest name gate and the FFS name-length rule stay as they are; a CHIM test that a
frame's harvest comes from its regions' catalogues.
