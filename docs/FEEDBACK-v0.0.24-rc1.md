# RC1 owner feedback, 30 September 2026

Development starts from the owner's source snapshot `amiwind-2026-09-30_231610.zip`,
version 0.0.24-rc1, published commit `04c1ecc`. Keep the published RC1 immutable.
Fix the reported UI, targeting and NPC placement issues before the character gallery.

## Current reports

Coordinates below are the player's diagnostic viewpoint, not the NPC's source
placement. Match the original reference before changing an actor's transform.

| Report | View XYZ | Yaw / pitch | State |
| --- | --- | --- | --- |
| Class confirmation shows The Tower before birthsign selection | Character creation | N/A | Cause found: class confirmation prints the default birth table entry. Hide it until birthsign selection/review; verification pending. |
| Clagius Clanler loses name/Talk prompt at close range | Balmora, Clagius' shop | Not supplied | Investigate physical hull versus visible model targeting and voice cooldown. |
| Floating Hlaalu Guard | -495, -501, 142 | 89 / -4 | Screenshot received; floor placement and reload behavior under investigation. |
| Floating Heddvild | -715, -818, 142 | 115 / 2 | Screenshot received; same placement audit. |
| Floating Stargel | -1128, -75, 256 | 94 / 0 | Screenshot received; same placement audit. |
| Llandras Belaal: tall or floating? | 232, 282, 58 | 223 / 4 | Measure foot contact separately from authored race proportions. |
| Unnamed floating NPC | 815, 110, 57 | 316 / -3 | Identify by source reference; no name visible in screenshot. |
| Balyn Omavel, floating | 852, 4, 57 | 91 / -7 | Source reference 41609 at 852.88, 69.89; also aligns with the unnamed viewpoint above. Retain both. |
| Additional floating Hlaalu Guard | 860, -451, 58 | 270 / -2 | Screenshot received; same placement audit. |
| Hlaalu Guard; check duplicate | 889, -536, 58 | 192 / -5 | Both east-bank viewpoints aim toward source reference 428718 at 857.17, -543.33. Retain both reports. |
| Blank ground patch; use adjoining hill terrain | 1144, -426, 114 | 225 / 64 | Identify the exact surface and neighbouring hill material before repair. |
| Names missing when facing interior NPCs directly | Balmora interiors | Not supplied | Broader targeting regression report; audit alongside Clagius Clanler. |
| Sticky terrain outside town | 1970, -1612, 128 | 353 / 0 | Reproduce with ordinary walking and inspect collision. |
| Invisible forward obstruction, city centre | -63, -51, 86 | 188 / 0 | Investigate together with the nearby stair viewpoint below. |
| Suspected stair obstruction | -98, -73, 88 | 341 / 72 | Keep exact viewpoint; compare standing sweep with visible architecture. |
| Were there dancing women in Balmora's Cornerclub? | Cornerclub | N/A | Check original cell/NPC records before treating as missing content. |

Release preparation: capture additional native Balmora screenshots after fixes.
The owner subsequently approved final **v0.0.24, Welcome to Balmora**, after this
work is completed and verified. Prepare final source/private packages and more
native Balmora screenshots; the owner still handles GitHub publication.
On 1 October (Helsinki), the owner also authorized **v0.0.24-rc2** if the new
features need another test cycle. That is the selected next package; final
v0.0.24 remains the destination after candidate acceptance.

Additional investigations: audit ground contact universally across converted NPC
placements on initial load and restoration. Distinguish authored flying/falling
or scripted actors (for example Tarhiel) from ground residents; do not flatten
all actor types to terrain. Measure disk, BSP and asset-loading phases of sub-cell
transitions before choosing incremental loading or prefetch under the 11 MiB heap.

The shared floor routine currently lifts the actor 8 units, then restores the
authored position if the landing is over 8 units below it. This is an inspected
code path, not yet the confirmed cause of every report. Sub-cell state restoration
also needs checking: a saved airborne position must not overwrite a valid landing.

## Requested character model gallery

Commands: `dbg aw charplane`, `dbg modelgallery`, `dbg npcgallery`.
Browse base-game NPCs and creatures on a plain midday inspection floor, one
model at a time. Include humanoids, enemies and animals, source identity/name,
stable numeric lookup, actual footprint and dimensions, and a clothing/base-body
choice for humanoids. Preserve authored proportions; allow walking around models.
Use Shift+N / Shift+P for next/previous and Enter for case-insensitive name/ID
lookup. Keep brief instructions in the console font at the top of the viewport.

Catalogue metadata belongs on disk and must map back to original records.
Load only the selected model. A fog-covered bounded floor is sufficient; a truly
infinite BSP and simultaneous residency of the full cast are unnecessary.
Conversion failures must be reported per entry, never hidden by skipping actors.

## RC2 checkpoint status — 1 October 2026

The table above preserves the original reports and intake state. RC2 implements
the confirmation/targeting changes, the guarded eastern hill-material patch,
canonical owner-core grounding and the gallery. All reported floater references
pass the independent final-mesh contact check; the two east-guard views refer to
the same placed guard, and the unnamed lady report is a view of Balyn Omavel.
Those camera reports remain individually retained. The strict broader audit still
has 23 contact findings, and both the new city-centre and region walking stalls
remain reproducible. See the RC2 release notes for exact acceptance boundaries.
# RC2 owner follow-up — 1 October 2026, 02:30 Helsinki

During further Balmora roaming in RC2, the owner reported that the city looked
clean and no unintended floating residents had been found. This is positive
playtest evidence for the reported Balmora placements; it is not an exhaustive
inspection of every room or an override of the outstanding host contact audit.
