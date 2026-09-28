# v0.0.18-dev2 — ship introduction and speaking faces

This checkpoint extends dev1. It implements the first ship sequence, not the
complete Morrowind introduction or a general MWScript interpreter. See
[authored sequence and adapter scope](INTRO_SCRIPT_MAPPING.md).

## Play it

The established town-center demo remains the default. Press Escape and choose
New game to enter the ship introduction, or use `aw_new_game` in the console.
Enter a name when Jiub asks; accept the movement prompt when the guard arrives.
`aw_intro_status` reports the current script stages. The existing debug scene
picker and free exploration remain available. Save/Load remain disabled.

## Implemented

- Original Jiub and escort speech, name entry, action gates and a bounded native
  state adapter driven by actual voice completion. The upper-deck guard's two
  proximity lines are converted and connected to the same speech controller.
- Original prison path grid and walking animation; guarded stair/slide movement,
  local obstacle steering, waiting for a following player and explicit blocked
  route reporting. Actors are never teleported past a failed route.
- Private conversion of ten actor appearances, including female body/equipment
  selection. Each has eight idle, four talking, one blink and eight walking poses.
  Authored head morphs use a four-level 25Hz audio envelope synchronized to the
  playback clock. This is amplitude-based mouth animation, not phoneme matching.
- All 21 base-game CharGen Say clips and original subtitle text converted from
  owned data, including exact WAV-to-MP3 stem resolution for this distribution.
  Later dock/Census clips are prepared but their gameplay stages remain open.
- Two localized, looping ship-water emitters from the original barrel scripts.
  The ship no longer inherits the exterior renderer's ambient-light minimum;
  existing baked lights remain. No night-time clock is implied by a dark hold.
- Distinct red health, blue magicka and green fatigue artwork. An audited set of
  unused palette slots supplies the colors without changing world texture pixels,
  lighting tables or console glyphs. Magicka/fatigue remain visual placeholders.
- Optional outer gold frame, OFF by default, under Options. Lower dialogue panels
  retain their borders and rise into the reserved band below the world view.
- Guided owned-data builds include the intro conversion stage. Original game
  assets and extracted scripts stay private. No Lua dependency is added.
- Journal renamed to `HORSTATORS_JOURNAL_2026-09-28.md`. Player height comparison
  against the original snapshot found unchanged eye height and actor geometry.

## Verification

172 host tests passed, including speech timing, malformed envelope/path data,
blocked navigation, actor step rollback, female appearance fallback, palette-slot
protection, menu controls and build-stage ordering. Full native compilation and
HDF payload readback passed. Native validation is recorded in the private evidence
and in IMPLEMENTATION_JOURNAL.md. The guard completed descent, ascent and final
instructions with failed=0. Diagnostic player positions exercised the NPC route;
a complete manual player walk/hatch transition remains uncertified.
Reference: FS-UAE 3.1.66, A1200/AGA, 68040/FPU/JIT, 2MiB Chip + 16MiB Fast,
9MiB game heap. No stock-A1200 or physical-hardware performance claim.

## Still open

The ship adapter ends on a scene change. Dock race/sex/head/hair selection and
3D preview, Census class/birthsign/review, papers/books, ring/package progression,
full topic dialogue, persistent character state and saves are not implemented.
The intro still uses the calibrated Nord camera fixture; race-dependent camera
selection is pending. Actor-to-actor collision and combat remain open. Town
voices still use the earlier greeting selection; the varied condition-aware pools
are only audited. Main-menu background, day/night, waiting, additional interiors,
Silt Strider and the reported terrain defect remain separate work.

Minor hull/view defects and alias-cache reload overhead remain under investigation.
Missing required assets or a blocked route unlock movement for inspection and
report failure; this must not be mistaken for completed story progression.

## Packages

The full public source ZIP is the recovery copy. The incremental ZIP applies to
dev1 with the journal rename; its receipt lists exact baseline hashes and any
removed files. Move that receipt outside the checkout before the owner's public
release check. The private playable contains the untouched built HDF, owned ROM,
matching presets, conversion receipts and native evidence. Never publish it.
Each archive has a SHA-256 companion. The owner handles commit/tag/publication. The development audit and failed
approaches are retained in IMPLEMENTATION_JOURNAL.md.
