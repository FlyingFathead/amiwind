# Look book page MENU-COLOURS-GAME-PALETTE

_Generated from tests/lookbook/pages.json with AmiWind v0.0.68-dev7._

The windows of a running game are drawn in the game's own colours, not in the title screen's palette.

## What the maintainer confirmed

The inventory with its item icons and the character picture, the map, the journal, and the stats and magic windows show the game palette's colours after any start, a start from the title menu by a console command included; only the title menu itself shows the title art's own palette. The UI's own colours (white text, greys) keep the entries they had before the scene palette's ice ramp.

- 2026-11-22, on v0.0.68-dev7: the maintainer's report of the regression on the v0.0.68-dev7 image: the map and the inventory with its icons showed a red cast they had not had; the windows of a game started by New Game or Load in v0.0.68-dev6 are the confirmed look

## How it is checked

A scripted session step of the look book (`tests/lookbook/menu_colours_game_palette.txt`), run with every other page in one emulator session on every development build before it is delivered. Its numbers are the check; its pictures are compared with their references where it has them.

- picture `menu-inventory`: the inventory with its item icons and the character picture
- picture `menu-map`: the map screen
- picture `menu-journal`: the journal
- picture `menu-stats`: the stats window
- picture `menu-magic`: the magic window

- after the book's start from the title menu by a console command (no Escape pressed before), each window opened by its key reads back the game palette and not the title art's (aw_ui_palette), on its own screen: inventory, map, journal, and a window over the game for stats and magic
- closed again, the screen is the game's

Status: checked on every development build.

## The code it lives in

- `engine/aga/src/aw_menu.c`: `AW_MenuFrontEnd`, `game_menu` (the title menu: the menu with no game behind it)
- `engine/aga/src/aw_ui.c`: `AW_UIMenuPalette`, `AW_UIColor`, `AW_UIColorUsable`, `palette_command` (the palette the screen is drawn through, the UI's colour picks off the textures' ice ramp, and the readout of both)
- `engine/aga/src/view.c`: `V_UpdatePalette` (the palette each frame is shown through)
- `tools/prepare_ui.py`: `background_packet` (the title art's own palette, which shares only the UI's entries with the game palette)

## The code it guards

No code is marked yet: the marker goes on the code once the page passes.

## Feature pages

- [INVENTORY.md](../INVENTORY.md)
- [WORLD_MAP_AND_JOURNAL.md](../WORLD_MAP_AND_JOURNAL.md)
- [AMIWIND_CONSOLE_COMMANDS.md](../AMIWIND_CONSOLE_COMMANDS.md)

## Register entries

<!-- the register history below is rendered from docs/bugs/bugs.json when the page is rendered -->

### [LOOKBOOK-NO-COLOUR-CHECK-68](../bugs/LOOKBOOK-NO-COLOUR-CHECK-68.md)

The look book checks only numbers on its pages, so a palette change that alters the colours of every confirmed look cannot fail any page. State: open; found in v0.0.68-dev4.
