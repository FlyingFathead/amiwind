# Look book page HELD-LIGHT-IN-HAND

_Generated from tests/lookbook/pages.json with AmiWind v0.0.67._

A carried light (the debug torch, the glass lantern, a candle) is held in the left hand in first and in third person.

## What the maintainer confirmed

Every carried light sits in the left hand: the torch, the glass lantern, candles and candlesticks, drawn as themselves with their flames, in first person and in third person, with the hands raised.

- 2026-11-07, on v0.0.61: seen in game on the v0.0.61 release image: the candle, the pewter candlestick and the glass lantern drawn as themselves in the hand in first person (HELD-LIGHT-ALWAYS-TORCH-61)
- 2026-11-18, on v0.0.67-dev2: the maintainer's report of the regression: every carried light was held in the left hand in first person for many versions, and third person still holds it right

## How it is checked

A scripted session step of the look book (`tests/lookbook/held_light_in_hand.txt`), run with every other page in one emulator session on every development build before it is delivered. Its numbers are the check; its pictures are compared with their references where it has them.

- picture `torch-first-down`: the debug torch in first person, looking down at the hands
- picture `torch-first-steep`: the debug torch in first person, looking steeply down
- picture `torch-first-photo`: the debug torch in first person in photo mode with the hands (the full view)
- picture `torch-third`: the debug torch in third person
- picture `lantern-first-down`: the glass lantern in first person, looking down
- picture `lantern-first-steep`: the glass lantern in first person, looking steeply down
- picture `lantern-first-photo`: the glass lantern in first person in photo mode with the hands
- picture `lantern-third`: the glass lantern in third person
- picture `candle-first-down`: a candle in first person, looking down
- picture `candle-first-steep`: a candle in first person, looking steeply down
- picture `candle-first-photo`: a candle in first person in photo mode with the hands
- picture `candle-third`: a candle in third person

- the light is the one in the left hand (aw_inventory worn) and it is lit (aw_hands: torch 1)
- the view is first person, the light is in the left hand and lit, and the view looks down (at least 30 degrees) for every first-person still, each read back by number
- the light's nearest vertex from the left hand it is drawn in (dbg camera held): in third person within 2.5 units, in first person within 0.5 units of the same light's third-person value

Status: checked on every development build.

## The code it lives in

- `engine/aga/src/aw_hand_models.c`: `AW_HandModelsApply`, `AW_HandLightItemApply`, `AW_HandItemPlace`, `hand_item_on_bone` (the first-person light on the arms' shield bone, by the one held-item placement)
- `engine/aga/src/aw_view.c`: `hand_parts_bone_tag`, `hand_parts_apply`, `parts_draws`, `parts_light_layer` (the arms from parts in first person (the hand's bone), the body's held light in third person)
- `engine/aga/src/aw_torch.c`: `held_own`, `AW_HeldLight`, `light_lit` (which light is held and lit)
- `tools/prepare_player_fp_parts.py` (the first-person table and its light stance)
- `tools/held_lights.py`: `carried_place` (each light's carried place on the shield bone)

## The code it guards

No code is marked yet: the marker goes on the code once the page passes.

## Feature pages

- [THIRD_PERSON.md](../THIRD_PERSON.md)

## Register entries

<!-- the register history below is rendered from docs/bugs/bugs.json when the page is rendered -->

### [FP-TORCH-OUT-OF-HAND-67](../bugs/FP-TORCH-OUT-OF-HAND-67.md)

In first person a held torch floats away from the left hand: a regression, the torch was held in the hand before. State: fixed, fixed in v0.0.67-dev3; found in v0.0.67-dev2.

- 2026-11-18 Guarded by the look book page HELD-LIGHT-IN-HAND (docs/lookbook/HELD-LIGHT-IN-HAND.md): A carried light (the debug torch, the glass lantern, a candle) is held in the left hand in first and in third person; a change to the code it lives in must pass that page before it is merged (docs/LOOKBOOK.md).
- 2026-11-18 fixed in source: a gated commit, v0.0.67-dev2 (6e7111d3) (tests/test_fp_held_item.py and tests/aga_held_item_test.c, the grip numbers read from the v0.0.67-dev2 image)
- 2026-11-19 confirmed by the maintainer: the maintainer, v0.0.67-dev3 (a375b13f) (the look book stills of the held lights)
- 2026-11-19 confirmed in play: the look book, v0.0.67-dev3 (a375b13f) (page HELD-LIGHT-IN-HAND (tests/lookbook), the distance read by the debug camera)
- 2026-11-19 fixed in source: a gated commit, v0.0.67-dev3 (a375b13f) (gate 11450 of the planning item FP-TORCH-OUT-OF-HAND-67)
- 2026-11-19 shipped: a development build, v0.0.67-dev3 (a375b13f) (the build of a375b13f, gate 11450, delivered as v0.0.67-dev3)

### [HELD-LIGHT-ALWAYS-TORCH-61](../bugs/HELD-LIGHT-ALWAYS-TORCH-61.md)

Any carried light held in the hand is drawn and lit as a torch. State: fixed, fixed in v0.0.61; found in v0.0.61-dev2.

- 2026-11-06 HELD-LIGHT-ALWAYS-TORCH-61: every carried light is held as the torch: HELD-LIGHT-ALWAYS-TORCH-61: a candle, candlestick or lantern equipped from the inventory goes into the left hand as in the original, but the hand shows the torch model with the torch's flame and light radius, in both views. The records give each light its own radius (torch 256, the candle 128, the three-candle holders and the lanterns 256); the repair draws the held light's own model and flames and scales its light by its record against the torch's.
- 2026-11-18 Guarded by the look book page HELD-LIGHT-IN-HAND (docs/lookbook/HELD-LIGHT-IN-HAND.md): A carried light (the debug torch, the glass lantern, a candle) is held in the left hand in first and in third person; a change to the code it lives in must pass that page before it is merged (docs/LOOKBOOK.md).

### [HELD-LIGHT-NOT-IN-HAND-65](../bugs/HELD-LIGHT-NOT-IN-HAND-65.md)

An equipped candlestick is not held in the hand; readying shows only the fists. State: open; found in v0.0.65-rc3.

- 2026-11-18 Guarded by the look book page HELD-LIGHT-IN-HAND (docs/lookbook/HELD-LIGHT-IN-HAND.md): A carried light (the debug torch, the glass lantern, a candle) is held in the left hand in first and in third person; a change to the code it lives in must pass that page before it is merged (docs/LOOKBOOK.md).
