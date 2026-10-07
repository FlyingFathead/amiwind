# AmiWind v0.0.30-dev4 - The Temple

Development build. It contains everything in
[v0.0.30-dev3](RELEASE-v0.0.30-dev3.md) plus a crash fix and new controls.
Maps and other game files are unchanged from dev3.

## Fixed: crash on a region change in Seyda Neen

The opening sequence kept pointers to its actors across region changes. After
a region reload one of them could point past the end of the new entity list,
and the game stopped with `NUM_FOR_EDICT: bad pointer`. Stale actors are now
dropped before use. On the same scripted route dev3 crashed in 2 of 2 runs;
the repaired engine crossed all planned sub-cells in 3 of 3 runs.
([INTRO-ROLES-30](bugs/INTRO-ROLES-30.md))

## New: Options > Controls

Options has a Controls page listing the gameplay actions and their keys.
Select an action, press Enter, then press the new key. Escape cancels; Delete
clears. Reset to defaults restores the shipped bindings. Greyed rows show
planned actions (inventory, quick keys, magic). See [keymaps](KEYMAPS.md).

## Changed: arrow keys move like W/A/S/D

Up and Down walk forward and back; Left and Right strafe. The mouse turns.
Existing saved key files keep their own Left and Right bindings; Up and Down
are added only where they are unbound.

## Still open

Seyda Neen cell-crossing pauses (now measured: about 1.0-1.5 s per sub-cell
load on the test route), lantern glow and static fires, dark NPCs in some
interiors, WinUAE music cuts at Enter and race selection, and the items listed
in the [dev3 notes](RELEASE-v0.0.30-dev3.md). See the [tracker](BUGS.md).
