# AmiWind console commands

Open the console with F10 or the backquote key and type
a command, for example `dbg headlamp on`. This page is generated from
`config/debug-commands.txt`, the catalogue the game itself reads, by
`tools/console_commands_doc.py`; do not edit it by hand.

## Audio

| Command | Also | Arguments and notes |
| --- | --- | --- |
| `dbg door sounds` | - | on/off (default on) |
| `dbg ost play` | - | 00..98 / original music filename stem (spaces as underscores) |

## Video

| Command | Also | Arguments and notes |
| --- | --- | --- |
| `dbg cull` | - | 0/1 or on/off (default 1) |
| `dbg draw distance` | `dbg drawdistance`, `dbg fog distance` | [100..1500 local units; default 540] |
| `dbg fog` | - | on/off or 1/0 (default on) |
| `dbg fog location` | `dbg foglocation` | 1/0 places in id1/world/fog-locations.txt set their own day/night fog distance (Balmora 300 day, 250 night; default 0 off) |
| `dbg playvid` | `dbg playvideo`, `dbg videoplay`, `dbg vidplay` | <1..17 / 01..17 / catalogue name> (drains queued game audio first) |
| `dbg render order` | - | 1 legacy / 2 mesh intersections (default) |

## Playtesting

| Command | Also | Arguments and notes |
| --- | --- | --- |
| `dbg aw charplane` | `dbg gallery`, `dbg modelgallery`, `dbg npcgallery` | [number/name/ID; next/previous/body/exit] |
| `dbg aw hors` | - | 0 (new Hors, Nord / Barbarian / Steed, after Census) |
| `dbg combattest` | - | [idle/draw/lower/punch/center/help/exit] empty floor, current hands |
| `dbg daycycle gallery` | - | [here/off] (eight-stage camera tour; here keeps this view; Esc returns) |
| `dbg lightgallery` | - | [off] lighting switches at this spot in a strip below the view: night mode, tint, lamps, glow, headlamp, horizon veil, time preview; arrows change, Esc done |
| `dbg nightgallery` | - | [here/off] (23:00 wide view, Masser, Secunda, stars; Esc returns) |
| `dbg shroompicker` | - | [1..10/list] (default 1; preserves inventory and picked state) |
| `dbg shroomtracker` | - | (picked mushrooms in this save; excludes empty plants) |
| `dbg torchgallery` | `dbg torchtest` | [npc ID/name] same as torchtest: one NPC in the dark room, V toggles your torch |
| `dbg tpscene` | - | [list/headselection] (fresh debug scene; resets unsaved progress) |

## World / Travel

| Command | Also | Arguments and notes |
| --- | --- | --- |
| `dbg map tp` | `dbg tp map` | select a destination on the world map (alias) |
| `dbg noclip` | - | - |
| `dbg recover` | - | - |
| `dbg reset location` | - | 0 |
| `dbg scene` | - | ship/town/balmora/<map name> |
| `dbg scene change` | `dbg tp menu` | (scene picker) |
| `dbg tp` | - | [X Y original Morrowind global XY / seydaneen / prisonship / balmora / vivec (Vivec Arena) / <map name>; no argument opens menu] |
| `dbg unstuck` | - | (nearest clear standing spot below or beside you; never into a wall or water; leaves noclip) |
| `dbg view` | - | x y z yaw pitch |

## Sky / Lighting

