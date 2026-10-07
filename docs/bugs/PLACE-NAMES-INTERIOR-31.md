# PLACE-NAMES-INTERIOR-31: location label has no place name inside interiors

## Status: 7 October 2026

Open. Owner report from the v0.0.31-dev3 playtest; cause read in source.

## Symptom

Outdoors the debug title names the town ("Vvardenfell / Bitter Coast Region /
Seyda Neen"), but inside the prison ship, the Census and Excise Office and its
courtyard it does not say Seyda Neen or the building.

## Where

`engine/aga/src/aw_hud.c` (`Sbar_Draw`): interiors have no exterior cell, so
the title falls back to the map's own message (for example "AmiWind / Prison
Ship"); the place-name table (`world/region-names.awn`) covers exterior cells
only.

## How it happened

The place names were added for exterior cells (ARN2); interiors were not part
of that change.

## Why it was not caught

The change was checked outdoors only.

## Reproduction

v0.0.31-dev3: the prison ship, the Census and Excise Office, its courtyard.

## Repair

Not done: give each interior map its original cell name (for example "Seyda
Neen, Census and Excise Office") and show it as "Vvardenfell / Bitter Coast
Region / Seyda Neen / Census and Excise Office"; the prison ship as the Imperial
Prison Ship off Seyda Neen.

## Verification

Pending.

## Prevention

Interior views in the place-name checks.
