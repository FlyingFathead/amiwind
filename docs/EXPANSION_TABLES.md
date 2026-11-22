# The expansions in every table

_Last updated with AmiWind v0.0.68-dev5 (21 November 2026)._

With Tribunal and/or Bloodmoon selected (both by default: `--dlc both`; `--no-dlc` builds the base game alone), every
table the builder makes from the game data reads the selected masters in load order. The one way to read them is the
merging reader, `src/mwad/masters.py`: `master_path` / `master_bytes` give the merged master of the selection (with the
base game alone, the base file itself, byte for byte), and `selected_masters` gives the list of selected masters for a
reader that walks them one by one. A stage whose code reaches that reader is keyed by the selection
(`tools/build_cache.py` `stage_reads_layers`); every other stage keeps its base key. With the base game alone every
table stays byte-identical to the base-only build.

The check is `tests/test_expansion_tables.py`: a scan of `tools/` and `src/` refuses any direct read of the base file
alone outside a short allow list with reasons (below), and synthetic-layer tests prove the tables fixed in round 2 read
the selection, and only the base file when the base game alone is selected, even when the expansion files are present.

## The tables

Source: **layers** = the selected masters through the merging reader (keyed by the selection); **base** = the base
game file alone, by design (reason given). Round: when the table was moved onto the selection (EXPANSION-DATA-ALL-TABLES-66).

| Table | Made by | Source | Round |
| --- | --- | --- | --- |
| Focus boxes and rooms (`focus.awf`), signposts, doors' names | `tools/prepare_focus.py` | layers | 1 |
| Focus reference identity list (the `AWI1` file list of the world change list) | `tools/prepare_focus.py` `reference_table` | layers: one entry per content file whose references the table holds | 2 |
| Placed item list | `tools/prepare_item_models.py` | layers | 1 |
| Area ambient and recipe tables, the actors' levelled lists per area | `tools/prepare_area_tables.py`, `tools/prepare_area.py` | layers | 1 |
| Room numbers | `tools/cell_numbers.py` `room_numbers` | layers (every selected master's rooms) | 1 |
| Container census | `tools/container_census.py` | layers (now with every selected master's room numbers) | 2 |
| Travel services (`travel.txt`) | `tools/prepare_travel.py` | layers: the selected masters' providers and settings, the merged master's cells | 2 |
| Magic effects, their models and sounds | `tools/prepare_magic.py` | layers: the selected masters, never which files are present | 2 |
| Dialogue lookup (`dialogue.lut`) | `tools/dialogue_lut.py` | layers | before |
| Dialogue choices measure (`docs/dialogue-choices.json`) | `tools/dialogue_choices.py` | layers: every master is in the table under the default selection | 2 |
| Greetings and voice lines | `tools/greeting_lut.py` | layers | before |
| Books, items index, character generation | `tools/prepare_books.py`, items index stage, `tools/prepare_character.py` | layers | before |
| NPC library, actor library | `tools/npc_library.py`, `tools/actor_library.py` | layers | checked 2 |
| Creature census and creature tables | `tools/creature_census.py`, `tools/creature_tables.py` | layers | checked 2 |
| Actor spec check (the original's counts) | `tools/actor_spec_check.py` | layers | checked 2 |
| Combat sheets | `tools/prepare_combat.py` | layers (the expansions' own settings by `ADDON_SETTINGS`) | checked 2 |
| MWScript tables and the MWScript tracker | `tools/mwscript/gamedata.py`, `tools/mwscript_features.py` | layers (every master, OpenMW's load order) | checked 2 |
| Map regions, places and lava outlines | `tools/prepare_world_ui.py` | layers | checked 2 |
| World doors | `tools/world_doors.py` | layers | checked 2 |
| Start-disabled references | `tools/start_disabled.py` | layers (reads the merged master) | checked 2 |
| Terrain survey, hull surface survey | `tools/survey_vvardenfell.py`, `tools/hull_surface_survey.py` | layers (read the merged master) | checked 2 |
| Harvest source and catalogues | `tools/harvest_build.py`, `tools/prepare_harvest.py` | layers for the placements; the harvest kinds are the Bitter Coast mushrooms and tree fungi by model name, so no Bloodmoon plant is a harvest kind yet | open |
| Teleport places (`dbg tp`) | `tools/tp_places_lut.py` | layers: the selected masters through the merging reader; an outdoor place or being that only an expansion adds is listed when the image holds a frame of one of its cells, in the base world or in the expansion's own store (TP-LIST-EXPANSIONS-66, TP-LIST-MODULE-STORE-PLACES-68) | v0.0.68 |

## Base-only by design

| File | Why it reads the base game file alone |
| --- | --- |
| `tools/chim_build.py` | the CHIM base world (Vvardenfell); the layers are built by `tools/chim_layer_data.py` |
| `tools/chim_layer_data.py` | the layer step reads the base file to tell the layer's own records from it |
| `tools/chim/sol_test.py` | a test fixture of the Solstheim layer |
| `tools/chim/flames.py` | a presence check only; the light records are read through `master_path` |
| `src/mwad/paths.py` | the game input check: the base file must be in the data folder |
| `src/mwad/doctor.py` | the input inventory (file sizes), no table |
| `src/mwad/audit.py` | the base terrain audit of a square around a centre cell (a debugging survey, no shipped table) |

## Still open

- Harvest: the harvest kinds are chosen by model name (`tools/world_flora.py`: `flora_bc_mushroom_NN`,
  `flora_bc_shelffungus_NN`), so the expansions' plants are not harvestable (the base game's other plants are not
  either). A new kind is a new generation of the placement index (`tools/prepare_harvest.py` `INDEX_GENERATIONS`).
  The placements' identity keys carry the SHA-256 of the master the source reads, which is the merged master when the
  layers are selected; saves made with the base game alone do not carry their pick facts over to a build with the
  layers.
