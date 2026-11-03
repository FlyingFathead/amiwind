# Census Office silver plate: a game-script smoke test

_Last updated with AmiWind v0.0.59-dev5 (2 November 2026)._

A repeatable check of the game's own rules on a classic first theft: in the Census and Excise Office the player
takes the silver plate from the dining table, drops it on the floor and saves. The session script is
`tests/sessions/census_tray.txt` in the development tree (session scripts are not part of the release).

## What the original data says

- The item is `misc_imp_silverware_plate_01` ("Silverware Plate", weight 3, value 17), reference 119580 on the
  dining table of the back room, with crab meat on it. Like every item in the office, it belongs to the NPC record
  `a shady smuggler`, who does not stand in the office.
- No script names the plate or any other silverware. The Census Office scripts that react to the player's items
  are `CharGenStuffRoom` (a tutorial message for the bread, the crab meat, the candle, the lockpick, the whiskey
  and the note, only while character creation runs), `CharGenDagger` (the dagger), `CharGenStatsSheet` (the
  papers), `CharGenDoorGuardTalker` (the papers open the hall door), `CharGenDoorEnterCaptain` (Keley's ring) and
  `CharGenDoorExitCaptain` (Caius's package).
- So the reaction to taking the plate is the engine's crime rule, not a script. As OpenMW 0.51 applies it
  (mwmechanics/mechanicsmanagerimp.cpp): the taken item is marked stolen from its owner; if an NPC within
  `fAlarmRadius` (2000) sees it and that NPC's alarm is at least `iAlarmStealing` (1), the crime is reported
  ("Your crime has been reported!") with a bounty of value times `fCrimeStealing` (17 gold) and guards respond.
  Socucius Ergalla has alarm 0 and does not report; the two guards in the building (Ganciele Douar and Sellus
  Gravius) have alarm 100 and report it when they see it. The line `sCaughtStealingMessage` is spoken by the NPC
  the plate belongs to, who would have to be present, and he is not.
- Dropped, the plate stays stolen (the mark goes only when the item is given back to its owner).

This expected result is read from the data and the OpenMW 0.51 rules above; the steps were not run in OpenMW.

## Expected and seen (v0.0.59-dev5, FS-UAE at 32 MB Fast)

| Step | Expected | Seen |
| --- | --- | --- |
| Aim at the crab meat | Item box, "E: Take" | Item box, "E: Take" |
| Aim at the plate | Item box, "E: Steal" in red | Item box, "E: Steal" in red |
| Take it | Plate in the inventory, stolen from `a shady smuggler` | Plate in the inventory; the world change list holds the stolen pair |
| Scripts | No script reacts to the plate | None reacts |
| Crime | Reported if a guard sees it (bounty 17) | No crime rule yet (CRIME-59); crime level stays 0 |
| Drop from the inventory | Lands on the floor in front of the player | Refused before the fix (DROP-ROOM-BRUSH-ENTITY-59); lies in front of the player after it |
| Quicksave and quickload | Plate on the floor, still stolen | Plate on the floor, stolen pair kept |
| Tutorial messages for the other items | Shown during character creation | Not shown (CHARGEN-TUTORIAL-ITEM-MESSAGES-59) |

## Running it

On a full image, with FS-UAE at 32 MB Fast, started with the map `seyda`. The session makes a character after the
census (`dbg aw hors`), loads the office (`dbg scene census`) and stands beside the table with `aw_view` (room
coordinates are the original's divided by four). The console lines to check after the take, the drop and the
load are `stolen misc_imp_silverware_plate_01 from a shady smuggler: 1` and `drops 1`; the shots t3 and t4 show the
plate on the floor. A refused drop prints its reason and what was in the way.
