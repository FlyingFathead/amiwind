# Scripted actors: Dagoth Ur, the Heart of Lorkhan and Vivec

_Last updated with AmiWind v0.0.52-dev (26 October 2026)._

A handful of the base game's actors are not ordinary residents: they are creature records with their own scripts,
and the end of the main quest depends on what those scripts do. This page says, in our own words, what the original
data asks of each of them and how much of it AmiWind does today. The facts come from the creature records and the
scripts attached to them in the player's own `Morrowind.esm` (read by the builder, never shipped); the game's
dialogue and voice lines are not repeated here. Placement in general: [actor placement](ACTOR_PLACEMENT.md).

## Who they are

| Actor | Record | Model | Script | Where |
| --- | --- | --- | --- | --- |
| Dagoth Ur (first meeting) | `dagoth_ur_1`, creature | `r\Dagothr.NIF` | `DagothUrCreature1` | Dagoth Ur, Facility Cavern |
| Dagoth Ur (the chamber) | `dagoth_ur_2`, creature | `r\Dagothr.NIF` | `DagothUrCreature2` | Akulakhan's Chamber |
| The Heart of Lorkhan | `heart_akulakhan`, creature | `r\heart_Akulakhan.NIF` | `LorkhanHeart` | Akulakhan's Chamber |
| Vivec | `vivec_god`, creature | `r\LordVivec.NIF` | none | Vivec, Palace of Vivec |

Three more scripts name them: each ash vampire's script, the dreamer workers' script in the chamber, and the global
`EndGame` script that ends the quest.

## Dagoth Ur, the first meeting

The first Dagoth Ur speaks once when the player comes within 800 units: one greeting if the player carries all
three of Kagrenac's tools (Keening, Sunder, Wraithguard), another if not. He is a fighting creature; when he dies,
a sparkle effect plays where he stood, the two Akulakhan doors grind open (each turns about 45 degrees with a stone
door sound) and his body is removed.

## Dagoth Ur in the chamber

He is the one the player fights. His script stops Recall and Intervention for as long as he exists, speaks his
welcome once, a second after the player arrives, and keeps him alive: whenever his health drops under 1,000 it is
set back, and his magicka is refilled, so he cannot be killed while the Heart lives. His protective shield spells
follow the Heart: a different shield for each Keening strike the Heart has taken, none after the fourth. Once the
Heart is destroyed his health is capped low and his magicka emptied, and he can die.

His "aggro from the start" is the Heart's script, not his: when the player first comes within 500 units of the
Heart, the Heart moves him to a fixed spot of the chamber, facing the player, and starts his combat with the player.
Every ash vampire killed earlier makes him weaker (a little strength, willpower and speed, some health, fatigue
and magicka each); when the quest's last stage is reached, any ash vampire still alive dies with him.

## The Heart of Lorkhan

The Heart cannot be killed by damage: its script sets its health high every frame. It beats (a looping sound),
and only after it has been struck with Sunder does it change its sound and start counting strikes with Keening.
Each of the first four Keening strikes plays one of the Heart's own animation groups (Idle2 to Idle5) and a line
from Dagoth Ur; the first one also turns him hostile. The fifth plays its death group (Death1), stops its sounds and
sets the global HeartDestroyed. After that a rumble plays until the player leaves, and the Heart is gone when the
cell changes.

## The end of the quest

When the Heart is destroyed, the global `EndGame` script advances the main quest's journal, plays the collapse of
Akulakhan and the bridge (their Death1 groups), removes the blight cloud over Red Mountain and clears its weather,
kills Dagoth Ur and his remaining Ash Vampires, allows teleporting again and rewards the player's reputation. The
dreamer workers in the chamber die too.

## Vivec

Vivec has no script of his own: he floats above the floor of his palace in his crossed-leg idle (the `idle2`
group), which the builder keeps as his initial state (levitating, no floor snap).

## What AmiWind does today

- **Placed** (v0.0.52-dev2): both Dagoth Urs, the Heart and Vivec stand where the game data puts them. Dagoth Ur is
  his whole original model (every one of his 2,254 triangles); the Heart is kept at its authored height. Before
  v0.0.52-dev2 neither Dagoth Ur nor the Heart was placed ([CREATURE-DAGOTH-UR-ABSENT-52](BUGS.md)).
- **Not yet**: their scripts. Today they play their idle loop only: no greeting, no combat, no strike counting. The
  Heart needs its Idle2 to Idle5 and Death1 groups, Dagoth Ur his combat groups; both come with his own skeleton
  table and the MWScript work of v0.0.53, as do the voice lines, the doors, the collapse and the weather.
- **Vivec** keeps a reduced model for now; his whole model is to be checked against the 1,999-vertex limit.
