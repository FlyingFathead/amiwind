# AmiWind v0.0.42: Things Are Starting To Look Pretty Khuul

Released 17 October 2026. Running on CHIM Engine v0.2.1. Previous release:
[v0.0.41](RELEASE-v0.0.41.md); development snapshots [v0.0.42-dev1](RELEASE-v0.0.42-dev1.md) and
[v0.0.42-dev2](RELEASE-v0.0.42-dev2.md). Working plan: [v0.0.42](../../history/plans/PLAN-v0.0.42.md).

More of the island on CHIM, the clouds back in the sky, and the first look of the original interface: the HUD
boxes and an inventory that is starting to take its original shape.

## What changed since v0.0.41

### The world

- **More of Vvardenfell on CHIM:** 1,168 of the island's 1,395 exterior cells (776 in v0.0.42-dev1), 392 more:
  the light cells of the CHIMport by weight, each measured again with the current builder first (all with at
  least 2 MB of memory to spare), most of them in the Ashlands, Molag Amur, the West Gash, Sheogorad, the
  Ascadian Isles, Red Mountain and the Grazelands. Places that join include Molag Mar, Pelagiad, Gnisis,
  Ghostgate, Bal Isra, the Arvel and Dren Plantations, Falasmaryon, Kogoruhn, Valenvaryon, Zergonipal, Mount Kand,
  Mount Assarnibibi and the Fields of Kummu, and 19 of the 24 inland lava cells. 227 cells stay classic for now,
  each with its reason in the progress tracker: towns go onto CHIM whole, so Ald-ruhn, Maar Gan, Suran, Vas, Vos
  and Balmora's outskirts wait for their heaviest cell; the medium cells are the next batch; and 98 empty sea
  floor cells whose original land records carry no heights wait for a builder fix.
- **The clouds are back.** v0.0.40 and v0.0.41 shipped a flat sky with no clouds: a wider Seyda Neen scenery area
  changed the textures the palette is picked from, the cloud sky conversion refused the new palette and the build
  used a flat stand-in with only a warning. The cloud sky is now converted for whatever palette the build has, and a
  stand-in sky stops the build: [SKY-FLAT-PALETTE-DRIFT-41](../../bugs/SKY-FLAT-PALETTE-DRIFT-41.md).
- **No more popping buildings:** where the streaming memory ran full (Ebonheart, Khuul) the engine kept dropping
  and reloading distant pieces, so outlines popped in and out while standing still. Pieces are now released only
  when that makes room, and the world index is 719 KiB smaller, which leaves more room for every map:
  [CHIM-ZONE-RELEASE-FLICKER-42](../../bugs/CHIM-ZONE-RELEASE-FLICKER-42.md).
- **Vivec's giant mushrooms are closed again:** towns and CHIM areas reduced the mushroom caps with a method that
  pulled their rims apart; they now keep their seams, and the seam gate fails on any tear:
  [MESH-VIVEC-CAP-GAP-38](../../bugs/MESH-VIVEC-CAP-GAP-38.md).
- **Doors in CHIM region cells** (Khuul and others) show their entrance again, with "Interior unavailable" where the
  room is not converted yet: [CHIM-REGION-DOORS-NO-PROMPT-42](../../bugs/CHIM-REGION-DOORS-NO-PROMPT-42.md).
- **Four characters stand on the ground** where the game places them (Lucan Ostorius, Paur Maston, Viatrix Petilia
  and Umbra), as the original game drops every walking character onto the ground when its cell loads; the cell
  west of Khuul joins CHIM in this build, the others wait for Suran and Ald-ruhn.
- **Vivec's interiors:** 141 rooms (130 in v0.0.41), the four Arena rooms behind Arena Waistworks among them, and
  Vivec himself in his palace.

### The interface

- **The inventory is starting to take its original shape:** the original title bar with the equipped weapon's
  name, item icons from the game's own art, and the character shown as a still picture in the original inventory
  pose, drawn once when the window opens or the equipment changes (about 0.1 ms a frame instead of 117 ms for the
  old turning preview on a slow 68040). The inventory is still work in progress.
