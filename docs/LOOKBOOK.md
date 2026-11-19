# The confirmed look book

_Last updated with AmiWind v0.0.67-dev2 (18 November 2026)._

Every look and behaviour the maintainer has confirmed in play is kept as a page of the look book, and every development
build is checked against the whole book before it is delivered. A regression of something already confirmed is then
caught by the build, not found again in play. The pages, their reference pages and an overview are in
[docs/lookbook](lookbook/README.md).

## What a page is

A page is one confirmed thing (register: [REGRESSION-GUARD-MISSING-67](BUGS.md)). It names:

- what the maintainer confirmed, when, and on which version;
- the register entries it guards, and the feature pages that describe it;
- the code it lives in: the files and functions (the modules) of the confirmed behaviour;
- how it is checked. Numbers are the main check, pictures the second.

The book is `tests/lookbook/pages.json`. A page is one of four kinds:

- **session**: scripted steps in the emulator, written in the language of the gameplay journeys
  ([GAME_RECORDER.md](GAME_RECORDER.md#gameplay-journeys)) in a file of `tests/lookbook/`. The steps read the game's own
  state (`probe`, `pick`, `expect`); `expect NAME near VALUE TOL` checks a number within a tolerance, and `still NAME`
  takes a picture that is compared with the page's reference pictures over its regions (when it has them);
- **journey**: the checks of named steps of a journey that already runs on every build (the opening journey), read from
  that journey's result on the same image;
- **image**: a check of the image's own files (a model's triangles, vertices and surface against its source);
- **gate**: a data check that runs in the gate itself, without the emulator (for example the dialogue's answer choices
  against the original's rules for every character).

The book also lists the pages still to write: every register entry with a step confirmed by the maintainer, and every
confirmed item reported broken again.

## Running the book

All session pages run in one emulator session, at 32 MB of Fast RAM and without warp: a short start (a test character
after the census office at Seyda Neen), then each page in turn. A page that stops the session fails with its reason and
the pages after it go on in a new session. `tools/lookbook.py`:

- `check`: the book, its page files, the marked code and the reference pages;
- `compose OUTDIR [--pages A,B] [--from PAGE]`: the session script (`lookbook-session.txt`) and the composed journey;
- `judge OUT SCRIPTS:RUN ...`: one line per page and check, the pictures compared, `LOOKBOOK-REPORT.json` and `.md`, and
  the last line `LOOKBOOK RESULT PASS n/n pages` or `LOOKBOOK RESULT FAIL m of n pages: PAGE, ...` (exit 1 on a miss);
- `render [--check]`: the reference pages in [docs/lookbook](lookbook/README.md).

A delivery runs the book on the build's image after the image is made and before the kit; a miss stops it and names
the page.

## Numbers from the engine

Where a page needs a number the console did not give, the engine has a small read-only readout for it:

- `dbg camera held`: the light in the left hand against the hand it is drawn in, in the view now (first or third
  person). It poses the vertices of the arms (or of the body) that hang on the left hand as the renderer draws them,
  places the light as it is drawn, and prints how far the light's attach point and its nearest vertex are from the
  hand. A light floating away from the hand reads several units; a light in the hand under two.

## Marked code

Code a page guards carries a marker around it:

```c
/* LOOKBOOK HELD-LIGHT-IN-HAND: confirmed by the maintainer 2026-11-07 on v0.0.61; a change here must pass this page */
... the guarded lines ...
/* LOOKBOOK HELD-LIGHT-IN-HAND end */
```

A marker is read only in a file of its page's code list, and its date and version must be one of the page's
confirmations. `tests/lookbook/guards.json` keeps the SHA-256 of each marked block as the page last passed it. The gate
fails when a marked block changes, and names the page to run. Once the page has passed on an engine built with the
change, `tools/lookbook.py record PAGE REPORT` records the new block with that run, and the change can be merged. A
marker is never taken out without the page's own tracker item.

## Pictures

A picture is never read as showing that something is missing or present: the frame may not contain it (in the normal
first-person view the left hand can sit below the screen's edge, and shows when the view looks down or in photo mode).
Whether a part is drawn, and where, is a number check (a part's drawn vertices, a grip point against a bone), or
nothing. First-person stills of the hands are taken looking down, looking steeply down and in photo mode with the hands.

A still is a screenshot of the emulator's screen (1024 x 768). A page's reference pictures are the parts of a confirmed
still inside its regions, in `tests/lookbook/ref/<PAGE>/`, made with `tools/lookbook.py reference PAGE STILL RUN`. A still
is compared by the mean difference per colour channel and the share of pixels that changed by more than a fixed step,
each with the page's limit. A page without reference pictures keeps its stills for the next confirmation and counts
only its numbers.
