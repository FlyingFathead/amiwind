# The confirmed look book

_Generated from tests/lookbook/pages.json with AmiWind v0.0.67-dev2._

Every look and behaviour the maintainer has confirmed in play, checked on every development build before it is delivered ([LOOKBOOK.md](../LOOKBOOK.md)). One reference page per page below.

| Page | Kind | Status | Register | Modules | Marked blocks | Last recorded pass |
|---|---|---|---|---|---|---|
| [HELD-LIGHT-IN-HAND](HELD-LIGHT-IN-HAND.md) | session | active (known gap) | [FP-TORCH-OUT-OF-HAND-67](../bugs/FP-TORCH-OUT-OF-HAND-67.md), [HELD-LIGHT-ALWAYS-TORCH-61](../bugs/HELD-LIGHT-ALWAYS-TORCH-61.md), [HELD-LIGHT-NOT-IN-HAND-65](../bugs/HELD-LIGHT-NOT-IN-HAND-65.md) | `aw_hand_models.c`, `aw_view.c`, `aw_torch.c`, `prepare_player_fp_parts.py`, `held_lights.py` | 0 | - |
| [ROBE-WORN](ROBE-WORN.md) | session | active | [ROBE-PART-NOT-BAKED-62](../bugs/ROBE-PART-NOT-BAKED-62.md) | `aw_view.c`, `prepare_player_parts.py`, `prepare_player_fp_parts.py` | 0 | - |
| [TELEPORT-ARRIVALS](TELEPORT-ARRIVALS.md) | session | active | [DBG-TP-NO-FLOOR-FALLBACK-63](../bugs/DBG-TP-NO-FLOOR-FALLBACK-63.md), [TP-BEING-TRIBUNAL-FALLS-THROUGH-67](../bugs/TP-BEING-TRIBUNAL-FALLS-THROUGH-67.md) | `aw_scene.c`, `tp_places_lut.py` | 0 | - |
| [DOCK-GUARD-POST](DOCK-GUARD-POST.md) | journey | active | [PIER-GUARD-WALKS-INTO-DOOR-65](../bugs/PIER-GUARD-WALKS-INTO-DOOR-65.md) | `aw_intro.c`, `aw_nav.c` | 0 | - |
| [INVENTORY-HINT-PER-KIND](INVENTORY-HINT-PER-KIND.md) | session | draft | [EQUIP-ACTION-REGRESSION-62](../bugs/EQUIP-ACTION-REGRESSION-62.md), [INVENTORY-EQUIPPED-LABEL-67](../bugs/INVENTORY-EQUIPPED-LABEL-67.md) | `aw_worldui.c`, `aw_inventory.c` | 0 | - |
| [CLIFF-RACER-WHOLE](CLIFF-RACER-WHOLE.md) | image | draft | [CREATURE-RACER-MESH-SPIKE-58](../bugs/CREATURE-RACER-MESH-SPIKE-58.md) | `creature_library.py`, `creature_tables.py` | 0 | - |

## Pages to write

From the register's confirmations, the maintainer's confirmations and the regressions reported again:

- First-person clothing drawn on the arms: robes, long sleeves and gloves (page FP-CLOTHING-VISIBLE) ([ROBE-PART-NOT-BAKED-62](../bugs/ROBE-PART-NOT-BAKED-62.md))
- A held weapon or item sits in the hand in first and third person (page HELD-ITEM-IN-HAND) ([FP-TORCH-OUT-OF-HAND-67](../bugs/FP-TORCH-OUT-OF-HAND-67.md))
- The OK box of the character windows highlighted when the keys reach it ([RACE-MENU-OK-HIGHLIGHT-65](../bugs/RACE-MENU-OK-HIGHLIGHT-65.md))
- Suran's dancers have their hair at the back of the head ([NPC-HAIR-BACK-MISSING-53](../bugs/NPC-HAIR-BACK-MISSING-53.md))
- The rock by the Seyda Neen port stands at its original rotation ([PORT-ROCK-ROTATION-23](../bugs/PORT-ROCK-ROTATION-23.md))
- Shargam gro-Shagdub answers about Ralen Hlaalo after naming him (the answer choice by the original's rules) ([DIALOGUE-TOPIC-WHO-60](../bugs/DIALOGUE-TOPIC-WHO-60.md))
- Sellus Gravius gives his dialogue, not only his greeting ([SELLUS-GRAVIUS-GREETING-ONLY-64](../bugs/SELLUS-GRAVIUS-GREETING-ONLY-64.md))
- After the papers the tutorial box is shown once ([TUTORIAL-BOX-SHOWN-TWICE-65](../bugs/TUTORIAL-BOX-SHOWN-TWICE-65.md))
- A wandering resident does not stop and stand right by a door ([WANDER-DOOR-RULE-66](../bugs/WANDER-DOOR-RULE-66.md))
- The dialogue's answer choices against the original's filter rules for every NPC (a gate page) ([DIALOGUE-TOPIC-WHO-60](../bugs/DIALOGUE-TOPIC-WHO-60.md))
- The opening: Jiub, the guard's walk, the census office (the regression tour) ([PIER-GUARD-WALKS-INTO-DOOR-65](../bugs/PIER-GUARD-WALKS-INTO-DOOR-65.md))
- The menus by the arrow keys: class and birthsign lists, their explanations ([RACE-MENU-OK-HIGHLIGHT-65](../bugs/RACE-MENU-OK-HIGHLIGHT-65.md))
- New Game after play leaves no state of the game before
- Close-ups of NPCs and creatures with their open-edge counts
- The shell of the egg-shaped magic effect drawn in the original's style
- The creatures' attack table: each creature attacks with its own moves
