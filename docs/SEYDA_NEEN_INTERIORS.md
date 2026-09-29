# Seyda Neen interiors — v0.0.23-dev2

29 September 2026. All thirteen town interiors are converted, plus the separate
prison ship and Addamasartus. The expanded exterior retains the port approach and
scenery whose full bounds intersect the selected area, including the previously
omitted rock mound beside the port.

| Debug map | Original cell | Coverage |
| --- | --- | --- |
| `prison` | Imperial Prison Ship | Interior |
| `seyda` | Seyda Neen | Expanded exterior |
| `census` | Seyda Neen, Census and Excise Office | Interior |
| `tradehouse` | Seyda Neen, Arrille's Tradehouse | Interior |
| `warehouse` | Seyda Neen, Census and Excise Warehouse | Interior |
| `draren` | Seyda Neen, Draren Thiralas' House | Interior |
| `eldafire` | Seyda Neen, Eldafire's House | Interior |
| `erene` | Seyda Neen, Erene Llenim's Shack | Interior |
| `fargoth` | Seyda Neen, Fargoth's House | Interior |
| `finemouth` | Seyda Neen, Fine-Mouth's Shack | Interior |
| `foryn` | Seyda Neen, Foryn Gilnith's Shack | Interior |
| `indrele` | Seyda Neen, Indrele Rathryon's Shack | Interior |
| `lighthouse` | Seyda Neen, Lighthouse | Interior |
| `terurise` | Seyda Neen, Terurise Girvayne's House | Interior |
| `vodunius` | Seyda Neen, Vodunius Nuccius' House | Interior |
| `addamasartus` | Addamasartus | Interior |

Use the scrolling debug scene picker or `aw_scene <map>` to inspect a room.
Stable existing scene IDs are retained for saves; the content fingerprint now
covers every map. Older saves from different converted content are rejected.

Rooms use original placed architecture, furniture, lights and doors. The Census
architectural activator fix is retained. Assets lacking a separate collision node
use their visual mesh to build collision; conversion audits list exclusions and
errors. Addamasartus has its original water height, but uses shared ambient
lighting to keep repeated cave geometry within the target's memory budget.

The cast includes 30 ordinary placed NPC references / 27 appearances, alongside
the existing eight scripted introduction roles. Beast residents use the beast
skeleton. Everyone uses the same solid-body spawn path. Clothing and a bounded
generic greeting are included; full voice conditions, cycles, services and quest
behaviour are not yet implemented. Darvame is at her original placement; the
Strider is a static bind-pose model, without travel or idle animation yet.

All sixteen scenes loaded in a native emulator pass. Actual Tradehouse front-door
entry and exit passed. The raw source-door audit has 43 links; it is not a claim
that all 43 arrivals, staircases and floors are completely tested. The runtime
uses a floor/clearance search on arrival. Inspect difficult edges and report the
map, `dbg position` coordinates and facing. The previously repaired Census room/floor is retained; its separate captain-wing
out-of-bounds report remains open. Successful loading is not a whole-floor test.

The dated [work plan](PLAN-2026-09-29.md) prioritizes complete local voice behaviour
next, followed by Strider travel and the clock/sky/weather work.
