# AmiWind console commands

_Generated from `config/debug-commands.txt` with AmiWind v0.0.55._

Open the console with F10 or the backquote key and type
a command, for example `dbg headlamp on`. This page is generated from
`config/debug-commands.txt`, the catalogue the game itself reads, by
`tools/console_commands_doc.py`; do not edit it by hand.

At start-up, on every map load and with the `version` command the console shows the
game and CHIM versions, the AmiQuake version and where help is (on a map load the
AmiQuake line ends with `SERVER (<game code CRC>)`):

```text
AmiWind v<version> / CHIM v<CHIM version>
AmiQuake: VERSION 1.09
Type: "dbg help" for help.
```

## Audio

| Command | Also | Arguments and notes |
| --- | --- | --- |
| `dbg door sounds` | - | on/off (default on) |
| `dbg music` | - | [on/off, true/false or 1/0; no argument = status of the switch and the stream] background music (default on; not saved): off closes the stream at once and opens none until on again |
| `dbg music custom` | - | [play / stop; no argument: status] the custom OST player (an image built with --custom-ost FILE): play your own track alone, the playlist and its auto-advance waiting; stop gives the playlist back; without a custom track: silence, never the OST |
| `dbg mwscript` | - | on/off (EXPERIMENTAL, default off, saved) run the game's compiled scripts (docs/MWSCRIPT_BYTECODE.md): ambient and activator sounds, NPC lines, music cues, journal and globals; functions not carried out yet are logged once |
| `dbg mwscript status` | - | the compiled scripts: objects attached on this map, global scripts, sounds, runs, skipped runs, opcodes per frame |
| `dbg ost play` | - | 00..98 / original music filename stem (spaces as underscores) |

## Video

