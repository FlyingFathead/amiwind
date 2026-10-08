# BUILD-PLUGIN-SOUNDS-32: A GOG image includes 8 converted sounds that only an official plugin uses

## Status: 8 October 2026

Open. Found by the GOG/Steam loose-file A/B (measured on both installations, no repository change).

## Symptom

`prepare_media_assets.discover` converts every loose sound, so a GOG image carries 8 extra
`sound/fx/envrn/ent_*.wav` conversions used only by `entertainers.esp`; `media-coverage.json`
differs from a Steam build.

## Where

`tools/prepare_media_assets.py` (`discover`, `stage_catalogue`).

## How it happened

Discovery walks the loose folder instead of following game records.

## Why it was not caught

Only one edition was ever built.

## Reproduction

Build media from a GOG and a Steam installation and compare the sound list.

## Repair

Not yet: convert sounds referenced by the masters AmiWind loads, not every loose file.

## Verification

Pending.

## Prevention

Edition A/B of the builder outputs.
