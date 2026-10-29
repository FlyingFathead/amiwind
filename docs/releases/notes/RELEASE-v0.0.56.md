# AmiWind v0.0.56: Some Velvet Morning

Release, 29 October 2026. Running on CHIM Engine v0.2.2. Previous release: [v0.0.55](RELEASE-v0.0.55.md).

AmiWind on a Raspberry Pi: a Pi 4 that starts straight into the game from a USB stick, the tool to make your own,
and a gallery of Ald'ruhn taken on it. The game needs 32 MB of Fast RAM, and the emulator presets of this release
have it. This is a short release: what was planned for v0.0.56 beyond this moved, openly, to v0.0.57.

## New since v0.0.55

- **Your own AmiWind boot stick for the Raspberry Pi**: `tools/pi_image/make_pi_image.sh` makes a Raspberry Pi OS
  Lite image that starts straight into Amiberry and AmiWind, from your own Kickstart and your own AmiWind image; it
  checks every download and never writes to a disk. A drive on the stick takes a newer AmiWind image as one file
  copy. A Pi 4 runs at 2.0 GHz by default, the setting the game is measured at: read the warning first
  ([your own AmiWind boot stick](../../PI_BOOT_IMAGE.md)).
- **AmiWind on a Raspberry Pi 4 is playable**, the frame rate between about 10 and 50 a second depending on the
  scene; every setting tried and what it gave, why Amiberry and not FS-UAE on a Pi, and what was already right
  ([Raspberry Pi with Amiberry](../../REAL_HARDWARE.md#raspberry-pi-with-amiberry)).
- **Gallery: Ald'ruhn on a Raspberry Pi**, sixteen frames from the afternoon into the night, all taken from Amiberry
  on the Raspberry Pi 4B ([gallery](../../GALLERY.md)).
- **The frame rate comes with `dbg hud`**, small in the bottom-left corner of the screen, in the vanity camera shots
  too; `dbg fps on` shows it without the debug HUD, `dbg fps off` hides it; the Halloween benchmark shows the same
  counter
  ([HUD-FPS-NEEDS-DBG-HUD-56](../../bugs/HUD-FPS-NEEDS-DBG-HUD-56.md)).
- **Teleports**: `dbg tp khuul` (the street outside Thongar's Tradehouse), `dbg tp arenapit` (the Vivec Arena Pit,
  which the old name never reached), and `dbg tp suran` on a street.
- **The release smoke test hops by teleport** to Seyda Neen, Balmora, Vivec, the Arena Pit, Ald'ruhn and Khuul, with
  a shot and the frame time at each.
- **The garbage collector takes a list of any length** (`tools/build_gc.py ... --items-file FILE`).
- **Two new repository checks**: no public link carries a tracking query, and every bug report page is in the
  release file list.

## Known in this build

- Rooms full of detailed objects are the slowest places: the prison ship's hold at the start, Seyda Neen, the Dwemer
  ruins; the original models' polygon count is the cause
  ([PRISON-SHIP-RENDER-COST-56](../../bugs/PRISON-SHIP-RENDER-COST-56.md)).
- On Amiberry, the 68k CPU on its own thread (`cpu_threaded`) ended one load in an engine error: leave it off
  ([SPRITE-BAD-TYPE-THREADED-56](../../bugs/SPRITE-BAD-TYPE-THREADED-56.md)).
- `dbg mwscript on` prints nothing; `dbg mwscript status` shows whether the scripts run
  (DBG-MWSCRIPT-SILENT-56).
- Plants at the foot of a sprite tree are hard to pick
  ([HARVEST-SEYDA-TREE-SPRITE-BLOCKS-PICK-47](../../bugs/HARVEST-SEYDA-TREE-SPRITE-BLOCKS-PICK-47.md)).
- Released without a build from scratch of the line, which moves to v0.0.57.