| Command | Also | Arguments and notes |
| --- | --- | --- |
| `dbg atmos` | - | 0..3 (saved, default 2): 1 rain, snow and storm ash outdoors (off until measured), 2 chimney, fire and steam smoke; 3 both |
| `dbg cam` | - | [mark NAME / recall NAME / list / orbit [photo] [speed DEG] [ref N / mark NAME] / orbit off] (docs/CAMERA_MARKS.md) mark saves place, view, time, headlamp, fog; recall: a public mark (bm1..bm5, sn1..sn5, vivec-palace) or yours, as dbg tp; orbit circles the crosshair target, player detached: +/- speed, 0 holds, wheel distance, right click or Esc ends |
| `dbg camera` | `dbg pov`, `dbg thirdperson` | [first / third / toggle / distance 7.5..200 / vanity on/off/now / death on/off / retry on/off / body on/off / die] player view: no argument = status; Tab first/third person (held: orbit), wheel zooms; vanity = idle orbit; death = death camera; retry = Retry fight; die = test death (docs/THIRD_PERSON.md) |
| `dbg campfires` | - | [on/off, true/false or 1/0] fires outdoors (default on; not saved): on = campfires, braziers, fire pits, torches and flame lamps burn and light the objects around them (and, at night, the ground near the nearest); off = no flame and no fire light outdoors, at once (interiors keep their fires) |
| `dbg crosshair` | `dbg crosshairs` | [on/off or 1/0; no argument toggles / colour NAME / shape NAME / style] show the crosshair (saved; default on; also Options > Prefs); colours Warm white (default), Yellow, Green, Blue; shapes Cross (default), Open cross, Small cross, Dot (saved); a number or a name's start is enough, no name lists them; style prints all three |
| `dbg cull` | - | far detail (saved; also Options > Video > Far detail): 1 Full (everything to the fog), 3 Light, 4 Strong (default; saves from before v0.0.42 keep Full), 6 Strong + small faces (distant models drop out sooner: faster); also 0 none, 2 fog-exact (same picture as 1), 5 small faces only, 7 debug view; on = 1, off = 0; +8 fog rule, +16 cut groups (see those) |
| `dbg cut groups` | - | [on/off, 1/0; no argument shows aw_cull] whole-structure cuts (saved as aw_cull + 16; default off until the in-game A/B): the pieces of one long structure (walkways, town walls, bridges, the Ghostfence, hillside rocks; the frame map's .cut file) are drawn, fogged and left out together, tested on the structure's box; 0 each piece on its own |
| `dbg draw distance` | `dbg drawdistance`, `dbg fog distance` | [100..4096 local units; default 540] |
| `dbg fog` | - | on/off or 1/0 (default on: exterior and interior fog; the console value 2 = exterior fog only, interiors without their cell fog as before) |
| `dbg fog location` | `dbg foglocation` | 1/0 places in id1/world/fog-locations.txt set their own day/night fog distance (Balmora 300 day, 250 night; default 0 off) |
| `dbg fog rule` | - | [on/off, 1/0; no argument shows aw_cull] no distance cut before the fog is opaque (saved as aw_cull + 8; default off until the in-game A/B): the Light/Strong far detail cut-offs and the small-faces step start at the fog distance, so nothing pops out of clear air; 0 the cut-offs as before (faster) |
| `dbg ghostfence` | - | [on/off, true/false or 1/0] animated scrolling textures (default on; not saved): on = the Ghostfence curtain, waterfalls and other turbulent textures ripple over time; off = drawn straight and still (unlit, as they are built; also stills water in interiors) |
| `dbg killhud` | `dbg photomode` | [on/off, true/false or 1/0; no argument toggles; hud: Ctrl+Alt+H] clean shots: hides bars, crosshair, hands, prompts, names, subtitles and overlays; full view; fog off and free camera (aw_photomode_nofog, aw_photomode_noclip, aw_photomode_hands); Ctrl+F fog, Ctrl+H dbg hud; off returns to the start point (not saved; Options > Video > Photo mode) |
| `dbg land fill` | `dbg landfill` | 1/0 (default 1): Land Fill Independence v1, enabled LAND passes with fog on or off; 0 disables for A/B |
| `dbg land method` | - | 1/0 legacy resident LAND rasterizer (default 0, experimental); separate from the CHIM far layer |
| `dbg magicfx` | - | [0 / 1 / 2; no argument shows the value] magic effects (docs/MAGIC_EFFECTS.md, experimental): 0 off (default, saved), 1 sprites and particles, 2 also their light |
| `dbg noclipbob` | `dbg noclipwobble` | same as noclipwobble |
| `dbg photomode ui` | - | [on/off or 1/0] photo mode's own notice box and hints (saved; default on; off hides them; the Halloween scene turns them off while it runs) |
| `dbg playvid` | `dbg playvideo`, `dbg videoplay`, `dbg vidplay` | <1..17 / 01..17 / catalogue name> (drains queued game audio first) |
| `dbg render order` | - | 1 legacy / 2 mesh intersections (default) |
| `dbg vanitycam` | `dbg vanitycamera` | same as vanitycamera |

## Playtesting

| Command | Also | Arguments and notes |
| --- | --- | --- |
| `dbg animkit` | - | [on/off / list / groups / play <group> / cycle [all] / stage [1..8] / stop / speed <0.1..4> / pick [on/off / cast / sneak / idle]] animation kit (docs/ANIMKIT.md): on/off gaits by speed; list/groups, play, cycle, stage: the target's groups; pick: every group by state |
| `dbg arena` | `dbg arenapit`, `dbg arenatest`, `dbg battlearena`, `dbg playground` | [opponent / list / next / prev / here/pit/floor / seed N / rematch / setup / exit] Vivec Arena combat minigame (also dbgmode arenapit, testarena): title, fight, result, then Enter rematch / S same seed / N, B next, previous / P pick / Esc leave; opponent = Arena fighter, gallery # or NPC record ID; Ctrl+X returns (not saved) |
| `dbg aw charplane` | `dbg gallery`, `dbg modelgallery`, `dbg npcgallery` | [number/name/ID; next/previous/body/exit] |
| `dbg aw hors` | - | 0 (new Hors, Nord / Barbarian / Steed, after Census) |
| `dbg bench` | `dbg halloweenbench` | [halloween [skeletons]] the standard benchmark (docs/REAL_HARDWARE.md; also aw halloweenbench, dbg halloween bench): 600 fixed frames of the Halloween scene, FPS small at the bottom left, then one result line on the console to copy |
| `dbg cast` | - | [NAME [target / touch / self / fail] [npc] [area FEET] [dur S] [shape egg/sphere] [repeat] / list / stop / orb 0-3 / shell egg/sphere; no argument: status and costs] a spell's look and sound (docs/MAGIC_EFFECTS.md; needs dbg magicfx 1/2): cast animation, orb, cast, bolt, hit, area; npc: the actor in front casts at you; no magicka |
| `dbg characterchange` | `dbg quickchar` | [race class birthsign review / all] reopen the pier race, gender, head and hair menu over the current scene; confirm to apply (after registration) |
| `dbg choosecompanion` | `dbg pickcompanion` | same as companion pick |
| `dbg combat` | - | [on/off / seed N / readout on/off / music on/off / dice on/off / style amiwind/original / block hold/auto / flee on/off / bestattack on/off / loadout NAME/off / calm] melee combat: no argument = status, costs; readout = a line per swing; seed 0 = new per fight; flee on = also by Flee rating (defaults on, readout on, music on, block hold, flee off) |
| `dbg combattest` | - | [opponent] same as arenapit; combattest gallery (or floor): the empty floor test, current hands, then idle/draw/lower/punch/center/help/exit |
| `dbg companion` | - | [pick/choose/test/off/distance N/mimic speed on/off] NPC follower test (not saved): no argument = status and counters; pick = attack the NPC under the red crosshair; test = spawn one beside you; off = it goes home / is removed; distance 48..512 (default 96); mimic speed (default on) |
| `dbg companiontest` | - | [on/off] same as companion test / companion off; no argument: status |
| `dbg creatures` | - | [on/off, true/false or 1/0; no argument: status] the outdoor creatures (default on; not saved): off removes the wild creatures alive (their state kept) and spawns none, to compare frame rate, memory and behaviour; on brings them back as their cells join again |
| `dbg daycycle gallery` | - | [here/off] (eight-stage camera tour; here keeps this view; Esc returns) |
| `dbg demowind` | - | [on / off / next / prev / effect 1-2 / dist 0-7 / status] DemoWind (docs/DEMOWIND.md): the effects test kit, fullscreen, no world; each effect with its ms a frame and bytes on screen; Left/Right effect, Up/Down distance to Red Mountain, Esc off |
| `dbg halloween` | - | [dagoth / skeletons / bench [skeletons] / fps on/off / camera wide/director / stop / status] Halloween scene (docs/HALLOWEEN.md, an image with the cast): skeletons, Desele's dancers, Dagoth Ur dance on the beat; dagoth (default) or skeletons alone; bench: the standard benchmark, one result line |
| `dbg halloweentest` | - | [same words as halloween] the Halloween scene with the FPS counter on (bottom left) |
| `dbg inventory grant` | - | <quoted source item ID> <1..999> explicit diagnostic grant of actual catalogue items (not saved defaults) |
| `dbg lightgallery` | - | [off] lighting switches at this spot in a strip below the view: night mode, tint, lamps, glow, headlamp, horizon veil, time preview; arrows change, Esc done |
| `dbg nightgallery` | - | [here/off] (23:00 wide view, Masser, Secunda, stars; Esc returns) |
| `dbg set playerrace` | `dbg set race` | [ID / NAME / list] zero-based race list; switch appearance in place; retain gender/class/name/equipment/level/stats; choose valid head and hair |
| `dbg shroompicker` | - | [1..10/list] (default 1; preserves inventory and picked state) |
| `dbg shroomtracker` | - | (picked mushrooms in this save; excludes empty plants) |
| `dbg torchgallery` | `dbg torchtest` | [npc ID/name] same as torchtest: one NPC in the dark room, V toggles your torch |
| `dbg tpscene` | - | [list/headselection] (fresh debug scene; resets unsaved progress) |

## World / Travel

| Command | Also | Arguments and notes |
| --- | --- | --- |
| `dbg door` | `dbg doorlocks` | [status / list; no argument: open or close the hinged door under the crosshair, locks ignored] ordinary hinged doors (docs/DOOR_MAPPING.md): status counts the table and this map's doors, list prints each (reference, edict or CHIM, how far open, lock) |
| `dbg door roulette` | - | [SEED] one random interior: loads you straight into a room of this disk at the room's own start and prints which (name, map id, cell number) and the seed; the same SEED loads the same room again (random tests of interior loading) |
| `dbg god` | `dbg godmode` | [on/off, true/false or 1/0; no argument toggles] Quake god mode (no damage; the HUD shows GOD) (not saved) |
| `dbg map format` | - | 2 draws the v2 world map layers (default) / 1 draws a v2 map as the v1 map (terrain and settlements only) |
| `dbg map lava` | - | 1/0 molten lava pools on the world map (M), v2 maps only (default 1, saved) |
| `dbg map tp` | `dbg tp map` | select a destination on the world map (alias) |
| `dbg noclip` | - | - |
| `dbg recover` | - | - |
| `dbg reset location` | - | 0 |
| `dbg scene` | - | ship/town/balmora/<map name> |
| `dbg scene change` | `dbg tp menu` | (scene picker) |
| `dbg superspeed` | - | [on/off, true/false or 1/0; no argument = status and current speeds] the old fixed fast walk/run (cl_forwardspeed, Shift x cl_movespeedkey) instead of the original's speed from Speed, Athletics and load; no running fatigue (default off; not saved; also plain superspeed on/off) |
| `dbg tp` | - | [X Y [Z] original global coordinates (Z: land on the first floor at or below it) / mark or marker (the map marker you set on the map screen) / seydaneen / prisonship / balmora / vivec (the whole city vivec_city, else the Vivec Arena) / tel_uvirith (also teluvirith) / heartchamber / suran / suranclub / aldruhn / <map name>; no argument opens menu] |
| `dbg unstuck` | - | (nearest clear standing spot below or beside you; never into a wall or water; leaves noclip) |
| `dbg view` | - | x y z yaw pitch |
| `dbg worldbounds` | - | [on/off, true/false or 1/0; no argument shows the state] the sea current along the edge of the open world that turns you back (an AmiWind extension; on in a default build) (not saved) |

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
| `dbg indoor luma` | `dbg interior luma`, `dbg interiorluma`, `dbg luma indoor`, `dbg luma interior` | [0..4] (brightness-enabled builds; static interior multiplier; default 1.0; no argument queries) |
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
| `dbg startwinkle` | - | on/off true/false 1/0 (slow, faint pulse of a few bright stars; default on, saved; off = steady stars) |
| `dbg sun` | - | on/off true/false 1/0 (default on, clock still advances) |
| `dbg timeofday` | - | [0..23.999 or morning/night/midday/day/evening/sunset/sunrise/dusk/dawn] |
| `dbg torch flame` | - | [classic/brightbase/sparks or 1/2/3] no argument: current style |
| `dbg torch radius` | - | [32..288] (player + admitted guard lights; default 192, classic 144) |
| `dbg torch strength` | - | [0..1] (player + admitted guards; default 0.7; local light only) |
| `dbg warm light` | - | 1/0 torch, lamp and window light takes the light hue (default 1) |
| `dbg weather` | - | [on/off / skyonly / auto / clear cloudy foggy overcast rain thunder ash blight snow blizzard] region weather: sky, fog and land light from the region's chances (default on, saved; skyonly: sky and fog only; off: clear sky); a name forces it until auto; no argument: the weather and chances |

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
| `dbg sensitivity` | - | [0.1..20, one decimal; no argument prints it] mouse sensitivity, Quake's sensitivity setting (saved; default 3, unchanged; also Options > Controls > Mouse sensitivity, 0.5..10 in steps of 0.5) |

## Diagnostics

| Command | Also | Arguments and notes |
| --- | --- | --- |
| `dbg all` | `dbg overlay` | on/off |
| `dbg blockers` | - | - |
| `dbg cell` | - | (original Morrowind cell here: exterior grid CELL x,y, or interior INT n with its full cell ID; the debug HUD shows the same at the end of its shorter row) |
| `dbg compass` | - | on/off true/false 1/0 (default off) |
| `dbg coords` | - | on/off |
| `dbg dimensions` | - | - |
| `dbg ent` | - | print and pin the current crosshair target; raw entity, source id/ref when retained, model and position. Snapshot, not live; merged scenery may have no source identity. |
| `dbg eyeheight` | - | [offset above player origin] |
| `dbg fps` | - | on/off |
| `dbg fpu` | - | (CPU and FPU support library status: 68040.library/68060.library resident or none) |
| `dbg fpucount` | - | [0/1] once a second: per-frame counts of brush model rotations (and rebuilds), direction vectors, table sine/cosine lookups and NPC targeting (average/peak) |
| `dbg hands` | - | - |
| `dbg heap` | - | (current hunk clearance and load peak) |
| `dbg hud` | - | on/off true/false 1/0; click-to-pin raw target identity (not saved), shown under the stat bars; a CHIM placement is named by mesh, reference and cell. Attack selects while on; right click or off leaves it and restores attacks after releasing the button. Use dbg overlay for overlays without inspection. |
| `dbg hud type` | - | 1 original / 2 compact (default) |
| `dbg logs live` | - | [on/off, true/false or 1/0] write the diagnostic logs (DEBUG.TXT, walk-profile.csv, frame-stalls.csv, heap-audit.log, cell-load-profile.tsv, music-events.csv, ...) as they happen, for benchmarks; default off: kept in memory (oldest lines drop) and written at Exit game or with dbg savelogs (saved once set) |
| `dbg npcfloors` | - | (read-only ground-contact report) |
| `dbg npclod` | - | [auto/0/1/2/3 / target <0..3/auto> / show on/off / bands <d0> <d1> <d2> / stats] NPC model levels (--npc-lod on builds): 0..3 forces a level on every NPC, auto = distance bands; target = the NPC under the crosshair; show labels level, triangles, KiB, distance; bands sets the edges live; stats (not saved) |
| `dbg npcs` | - | - |
| `dbg pos` | - | - |
| `dbg probe` | - | (slow floor audit) |
| `dbg rcount` | - | [0/1/2/3/4] once a second: renderer counts per frame (brush models, faces, clip fragments, edges, spans, surface cache, alias models) and timing split; 2 = remote state file only; 3 = 2 + brush-slot profile (walk/emit split, distance x size table, leaves per placement); 4 = 3 printed |
| `dbg savelogs` | - | write the in-memory diagnostic logs to the game folder now (also done at Exit game) |
| `dbg sealevel` | - | on/off |
| `dbg show fps` | - | [on/off] |
| `dbg showram` | - | on/off |
| `dbg sweep` | - | [actors/plants/doors/lights/statics] each entity class of the loaded area: what the image ships (map entities, door bank, harvest catalogue) against what is live; names each failure (actor without model or animation, harvestable but not pickable, door without a link); last line SWEEP RESULT ok/FAIL (read only) |
