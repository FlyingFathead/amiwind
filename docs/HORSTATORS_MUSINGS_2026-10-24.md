# Horstator’s musings (24 Oct 2026): “[C]hunks and [H]eaps in [M]emory”

_Last updated with AmiWind v0.0.51 (25 October 2026)._

> Next musings, 25 Oct 2026: why AmiWind is free, and the artisan, the engineer and the door handle. See
> [[C]raft, [H]andles, [I]ntent and [M]eaning](HORSTATORS_MUSINGS_2026-10-25.md).

It's been almost a month at this, and things are starting to take form. The whole of Vvardenfell is in: every
exterior on the CHIM engine, the base game's interiors on the shared room store, and the people standing where the
original game put them. That is what v0.0.48 is named for.

But efficiency still remains a question, both in the gameplay and in the build system itself.

## In the game

The target hasn't moved. It has to run on a real Amiga: 16 MB of Fast RAM must work, and 32 MB should run well. Now
that the content is in, the game has to be optimized accordingly: what sits in memory, what streams in and when, and
what the Amiga never has to draw at all.

## In the build system

Now that the whole island is in, the build times need to be as quick as possible. The biggest hurdle is the test loop:
a single issue shouldn't take ages to recompile. When it does, every fix and every feature behind it waits, and the
backlog grows. The release builds of v0.0.48 showed it plainly. A release candidate rebuilt from the previous
development build took about an hour and a half where minutes should have done, because a version label alone made
the whole CHIM world count as changed.

Two things already help:

- **The MiniWind builds** ([MINIWIND.md](MINIWIND.md)): build just the parts you need, test them, and go back to the
  whole island when they work.
- **The build monitor** in the [AmiWind Toolkit](AMIWIND_TOOLKIT.md), a web UI on localhost: it shows the current
  build live, stage by stage, with the cores each stage uses, so you can see whether there are bottlenecks in the
  overall process, such as a step running on two cores out of twenty-four or a stage that should have come from the
  cache.

The rest comes first in the next version ([build turnaround first](ROADMAP.md#build-turnaround-first-24-october-2026)):
rebuild only what changed, so that a release built from its finished candidate reuses everything but the engine and
the final image; every step on every core; and fast tools around the build, the bug register included.

## Why now

The next big piece is the game logic: MWScript, object states, the scripts that make Morrowind Morrowind. That will
mean hundreds of small fixes, each one tried, built and checked. With a slow loop that's a year. With a fast one it's
weeks. So the build gets fast first, and then the game gets its scripts.
