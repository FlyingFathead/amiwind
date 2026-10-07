# Points-of-interest checklist

`tools/poi_checklist.py` reads the user's own `Morrowind.esm` and lists every
named exterior place and every interior cell, grouped by region, as a
checklist for converting and inspecting the world place by place.

```sh
python tools/poi_checklist.py --esm "/path/to/Data Files/Morrowind.esm" \
    --markdown private/poi-checklist.md --json private/poi-checklist.json
```

- **Exterior places:** named exterior cells (towns, landmarks), grouped by
  name across their grid cells.
- **Interiors:** each interior cell with its doors from the exterior (grid and
  position). Interiors reached only through other interiors are attached to
  their nearest exterior-connected parent through the door graph.
- **Type:** a hint from the cell name (tomb, cave, mine, shrine, house...) or,
  when the name says nothing, from the most common static kit (Dwemer ruin,
  Daedric shrine, Velothi interior...). Not an authoritative classification.
- **Status:** "converted" is ticked when the cell is in
  `config/seyda_area.json` or `config/balmora_interiors.json`. "Auto-checked"
  and "inspected" are left for the person working through the list.

The output names the game's places and is generated from the user's own data,
so keep it private. The tool and its synthetic test
(`tests/test_poi_checklist.py`) contain no game data.

For a stock `Morrowind.esm` the tool currently reports 1,216 places, 58 of
them converted.
