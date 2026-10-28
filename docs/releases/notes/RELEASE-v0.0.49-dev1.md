# AmiWind v0.0.49-dev1: build turnaround first (in development)

Development snapshot, 24 October 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.48](RELEASE-v0.0.48.md).

The first step of v0.0.49 is the builder, before game logic: slow builds hold back every fix behind them
([roadmap](../../ROADMAP.md#build-turnaround-first-24-october-2026)). No game change yet.

## New since v0.0.48

- **A version change no longer rebuilds the CHIM world.** The version file counts in a stage's key only when the
  stage shows the version in its output (the engine, the image, the tracker data); the CHIM world's records read it
  only for provenance, which keys nothing. v0.0.48 had to ship its candidate's image as the final because the label
  alone re-keyed the whole world ([BUILD-CHIM-KEY-VERSION-48](../../bugs/BUILD-CHIM-KEY-VERSION-48.md)). A gate test checks
  every stage the builder starts.
- **Release candidates and finals reuse like development builds.** The caches are keyed by content, so the release
  kind no longer switches one off; `--release-from-scratch` (and every `--clean` build) builds a release version from
  scratch, the reproducibility check ([build cache](../../BUILD_CACHE.md)).
- **Real hardware.** The second real-machine figure: an A3000 with a 68060 at 80 MHz through RTG on the tester's own modified build, about 0.6 to 0.7
  frames per second on a short timedemo; the hardware page now says how to show the frame rate and run a comparable
  timedemo, and one standard timedemo is planned ([AmiWind on real hardware](../../REAL_HARDWARE.md),
  [BENCH-NO-STANDARD-DEMO-48](../../bugs/BENCH-NO-STANDARD-DEMO-48.md)).
- **Bug register.** The v0.0.48 release night's late stops are registered (among them
  [BUILD-SIZE-GUARD-LATE-48](../../bugs/BUILD-SIZE-GUARD-LATE-48.md),
  [RELEASE-INCLUSION-CHECK-LATE-48](../../bugs/RELEASE-INCLUSION-CHECK-LATE-48.md) and
  [BUILD-IMAGE-NO-RESUME-33](../../bugs/BUILD-IMAGE-NO-RESUME-33.md), seen again).
- **Release records.** The previous-release record and the size baseline now describe v0.0.48; its payload is
  3.70 GiB.

## Known in this build

- Everything in [v0.0.48's known items](RELEASE-v0.0.48.md#known-in-this-build) still applies.
- The CHIM world is built once more in this version: the code that writes it changed. After that, a version-only
  step rebuilds only the engine and the image; this snapshot's build is the first proof.
- Everything else is in the [bug register](../../BUGS.md).
