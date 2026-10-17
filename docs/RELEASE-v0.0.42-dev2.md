# AmiWind v0.0.42-dev2: CHIMport by weight (in development)

Development snapshot, 17 October 2026, in development. Running on CHIM Engine v0.2.1. Previous snapshot:
[v0.0.42-dev1](RELEASE-v0.0.42-dev1.md). Previous release: [v0.0.41](RELEASE-v0.0.41.md). Working plan:
[v0.0.42](PLAN-v0.0.42.md).

The second v0.0.42 snapshot: more of the island on CHIM, the light cells first, then the medium ones
(config/chim-weight-classes.json), plus the work queued after dev1.

## What changed since v0.0.42-dev1

- **The original inventory title bar** with the equipped weapon's name, as in the original
  ([UI-WINDOW-TITLE-BAR-42](bugs/UI-WINDOW-TITLE-BAR-42.md),
  [UI-INVENTORY-HEADING-CENTRE-42](bugs/UI-INVENTORY-HEADING-CENTRE-42.md)).
- **Inventory icons** from the original art for every item that has one
  ([UI-ICONS-INVENTORY-42](bugs/UI-ICONS-INVENTORY-42.md)).
- **Resource plan before every build**: the memory and cores each stage needs, checked before the first stage
  (docs/BUILD_PROFILE.md "Resource plan").
- **Vivec's giant mushrooms are closed again**, and every other mushroom in towns and CHIM areas: their caps are
  reduced without pulling the cap parts apart ([MESH-VIVEC-CAP-GAP-38](bugs/MESH-VIVEC-CAP-GAP-38.md)).
- **Inspect mode (`dbg hud on`) no longer covers the view**: its hint is a row above the XYZ lines, the pinned
  details sit under the view, a pin on a CHIM-area object names its mesh and reference, and a right click leaves the
  mode ([INSPECT-OVER-VIEWPORT-42](bugs/INSPECT-OVER-VIEWPORT-42.md),
  [INSPECT-CHIM-PLACEMENT-UNNAMED-42](bugs/INSPECT-CHIM-PLACEMENT-UNNAMED-42.md),
  [INSPECT-NO-RIGHT-CLICK-EXIT-42](bugs/INSPECT-NO-RIGHT-CLICK-EXIT-42.md)).
- **Debug lines stay out of the view and off the weapon and magic boxes**
  ([HUD-DEBUG-STRIP-OVER-BOXES-42](bugs/HUD-DEBUG-STRIP-OVER-BOXES-42.md),
  [HUD-NOTIFY-OVERLAP-31](bugs/HUD-NOTIFY-OVERLAP-31.md)).
- **No head bob in noclip**, also after crossing into another area; walking brings it back
  ([NOCLIP-BOB-DEFAULT-42](bugs/NOCLIP-BOB-DEFAULT-42.md)).
- **`dbg tp mark`** (also `dbg tp marker`): teleport to the marker you set on the map screen.
- **More Fast RAM for the emulated Amiga, chosen in the launcher**: 16 MiB stays the default; 128 MiB (like a
  68060 accelerator card), 256 MiB, 512 MiB, 1 GiB, 1.5 GiB (the most the emulators give) or a custom size,
  checked against what the emulator can make ([Fast RAM](FS-UAE-LAUNCHER.md#fast-ram)).

## Known in this build

- [VIVEC-ROOM-PRECACHE-LIMIT-42](bugs/VIVEC-ROOM-PRECACHE-LIMIT-42.md): Vivec, Telvanni Tower is left out (one model
  slot over the engine limit).
- [NIGHT-WINDOWS-LOST-CHIM-36](bugs/NIGHT-WINDOWS-LOST-CHIM-36.md): windows do not glow at night.
- [UI-INVENTORY-ORIGINAL-LAYOUT-42](bugs/UI-INVENTORY-ORIGINAL-LAYOUT-42.md): the inventory lacks the original
  encumbrance bar, armour rating and icon grid.
