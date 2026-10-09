# BUILD-PLUGIN-SOUNDS-32: A GOG image includes 8 converted sounds that only an official plugin uses

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | media discovery (tools/prepare_media_assets.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | low: A GOG image carries 8 extra converted plugin sounds, so its outputs differ from a Steam build. |
| Family | Morrowind editions, archives and inputs (`game-data-editions`) |

<!-- END GENERATED FACTS -->

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

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Morrowind editions, archives and inputs (`game-data-editions`). The builder reads the owner's data the way Morrowind does (archive order, loose files) and checks inputs against known versions. See [families](README.md#families).

- [ASSETS-ARCHIVE-ORDER-32](ASSETS-ARCHIVE-ORDER-32.md): Asset readers ignore the Tribunal and Bloodmoon archives, so some textures are pre-expansion versions
- [BUILD-EDITION-DIFFERENCES-32](BUILD-EDITION-DIFFERENCES-32.md): GOG and Steam editions produce different builds (fonts, loose files)
- [BUILD-EDITION-SKY-32](BUILD-EDITION-SKY-32.md): Night sky and sky palette outputs depend on the Morrowind edition (loose .tga read before archive .dds)
- [BUILD-EXPANSIONS-31](BUILD-EXPANSIONS-31.md): Tribunal and Bloodmoon cannot be converted with today's tools
- [BUILD-INPUTS-UNVERIFIED-32](BUILD-INPUTS-UNVERIFIED-32.md): The builder does not check user inputs (Morrowind data, Amiga libraries) against known versions

<!-- END GENERATED CATEGORY -->
