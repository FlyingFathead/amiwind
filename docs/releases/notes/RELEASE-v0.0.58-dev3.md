# AmiWind v0.0.58-dev3 (in development)

Development snapshot, 31 October 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.57](RELEASE-v0.0.57.md).

The third snapshot of v0.0.58, "Time To Talk". The game needs 32 MB of Fast RAM, and the emulator presets of this
snapshot have it. What the earlier snapshots brought is in the [dev2 notes](RELEASE-v0.0.58-dev2.md) and the
[dev1 notes](RELEASE-v0.0.58-dev1.md). This snapshot is for testing in game; the new parts below have not been
checked in game yet.

## New since dev2

- **The cliff racer is drawn whole.** The creature bake kept a thin part whole when its size reduction would have
  collapsed it, so the wings join the body and the stray spike is gone. Every creature model is checked for the same
  fault; the one still found is listed below.
- **The character restart debug command no longer crashes** when it is used after the Halloween scene in Seyda Neen:
  a new server, a reload of the same map included, resets the scene and the ambient sound slots first. The command
  also works from the main menu, where it starts a new game straight into Seyda Neen as the census would leave you.
- **An NTSC machine starts.** Without a PAL screen mode the engine takes the default monitor's mode instead of
  stopping.
- **The presets show only the drawn picture.** The FS-UAE and WinUAE presets (the slow accelerator preset too) crop to
  the 320x200 picture, which fills a widescreen monitor at no cost to the game. The Raspberry Pi boot image does the
  same and no longer prints the first-login SSH banner that did not apply.
- **Dialogue.** The journal's topic pages reach the dialogue through pointers set at start, and the dialogue fills the
  values the page shows before the interface reads them. Exhausted topics are drawn dimmer. Topic names on the
  journal's topic pages are links that open that topic's page, and a "journal updated" notice shows whenever a quest
  advances (as in OpenMW, without a sound). Links inside the dated quest entries come later.
- **Builds.** The performance check of a build judges a section run on other cores than its baseline by CPU seconds
  per unit, and each row names its basis. The building guide now says what a build costs in time and in machine.
- **Documents.** The Raspberry Pi 4B reference figures and what the published PiStorm numbers mean are written down,
  with the PAL ceiling for European machines and Seyda Neen with the Halloween scene as the heavy case. The
  [roadmap](../../ROADMAP.md) has the plan first made for v0.0.59 folded into v0.0.58.

## Known in this build

- The netch bull's reduced model loses a stretch of one leg
  (CREATURE-NETCH-BULL-LEG-REDUCED-58, open in the [register](../../BUGS.md)).
- The prison ship's hold draws slower than the Arena Pit, and Seyda Neen is heavy on the Raspberry Pi 4B
  ([PRISON-SHIP-RENDER-COST-56](../../bugs/PRISON-SHIP-RENDER-COST-56.md)).
- Casting the spells you make, and using items you enchant, wait for player casting (a later version).
- The fuller combat sounds are still behind `dbg combat sounds on` until they are checked in game.
- Some rooms still load in after you arrive ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).

## Not yet checked in game

- The cliff racer's whole shape, the restart command after the Halloween scene and from the main menu, the cropped
  presets and the journal's topic pages.
