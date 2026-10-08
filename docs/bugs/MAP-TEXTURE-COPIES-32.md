# MAP-TEXTURE-COPIES-32: Every map carries its own copy of every texture it uses

## Status: 8 October 2026

Open. Found by the world streamer measurement (Balmora's 64 shipped maps,
extrapolated to the island).

## Symptom

Quake maps embed their textures, so the same texture is stored in hundreds of maps:
about 1.4 GB island-wide against a few MB if each were stored once. Per-map names
(`surfaceN`) hide identical textures; only a pixel hash finds them.

## Where

The converters and the BSP texture lump.

## How it happened

Quake's map format embeds textures.

## Why it was not caught

Per-map size checks only.

## Reproduction

Hash texture pixels across all maps.

## Repair

Not yet: a shared texture store loaded once (part of the world streamer).

## Verification

Pending.

## Prevention

The builder reports texture bytes stored more than once.
