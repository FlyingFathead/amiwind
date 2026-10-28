# AmiWind v0.0.16: first repository release

Official project: https://github.com/FlyingFathead/amiwind/

By FlyingFathead +- ChaosWhisperer

This is an early demo release. The source, conversion tools, native runtime and
release packages now share **v0.0.16**. The former internal pipeline numbering
is retired from release filenames. The repository has one root, `amiwind/`.

## Changes

- Complete selected AGA engine source is part of `engine/aga/`; builds compile
  that checked-in source, with no separate source-root overlay.
- Guided dependency installation with confirmation, reference-version reporting,
  input structure/size/SHA-256 checks, WSL detection and verified GOG-path offer.
- Default local output in ignored `out/`, expanded game/ROM/build ignore rules,
  and asset-free GitHub Actions compilation with a versioned boot-notice image.
- Shared release version and native-version checks; versioned full public source,
  incremental public source and private playable packages.
- Boot credits and project URL. README state summary, matched-size documentation
  screenshots, modular build and release instructions.
- Ordinary water now uses a blue contents-palette shift instead of the inherited
  warm brown shift. The separate red damage shift is preserved.
- Exterior fog/draw distance defaults to **540**, including menu reset, help,
  generated configuration and the medium-distance key binding. Other distances
  remain selectable.

The AGA runtime incorporates code from id Software's **Quake** and the
**AmiQuake** lineage, modified, extended and adapted for AmiWind. These components
retain their original notices and GPL version 2 licensing; individual v2-or-later
grants remain intact. Host conversion tools and the earlier A500 runtime remain
separately GPL-3.0-only. See LICENSING_AND_CREDITS.md for provenance and exclusions.

## Downloads and patch base

Use `AmiWind-v0.0.16-public-source.zip` for a fresh checkout. It extracts into
`amiwind/`. The incremental archive applies to the **last delivered consolidated
source**, `amiwind-0.12.1.dev1-source.zip`, SHA-256:

```text
73b06b6189de15ad0baa9d43c47541de30fe2e07d83dfcb3e44fdebfd90423c4
```

See PATCH-v0.0.16.json for changed/removed paths. The older v0.0.15-dev2 public
ZIP had two top-level directories; start from the full v0.0.16 ZIP when migrating
that layout. Preserve local changes and older archives.

The private playable ZIP is delivered separately to the owner. It includes the
playable HDF and supplied ROM and **must not be uploaded to the repository or
GitHub release**. The optional public dry-run image contains neither and boots
only to a notice. The five README screenshots are owner-approved documentation;
no reusable original/converted game assets are included in public source.

## Validation and limitations

Validation details are recorded in VALIDATION-v0.0.16.md. Native acceptance uses
FS-UAE 3.1.66, A1200/AGA, 68040/FPU/JIT, 2 MiB Chip and 16 MiB Z3 Fast RAM.
The existing checkpoint-017 scenes and music are reused; this update does not
claim a new full conversion from the original installation.

The underwater/damage combination is checked by compiling the real palette
routines against synthetic inputs. This is not a new drowning or combat system.
Opening/character creation, full conversations, quests, NPC walking and combat
remain unfinished. Original-font UI integration remains a preview study.
Known scene geometry and audio issues remain open.

Hosted GitHub CI, fresh dependency installation, Windows/WSL execution and
physical Amiga performance are not claimed as tested here. The owner-run
publication helper waits for hosted CI before creating the tag/release.
