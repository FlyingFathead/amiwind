# Look book page ROBE-WORN

_Generated from tests/lookbook/pages.json with AmiWind v0.0.67-dev2._

A worn robe is drawn on the body in first and in third person.

## What the maintainer confirmed

A common robe put on shows on the player's body in third person and on the arms in first person.

- 2026-11-18, on v0.0.67-dev2: the maintainer's play session on the v0.0.67-dev2 image, wearing a common robe: it shows in both views (ROBE-PART-NOT-BAKED-62)

## How it is checked

A scripted session step of the look book (`tests/lookbook/robe_worn.txt`), run with every other page in one emulator session on every development build before it is delivered. Its numbers are the check; its pictures are compared with their references where it has them.

- picture `robe-third`: the robe on the body in third person
- picture `robe-first-down`: the robe's sleeves in first person, looking down

- the robe is worn (aw_inventory worn) and the body is assembled from what is worn, with more slots than before it (aw_camera)
- the first-person arms are assembled from parts with the robe on (aw_camera)

Status: checked on every development build.

## The code it lives in

- `engine/aga/src/aw_view.c`: `parts_ready`, `hand_parts_ready` (the body and the arms assembled from what is worn)
- `tools/prepare_player_parts.py` (the third-person parts and their recipes)
- `tools/prepare_player_fp_parts.py` (the first-person parts (a robe's own sleeves))

## The code it guards

No code is marked yet: the marker goes on the code once the page passes.

## Feature pages

- [THIRD_PERSON.md](../THIRD_PERSON.md)

## Register entries

<!-- the register history below is rendered from docs/bugs/bugs.json when the page is rendered -->

### [ROBE-PART-NOT-BAKED-62](../bugs/ROBE-PART-NOT-BAKED-62.md)

An equipped robe taken from Tarhiel is drawn in first person but not on the third-person body or in the inventory picture. State: open; found in v0.0.62-dev1.

- 2026-11-18 Guarded by the look book page ROBE-WORN (docs/lookbook/ROBE-WORN.md): A worn robe is drawn on the body in first and in third person; a change to the code it lives in must pass that page before it is merged (docs/LOOKBOOK.md).
- 2026-11-18 confirmed by the maintainer: the maintainer, v0.0.67-dev2 (0d6f7ab7) (a play session on the v0.0.67-dev2 image, wearing a common robe)
