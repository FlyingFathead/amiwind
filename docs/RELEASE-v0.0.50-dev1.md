# AmiWind v0.0.50-dev1: The Doors: Riders On The CHIM (in development)

Development snapshot, 24 October 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.49](RELEASE-v0.0.49.md).

v0.0.50 is "The Doors: Riders On The CHIM": every exterior entrance in the game linked to its interior, and every way
back out linked too (the maintainer's decision of 24 October 2026;
[roadmap](ROADMAP.md#v0050-the-doors-riders-on-the-chim-24-october-2026)). The actor
sizes, the game's scripts, object state in rooms, Bloodmoon and the Morrowind-style UI work move to v0.0.51.

This snapshot is the build where only the version changed against v0.0.49. It was written to check that a version
change rebuilds only the engine and the image, and that the CHIM world comes from the cache. No game change yet.

## New since v0.0.49

- **No hidden version read in the build stages.** The v0.0.49 final rebuilt the CHIM world: the version was read
  lazily on first use, so the CHIM stage's read trace recorded the version code although the stage never used the
  number. The four tools that show the version now read it themselves, and a gate test refuses a lazy module
  attribute in the build tools ([BUILD-VERSION-GETATTR-TRACE-49](bugs/BUILD-VERSION-GETATTR-TRACE-49.md)).
- **Door audit of the v0.0.49 image.** Against every load door of the base game's master file: 3,133 load doors,
  3,027 lead where they should and 106 do not yet (85 ways back out of rooms around Vivec and Ebonheart, 15 entrances
  that no door list carries, 6 to check by hand). The fix is v0.0.50's work
  ([CHIM-REGION-DOORS-NO-ROOMS-48](bugs/CHIM-REGION-DOORS-NO-ROOMS-48.md)).
- **Real hardware and graphics cards.** The hardware page now leads with the machines AmiWind aims at: FPGA
  accelerators, PiStorm and new machines such as the THEA1200, with a classic 68060 as the floor. Hardware 3D through
  Warp3D is a research item: an RTG screen alone leaves all the drawing on the CPU
  ([AmiWind on real hardware](REAL_HARDWARE.md),
  [roadmap](ROADMAP.md#research-hardware-3d-through-warp3d-v0050-study-24-october-2026)).

## Known in this build

- Everything in [v0.0.49's known items](RELEASE-v0.0.49.md#known-in-this-build) still applies.
- Everything else is in the [bug register](BUGS.md).