- **The HUD's weapon and magic boxes use the original art:** the equipped weapon's icon with its condition bar,
  and the selected magic item on the original magic backdrop with its charge bar. See [the HUD](../../HUD.md).
- **Far detail** (Options > Far detail): Full, Light, Strong or Strong + small faces. **Strong is the new
  default** (decided by the maintainer): 17-27 % off the 3D time in Balmora on a slow 68040; distant small
  objects drop out a little before the fog hides them. A saved setup from an earlier version keeps Full until
  Strong is chosen. [The far test](../../performance/FAR-TEST.md).

### For testers

- **Extra Fast RAM is used by itself:** free Fast RAM beyond a margin for the system becomes CHIM's cache (the
  world already seen stays in memory, and more is fetched ahead in the direction you travel), with no upper limit
  but the machine. 16 MiB plays exactly as before. A notice on the startup logo says how much was found (M skips
  it for this start), Options > Extra RAM turns it off, and the console says what happened on every start. In the
  emulator at 128 MiB the streaming memory no longer runs full at Seyda Neen or on Ebonheart's plaza:
  [real hardware](../../REAL_HARDWARE.md#extra-ram-is-used-automatically).

- **Inspect mode:** its line and the pinned details sit at the bottom of the screen, underneath the health, magic
  and fatigue bars (the bars move up while it is on), a right click leaves the mode, and a pin on the CHIM world
  names the mesh and the Morrowind reference it hit.
- **A debug torch (test only):** while AmiWind is a preview, the player leaves the census office with a torch that never burns out.
- **`dbg tp mark`** (or `dbg tp marker`) goes to the marker set on the map.
- **`aw_star_twinkle`** turns the stars' faint twinkle on or off (on by default; it shows once the night clouds
  clear around midnight).
- **No head bob in noclip;** the walking bob comes back as it was when noclip ends.
- **Fast RAM in the launcher:** the FS-UAE launcher and the WinUAE presets offer 16 MiB (the default, as before),
  128 MiB, 256 MiB, 512 MiB, 1 GiB, 1.5 GiB or a custom size, for testing like an accelerated Amiga
  ([FS-UAE launcher](../../FS-UAE-LAUNCHER.md#fast-ram)).
- **A 68060 engine on the game disk**, picked at boot on a 68060: [AmiWind on the 68060](../../68060.md).
- **Camera marks, an orbit camera and timedemo on CHIM maps** for measurements:
  [camera marks](../../CAMERA_MARKS.md), [hardware benchmark](../../HARDWARE-BENCHMARK.md#timedemo).

### The build tools

- One worker pool for the CHIM checks, each stair flight walked once and kept, a time estimate that follows the
  work, a resource plan before every build, and a size ledger against the previous release.

## Known in this build

- [UI-INVENTORY-FONT-TABS-42](../../bugs/UI-INVENTORY-FONT-TABS-42.md): the inventory categories are plain text in the
  console font, not buttons in the game's font as in the original.
- [UI-INVENTORY-ORIGINAL-LAYOUT-42](../../bugs/UI-INVENTORY-ORIGINAL-LAYOUT-42.md): the inventory lacks the original
  encumbrance bar, armour rating and icon grid.
- [HUD-STATS-29](../../bugs/HUD-STATS-29.md): spells cannot be selected yet (no spell list), so the magic box shows magic
  items only.
- [NIGHT-WINDOWS-LOST-CHIM-36](../../bugs/NIGHT-WINDOWS-LOST-CHIM-36.md): windows do not glow at night; the window data for
  the CHIM towns comes after the CHIMport.
- [VIVEC-ROOM-PRECACHE-LIMIT-42](../../bugs/VIVEC-ROOM-PRECACHE-LIMIT-42.md): Vivec, Telvanni Tower is left out (one model
  slot over the engine limit).
- [MESH-EBONHEART-DRAGON-PEDESTAL-42](../../bugs/MESH-EBONHEART-DRAGON-PEDESTAL-42.md): the dragon statue in Ebonheart's
  plaza floats without its pedestal.
- [INTERIOR-CREATURES-MISSING-41](../../bugs/INTERIOR-CREATURES-MISSING-41.md): only listed creatures are placed in
  interiors (Vivec first).

See the [bug register](../../BUGS.md) for everything else.
