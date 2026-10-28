# v0.0.18-dev1 — original-font UI checkpoint

Based on the owner's latest 0.0.17 snapshot, `amiwind-2026-09-28_045110.zip`.
This is a development checkpoint, not a completed opening sequence.

## Implemented

- Private conversion of the original Magic Cards bitmap font at 16px (default),
  14px and 12px, with proportional spacing and three ink shades plus transparency.
- Validated packed native font reader, clipped glyph drawing and word wrapping.
- Original private border corners/edges and red/blue/green bar artwork. Public
  source contains the converter only; missing private artwork uses a fallback.
- Black UI panels; subtitles slide upward from the screen bottom into the unused
  48px band below the 3D viewport. Longer text pages within that band.
- Main menus use the proportional font. The console and compact diagnostics keep
  their existing atlas. `dbg ui font 16|14|12|fallback` selects UI variants;
  `dbg ui preview` auditions the panel with a development sentence.
- Health bar reads player health. Magicka/fatigue bars are full-value visual
  placeholders: no resource consumption or recovery mechanics are claimed.
- AGA/ECS display border blanking, leaving world palette index zero intact.
- Owned-data image builds automatically convert the UI assets when available.

## Verification and limits

163 host tests pass, including real native UI clipping, malformed-font rejection
and bounded wrapping. The complete native engine cross-compiles. A private image
was rebuilt with current QuakeC and existing validated geometry/music, and every
HDF payload was read back against its source bytes. Emulator checks cover font
variants, fallback, menu/options, console, multiple subtitle pages, town and ship.
Reference: FS-UAE 3.1.66, A1200/AGA, 68040/FPU/JIT, 2MiB Chip + 16MiB Fast.
No physical-machine or stock-A1200 performance claim. Captures/logs are private.

The old arbitrary centerprint lifetime is now a paged 8-second subtitle default;
scripted voice completion still needs its dedicated speech controller. The band
fits a speaker plus one 16px text row at 320x200. Full topic dialogue, interactive
creation screens, live magicka/fatigue, minimap, inventory and hotkeys remain open.
The intro, facial animation, guard navigation, additional interiors, day/night,
waiting and Silt Strider are subsequent milestones, not completed by this UI work.

The source reader now accepts additional Census Office item record types rather
than failing on the original registration dagger. This does not spawn those items.

## Packaging

Complete source and incremental public source contain no original/converted game
assets or ROM. The incremental receipt identifies the exact baseline file hashes;
apply it only to the matching latest snapshot. Private playable contains the HDF,
owned ROM and matching versioned emulator presets. Each archive has a SHA-256 file.
The owner continues to handle publication.
