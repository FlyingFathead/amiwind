# AmiWind v0.0.49: Build Turnaround

Released 24 October 2026. Running on CHIM Engine v0.2.2. Previous release: [v0.0.48](RELEASE-v0.0.48.md);
development snapshot [v0.0.49-dev1](RELEASE-v0.0.49-dev1.md).

A builder release on v0.0.48's game. v0.0.48 had to ship its release candidate's image as the final because a new
version number alone rebuilt the whole CHIM world. The version no longer keys the CHIM world. This release's final
was built from the v0.0.49-dev1 build's caches with only the version changed: 39 of 43 stages were reused, but the
CHIM world was built once more, because the first form of the fix left a trace the cache could not verify
([BUILD-VERSION-GETATTR-TRACE-49](../../bugs/BUILD-VERSION-GETATTR-TRACE-49.md), repaired for v0.0.50, whose first
version-only build is the proof). The game is the same as v0.0.48's: every exterior cell of Vvardenfell and 1,132 of the 1,134 base-game
interiors on CHIM, 32 MB of Fast RAM the safe minimum.

## What changed since v0.0.48

- **A version change rebuilds only what shows the version.** The version file counts in a stage's key only when the
  stage shows the version in its output (the engine, the image, the tracker data); the CHIM world's records read it
  only for provenance, which keys nothing. A gate test checks every stage the builder starts
  ([BUILD-CHIM-KEY-VERSION-48](../../bugs/BUILD-CHIM-KEY-VERSION-48.md)).
- **Release candidates and finals reuse like development builds.** The caches are keyed by content, so the release
  kind no longer switches one off; `--release-from-scratch` (and every `--clean` build) builds a release version from
  scratch, the reproducibility check ([build cache](../../BUILD_CACHE.md)).
- **The docs say what the game is today.** The front page lists what works and what does not yet; the progress
  tracker, the FAQ, the architecture page, the CHIM pages and the Linux, Windows, WinUAE and FS-UAE guides name the
  v0.0.48 presets, 32 MB of Fast RAM and the interiors on CHIM.
- **Real hardware.** The second real-machine figure, an A3000 with a 68060 at 80 MHz through RTG on the tester's own
  modified build (about 0.6 to 0.7 frames per second on a short timedemo), and how to show the frame rate and run a
  comparable timedemo
  ([AmiWind on real hardware](../../REAL_HARDWARE.md)); one standard timedemo is planned
  ([roadmap](../../ROADMAP.md#one-standard-timedemo-for-real-amigas-v0049)).
- **Release records.** The previous-release record and the size baseline describe v0.0.48.

## Known in this build

- Everything in [v0.0.48's known items](RELEASE-v0.0.48.md#known-in-this-build) still applies.
- [BUILD-VERSION-GETATTR-TRACE-49](../../bugs/BUILD-VERSION-GETATTR-TRACE-49.md): a version-only rebuild still rebuilt the
  CHIM world here; repaired on the v0.0.50 line.
- [BUILD-CHIM-STAGE-SERIAL-TAIL-36](../../bugs/BUILD-CHIM-STAGE-SERIAL-TAIL-36.md): the CHIM stage's validation and world
  pack still run on a few cores for about three minutes of a build.
- [BENCH-NO-STANDARD-DEMO-48](../../bugs/BENCH-NO-STANDARD-DEMO-48.md): real-machine figures cannot be compared yet.
- Everything else is in the [bug register](../../BUGS.md).
