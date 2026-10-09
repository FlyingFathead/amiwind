# HARVEST-BITTERCOAST-29: one of three nearby mushrooms usable

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 6 October 2026, in v0.0.29-rc2 |
| Where | Bitter Coast mushrooms near global -15287 -59485 735 |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.29-rc2 (last seen) |
| Severity | low: Only one of three nearby mushrooms reportedly usable; cause unknown. |
| Family | Harvestable plants (`harvest`) |

<!-- END GENERATED FACTS -->

Status: **open**, reported in v0.0.29-rc2 on 6 October 2026.
Fixed: **No**. First fixed version: none. Cause: unknown.

## Report and location

In Bitter Coast, the player reports that only one of three nearby mushrooms
can be eaten. They tentatively call them Luminous Russula and ask whether the
other two may be different types. The report does not establish their species,
whether they are harvestable, or whether the failed action is world pickup or
inventory consumption.

The original screenshot shows **AmiWind v0.0.29-rc2**, **Vvardenfell / Bitter
Coast Region**, global XYZ approximately **-15287 -59485 735**, game time
**02:39**. The small local overlay appears to read **-237 -28 -200**, **S190**,
**P39**; confirm those local values and the map before using them for reproduction.
The screenshot documents the scene, not a successful or failed input sequence.

## Next reproduction

1. Identify the map and original reference IDs for all three visible objects.
2. Check each source species/type and whether it has a harvest or use action.
3. Replay the world interaction from a normal reachable position; record the
   prompt, input, result, harvest state and inventory change for each object.
4. If pickup succeeds, test inventory consumption separately and record quantity,
   item identity, feedback and any action restrictions.
5. Recheck after save/reload and across overlapping map copies where applicable.

Do not infer a range, occlusion, species, placement or persistence defect from
this report alone. Broader mushroom coverage remains tracked separately under
HARVEST-WORLD-29. Preserve the known successful pickup/save behavior as a control.

[Bug register](../BUGS.md) | [Playtest ledger](../RC1_PLAYTEST_LEDGER.md)

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Harvestable plants (`harvest`). Harvest catalogues are built by the builder for the shipped maps and counted by the entity tracker. See [families](README.md#families).

- [CHIM-HARVEST-SPECIALS-33](CHIM-HARVEST-SPECIALS-33.md): The intro docks on CHIM have no harvestable plants: their catalogue is named after the legacy map, which a pure CHIM image leaves out
- [ENTITY-TRACKER-HARVEST-32](ENTITY-TRACKER-HARVEST-32.md): The entity tracker did not count plants placed by harvest catalogues
- [HARVEST-EXTRA-TOWNS-32](HARVEST-EXTRA-TOWNS-32.md): Opt-in towns get no harvestable mushrooms
- [HARVEST-GEOMETRY-GATE-32](HARVEST-GEOMETRY-GATE-32.md): The harvest geometry gate was never re-run on the shipped Seyda Neen maps
- [HARVEST-PILOT-SHIPPING-32](HARVEST-PILOT-SHIPPING-32.md): 24 Seyda Neen maps still ship the six-plant pilot harvest catalogue
- [HARVEST-SEYDA-STALE-32](HARVEST-SEYDA-STALE-32.md): v0.0.31 ships Seyda Neen harvest catalogues made for older map versions
- HARVEST-WORLD-29 (no report page): Original mushroom placement, picking and persistent state worldwide

<!-- END GENERATED CATEGORY -->
