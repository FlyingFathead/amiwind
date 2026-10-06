# HARVEST-BITTERCOAST-29: one of three nearby mushrooms usable

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
