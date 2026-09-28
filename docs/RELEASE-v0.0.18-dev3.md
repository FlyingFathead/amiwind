# v0.0.18-dev3 — main menu and actor cache correction

Extends the ship-intro checkpoint without changing player height, actor meshes,
collision dimensions or the default town demo opening.

## Changes

- Separate Main Menu: New Game, disabled Load Game, Options and Exit Game.
  In-game Escape offers Return to Game and Main Menu as distinct actions. Leaving
  the active scene requires confirmation; New Game starts the ship introduction.
- Original owned `menu_morrowind.dds` background, converted to a bounded 320x200
  native image. Its dedicated menu palette preserves UI atlas/font colors and
  restores the world palette on leaving the menu or opening the console. This
  avoids tinting the title red through the limited town/status-bar palette.
- Conservative alias bounds cover every packed animation frame. A sphere test
  rejects wholly off-screen actors before fetching their model from the disk
  cache; the existing exact animated-box test still handles surviving actors.
  Geometry, player projection and actor collision bodies are unchanged.
- The original font, lower dialogue panels and optional outer frame settings from
  dev2 remain. Load and Save have no implementation and remain disabled.

## Verification

173 host tests pass, including menu confirmation/disabled entries, front-end
New Game, palette restoration with existing water/damage effects, and conservative
frustum boundary checks. Full Amiga cross-build and every HDF payload readback
pass. Native checks cover leaving the town, menu background/options, New Game,
Jiub/name entry, speaking faces and return to the world palette.

The first native cache trial recorded only three Jiub model loads, two escort
loads and one upper-guard load during the menu-to-intro run, compared with repeated
loads every frame in dev2's route diagnostic. The two runs have different routes
and lengths; this is not a paired FPS benchmark. The 9MiB heap and 16MiB Fast RAM
preset remain; the optional menu artwork/palette adds about 64KiB of resident
storage. Reference remains accelerated FS-UAE/AGA/68040, not physical hardware.

## Remaining work

This is still the first ship adapter, not the complete opening. Dock/Census
creation, persistent character data, full conversations, books/scrolls, NPC
collision/combat, varied town voices, day/night, waiting, Silt Strider and terrain
repair remain open. Main-menu title music and original pixel-perfect menu layout
are not claimed. Minor ship hull defects and audio stalls remain.
See INTRO_SCRIPT_MAPPING.md and RELEASE-v0.0.18-dev2.md for inherited scope.

## Packages

Public complete source is the recovery copy. Public incremental source targets
exactly v0.0.18-dev2; its receipt lists baseline hashes and deletions. Move that
receipt outside the checkout before the public source release check. The private
playable contains owned game/ROM data, presets, conversion receipts and evidence;
keep it private. Each archive includes a separate SHA-256 companion. The owner
continues to handle git commits, tags and publication.