| Command | Also | Arguments and notes |
| --- | --- | --- |
| `dbg 24hrcycle` | `dbg daytimecycle` | [seconds per hour 0.25..60, default 1; off] steps through 24 game hours, showing each hour that long (default 24 s in all); Esc stops |
| `dbg cloudcontrol` | - | legacy/new or 1/2 (legacy also disables midnight clearing) |
| `dbg clouds` | - | on/off true/false 1/0 (default on, independent of sun) |
| `dbg cloudtype` | - | classic/veil or 1/2 (classic default) |
| `dbg dayclouds` | - | 0..100% in 10:00..14:00 core; 09:00..10:00/14:00..15:00 fade; dawn/sunset protected |
| `dbg daynight` | - | [on/off] off holds the clock at 12:00 midday (sky, light, lamps, windows; survives map changes, not saved); on resumes from the current time; no argument: state |
| `dbg daynightcycle` | - | on/off true/false 1/0 (automatic time; explicit set/wait still work) |
| `dbg emissive` | - | [0 or 1] glowing lanterns, flames, lava and mushrooms (default 1); no argument: query |
| `dbg exterior luma` | `dbg luma exterior`, `dbg luma outdoor` | [0..4] no argument: query |
| `dbg guardtorch` | - | [on/off/auto] (all guard torches; auto follows guards_torch_cycle) or light radius 0.1..2.0 of the player torch (default 0.5) |
| `dbg headlamp` | `dbg hlamp` | [on/off, true/false or 1/0] torch light without holding a torch (not saved) |
| `dbg horizon veil` | - | 0..15 (default 0 off) haze the lowest sky bands into the far fog colour so distant gaps read as haze |
| `dbg indoor luma` | `dbg interior luma`, `dbg interiorluma`, `dbg luma indoor`, `dbg luma interior` | [0..4] (brightness-enabled builds; static interior multiplier; default 1.2; no argument queries) |
| `dbg lamp lights` | - | [0..4] nearest exterior lamps, lanterns, torches and fires lit at night, each a torch's worth (default 2; 0 off) |
| `dbg lamps` | - | status of the night lamps here: map, night, cached and lit lamps, night windows |
| `dbg light hue` | - | [R G B 0..255] colour of torch, lamp and window light (default 255 210 140); no argument: current |
| `dbg luma` | - | no argument: current indoor and outdoor luma, then how to set them |
| `dbg night light` | - | 1 light-space night (default): lamps, glows and torches keep their light / 0 old whole-frame night remap |
| `dbg night tint` | - | 0..100 hue strength of the night tint with night light 1 (default 100) |
| `dbg night windows` | - | 1/0 window glass glows at night (default 1; an AmiWind addition, the original windows never glow) |
| `dbg nightclouds` | - | auto/clear/partial/overcast (night-only, stable game-day prototype) |
| `dbg nightsky` | - | on/off true/false 1/0 (night layer including moons; default on) |
| `dbg nightskymode` | - | legacy/clear or 0/1 (midnight clear default, return by 04:00) |
| `dbg outdoorlantern` | - | [0.25..3.0] light radius of exterior lamps and lanterns at night, relative to the torch (default 1.0) |
| `dbg set time` | `dbg settime`, `dbg time` | HHMM (0000..2359) or morning/night/midday/day/evening/sunset/sunrise/dusk/dawn |
| `dbg sky` | - | on/off true/false 1/0 (sky/fog presentation; time control is separate) |
| `dbg skyline fill` | `dbg skylinefill` | 1/0 object silhouetting horizon: sky below fogged far scenery takes the fog colour; experimental and buggy (sprites need their shapes from the alpha channel); tested but subpar results, kept for future improvement (default 0: land-outline horizon) |
| `dbg skyspeed` | - | [0..100] (cloud multiplier; default 0.00333333333 = 1/300 of old speed) |
| `dbg skytype` | - | 1/2/3 or V1/V2/V3 (V3 extra stronk default) |
| `dbg starsky` | - | on/off true/false 1/0 (stars and nebula; default on) |
| `dbg sun` | - | on/off true/false 1/0 (default on, clock still advances) |
| `dbg timeofday` | - | [0..23.999 or morning/night/midday/day/evening/sunset/sunrise/dusk/dawn] |
| `dbg torch flame` | - | [classic/brightbase/sparks or 1/2/3] no argument: current style |
| `dbg torch radius` | - | [32..288] (player + admitted guard lights; default 192, classic 144) |
| `dbg torch strength` | - | [0..1] (player + admitted guards; default 0.7; local light only) |
| `dbg warm light` | - | 1/0 torch, lamp and window light takes the light hue (default 1) |

## Ui / Console

| Command | Also | Arguments and notes |
| --- | --- | --- |
| `dbg console bg color` | - | black/blue/gray or R G B |
| `dbg console font` | - | small/normal |
| `dbg font` | - | readable/retro |
| `dbg ui dialogue` | - | 1/2/3/4 (default 3) |
| `dbg ui font` | - | 16/14/12/fallback |
| `dbg ui ink` | - | original/readable |
| `dbg ui labels` | - | below/topright/hudleft |
| `dbg ui layout` | - | 1 legacy / 2 full width / 3 padded content (default) |
| `dbg ui preview` | - | - |
| `dbg ui targetnames` | - | on/off (after creation) |
| `dbg ui targetplace` | - | below/topright/hudleft |

## Input

| Command | Also | Arguments and notes |
| --- | --- | --- |
| `dbg input trace` | `dbg inputtrace` | on/off true/false 1/0 (alias; default off) |

## Diagnostics

| Command | Also | Arguments and notes |
| --- | --- | --- |
| `dbg all` | `dbg hud`, `dbg overlay` | on/off |
| `dbg blockers` | - | - |
| `dbg compass` | - | on/off true/false 1/0 (default off) |
| `dbg coords` | - | on/off |
| `dbg dimensions` | - | - |
| `dbg eyeheight` | - | [offset above player origin] |
| `dbg fps` | - | on/off |
| `dbg fpu` | - | (CPU and FPU support library status: 68040.library/68060.library resident or none) |
| `dbg fpucount` | - | [0/1] once a second: per-frame counts of brush model rotations (and rebuilds), direction vectors, table sine/cosine lookups and NPC targeting (average/peak) |
| `dbg hands` | - | - |
| `dbg heap` | - | (current hunk clearance and load peak) |
| `dbg hud type` | - | 1 original / 2 compact (default) |
| `dbg npcfloors` | - | (read-only ground-contact report) |
| `dbg npcs` | - | - |
| `dbg pos` | - | - |
| `dbg probe` | - | (slow floor audit) |
| `dbg rcount` | - | [0/1/2] once a second: renderer counts per frame (brush models, faces, clip fragments, edges, spans, surface cache, alias models) and timing split; 2 = remote state file only |
| `dbg sealevel` | - | on/off |
| `dbg show fps` | - | [on/off] |
| `dbg showram` | - | on/off |
