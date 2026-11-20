# Look book page DOCK-GUARD-POST

_Generated from tests/lookbook/pages.json with AmiWind v0.0.67._

In the opening the dock guard walks to his post by the census office door and is not caught in a pier post.

## What the maintainer confirmed

After the race choice the dock guard walks along the pier to his post beside the census office door, around the posts, and the player walks past him into the office.

- 2026-11-18, on v0.0.67-dev2: the maintainer's report of the regression: the walk had worked from v0.0.66-dev2 (fixed there, confirmed in play by the opening journey on v0.0.66-dev5 and every journey since)

## How it is checked

The checks of steps 1 of `tests/sessions/journey_opening.txt`, which runs on every development build.

- step 1 of the opening journey: the walk up the pier past the dock guard reaches the census office and the papers are taken (and, once the opening worker's check is in, the guard's box never overlaps a solid on his walk)

Status: checked on every development build.

## The code it lives in

- `engine/aga/src/aw_intro.c` (the opening's actors and the dock guard's walk)
- `engine/aga/src/aw_nav.c` (a scripted walk round an obstacle on its last leg)

## The code it guards

No code is marked yet: the marker goes on the code once the page passes.

## Feature pages

- [GAME_RECORDER.md](../GAME_RECORDER.md)

## Register entries

<!-- the register history below is rendered from docs/bugs/bugs.json when the page is rendered -->

### [PIER-GUARD-WALKS-INTO-DOOR-65](../bugs/PIER-GUARD-WALKS-INTO-DOOR-65.md)

After the race choice the dock guard walks against the office door for about half a minute before stepping aside. State: open; found in v0.0.65-rc2.

- 2026-11-13 Before the regression: fixed in source, v0.0.66-dev2 (0e39169a) (a gated commit; gate 10540 passed on e48fbb60, the pier guard line that holds it: every scripted walk goes round an obstacle on its last leg)
- 2026-11-13 regressed on v0.0.66-dev1 (was fixed in v0.0.65): Seen again on v0.0.66-dev1 in play: in the opening the dock guard is stuck between the pier posts and the wall on his way to the office door (Seyda Neen, local 374 -205, the guard placed from the original reference 172852). The opening walk of the dev1 image passed but took no picture of the guard on that stretch.
- 2026-11-14 Before the regression: shipped, v0.0.66-dev2 build 2026_11_14_v0.0.66-dev2_full-v0.0.66-dev2_3988c6e (a numbered build; the delivered build: the build holds 0e39169a)
- 2026-11-15 Before the regression: confirmed in play, v0.0.66-dev5 build 2026_11_15_v0.0.66-dev5_full-v0.0.66-dev5_18eb63f (the opening journey; the opening journey's step 1 (tests/sessions/journey_opening.txt): the walk up the pier past the dock guard reached the census office and the papers were taken: all six checks passed, as on every journey since)
- 2026-11-18 Guarded by the look book page DOCK-GUARD-POST (docs/lookbook/DOCK-GUARD-POST.md): In the opening the dock guard walks to his post by the census office door and is not caught in a pier post; a change to the code it lives in must pass that page before it is merged (docs/LOOKBOOK.md).
- 2026-11-18 Measured on the built images (SHA-256): no commit between v0.0.66 and v0.0.67-dev2 changed the dock guard's walk or the pier. The dock map, its door table, the path grid and every model record of the pier (the dock pieces, the four pilings, the railings, the door and its frame, the walls) are byte-identical in v0.0.66, v0.0.67-dev1 and v0.0.67-dev2; the walking code is unchanged since v0.0.66-dev2 (e48fbb60); the suspected change of where a walk starts after a load (2d772eb7) is not in the dev2 build. In both of the pictures the guard is still in his walk (a walk frame): the fault is latent si
- 2026-11-18 fixed in source: a gated commit, v0.0.67-dev2 (916b21de, with 4386e297; gate 11561 passed on 1b67c7aa) (tests/aga_nav_test.c, tests/aga_opening_test.c, tests/test_pier_guard_route.py, tests/test_journey_smoke.py; gate 11561)
- 2026-11-18 regressed on v0.0.67-dev2 (was fixed in v0.0.66-dev2): Came back on the v0.0.67-dev2 image (the maintainer's pictures, 2026-11-18): in the opening the dock guard stands inside a pier post on the Seyda Neen dock and stays there (cell -2,-9, local 445 -267 and 346 -187 at two moments of one session). It had worked in the builds since v0.0.66-dev2. Not measured yet; the first suspect is the change of where a walk starts after a load (WANDER-DOOR-AFTER-LOAD-67) in the same walking code.
- 2026-11-18 seen again on v0.0.67-dev2: Seen on 2026-11-18 at 32 MB Fast in the opening journey on the v0.0.67-dev2 image with the engine of gate 11562 (the fixed route along the pier's centre line): he reached his post (1 unit from it, at 286 -213 31) and steps 2 to 9 passed, but the walk's body check read 1: one tick with his box inside a solid, the walk's first tick (point 0) at his placement 366 -210 17, where his placement, which fits his feet to the deck, leaves his body box 5.75 units under the pier deck (top 22.75). The first step's stuck search lifted him; no tick of the route itself touched a so
