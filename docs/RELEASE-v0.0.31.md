# AmiWind v0.0.31 - Lamps, Lanterns and Loading

Balmora and Seyda Neen at night, lit by their own lamps and lanterns; much
faster loading; the AmiWind Toolkit; and a hard look at what the engine is
asked to draw. This release gathers development builds
[dev1](RELEASE-v0.0.31-dev1.md), [dev2](RELEASE-v0.0.31-dev2.md),
[dev3](RELEASE-v0.0.31-dev3.md), [dev4](RELEASE-v0.0.31-dev4.md),
[dev5](RELEASE-v0.0.31-dev5.md) and [dev6](RELEASE-v0.0.31-dev6.md); details
and measurements are in those notes.

What's new:

- **Night in town:** the original street lamps, lanterns, wall torches and fires
  light Balmora and Seyda Neen at night with warm light; lantern and window
  glass glows; blue lanterns stay blue.
- **Light-space night:** night darkens the light, not the finished picture, so
  torches and glowing materials keep their light after dark.
- **Fire:** fireplaces and braziers burn with flames shaped like the original
  emitters, deep red to a near-white core, with rising embers; torches shed
  embers too. `dbg torchgallery` opens a dark room to look at them.
- **Guard torches** light half as far, so they no longer outshine the lamps.
- **Light hue:** torch, lamp and window light can be any colour
  (`dbg light hue R G B`, or the Hue row in `dbg lightgallery`).
- **Light gallery:** `dbg lightgallery` puts every night-lighting switch in a
  strip below the view, with a time preview.
- **Fog distance slider** (Options > Fog distance, 100-1500), **skyline fill**
  for short fog distances, and optional **location fog** per place.
- **Horizon veil** (`dbg horizon veil`) hazes gaps in distant silhouettes.
- **Faster loading** everywhere, and lighter Seyda Neen sub-cells.
- **Music and opening:** silent start-up until the title music, no stray clips
  while the ship loads, a shorter wait after the intro video, and the ship
  fades in from black.
- **Place names** in the location label, from the original cell names.
- **Time controls:** `dbg time`, `dbg time HHMM`, `dbg 24hrcycle`.
- **Debug headlamp:** `dbg headlamp on` lights dark places without a torch.
- **`dbg lamps`** shows which lamps are lit around you and why.
- **AmiWind Toolkit:** World / Local / 3D Inspector, multi-cell selection,
  scrollbars, keyboard panning.
- **Entity tracker:** the image build counts what the original game places
  against what AmiWind places, and stops if a category goes missing.
- **Builder:** writes the night lamp, glowing glass and location fog tables
  itself, and finishes its last step again.
- **Console:** every `dbg` command sorted and tested; on/off words work for
  every setting.
- **Docs:** a performance page with charts on what the engine is asked to draw,
  and the rule that the repository builds the whole game from scratch.

What we gained (measured):

- **Loading:** game files are read in 16 KiB pieces instead of 1 KiB (a 4.8 MB
  Seyda Neen map took over 4,700 separate disk reads). Seyda Neen region
  crossings: 0.54-0.71 s in v0.0.30, now 0.39-0.48 s on the test route.
- **Seyda Neen maps:** 247.5 MB down to 185.6 MB (-25 %); maps over the modeled
  memory reserve: 43 down to 6.
- **Lamps and lanterns at night:** 694 original street lamps, lanterns, wall
  torches and fires give a torch's worth of warm light from dusk to full day;
  lantern and window glass glows in 79 town maps.
- **Torch light at night:** torches and glowing materials keep their light after
  dark; walls lit by a torch measured about 2.5 times brighter than before.
- **Frame rate control:** Options > Fog distance is now a slider (100-1500); in
  Balmora a fog distance of 250 roughly doubles the frame rate, and the skyline
  stays fogged instead of cut out.
- **Music:** silent start-up until the title music, no stray clips while the
  opening loads, and the prison ship fades in from black.
- **Place names:** the location label reads "Vvardenfell / West Gash Region /
  Balmora" from the original game's cell names.
- **AmiWind Toolkit:** World, Local and 3D Inspector tabs for anyone working on
  AmiWind (below).
- **Console:** 116 `dbg` commands, sorted and tested so every one reaches its
  handler; `dbg time`, `dbg 24hrcycle`, `dbg lightgallery`, `dbg lamps`,
  `dbg headlamp`.
- **Bug tracking:** one register, 186 records, a report page for every bug found
  since v0.0.30.

| | |
| --- | --- |
| ![A Balmora street lamp lights the wall and street at 01:19](images/amiwind-v0.0.31-balmora-night-street-lamp.png) | **01:19, a street lamp.** A torch's worth of warm light on the wall and the street; its glass glows. |
| ![A lamp-lit house in Balmora at 02:18 with a passer-by](images/amiwind-v0.0.31-balmora-night-lamp-house.png) | **02:18, a lamp-lit house.** Pools of light with darker street between, the way a town at night should look. |
| ![The Odai river in Balmora glittering at 22:46](images/amiwind-v0.0.31-balmora-night-river.png) | **22:46, the river.** The water glitters under the night sky. |
| ![A Balmora plaza at 21:38 with a Hlaalu guard carrying a torch](images/amiwind-v0.0.31-balmora-night-plaza-guard.png) | **21:38, a plaza guard.** Guard torches light half as far as before, so they no longer outshine the lamps. |
| ![A Balmora house corner lit by its lamp at 22:36](images/amiwind-v0.0.31-balmora-night-house-corner.png) | **22:36, a house corner.** Lamps stay lit while you turn and walk; a lamp that hands its light to a nearer one fades out instead of snapping off. |

## Loading

Every loose game file is read through a 16 KiB buffer instead of the C
library's 1 KiB default; Seyda Neen's 64 sub-cell maps carry 700 units of
surroundings instead of 896 (draw distance, switching margin and a safety
margin) with ground simplified within 2 units of height
([performance lessons](performance/LESSONS_LEARNED.md),
[Seyda Neen performance](SEYDA_NEEN_PERFORMANCE.md)).

## Night

- Lamps, lanterns, wall torches and fires from the original placements light
  the town at night (`id1/world/lamps.awl`), warm by default; blue lanterns keep
  plain light. Only the nearest lamps get light at once; lamps ahead of you are
  preferred, keep their light while you turn, and fade in and out.
- Lantern and window glass glow at night at any distance
  (`id1/world/night-windows.txt`).
- Light-space night is the default: the night darkens the light itself, so
  torches and glowing materials keep theirs.
- Settings: `dbg outdoorlantern` (lamp reach), `dbg guardtorch` (guard torch
  reach), `dbg light hue R G B`, `dbg lightgallery`, `dbg lamps` (what the lamps
  see here and why).

## Frame rate

- Options > Fog distance opens a slider: drag it, use the arrows (Shift: steps
  of 1) or type a number, 100 to 1500. The fog distance is also the draw
  distance, so it is the biggest frame-rate setting in towns.
- Skyline fill: sky that shows below distant scenery takes the fog colour
  (`aw_skyline_fill`).
- Location fog (`dbg fog location 1`, off by default): places can set their own
  day and night fog distance (`id1/world/fog-locations.txt`).

## Whoops! Actually...

Measuring what the engine is asked to draw showed that Quake's visibility data
never saw our buildings: every converted building, interior room and rock is a
separate brush model, which `vis` ignores, so interiors were 100 % visible from
everywhere and Balmora 84-89 %. The repair (static building faces in the world
model, culled leaf by leaf, plus invisible occluder blocks) is being prototyped
for the next release. [Town visibility](performance/TOWN-VISIBILITY.md),
[TOWN-VIS-OCCLUSION-31](bugs/TOWN-VIS-OCCLUSION-31.md).

## Music and opening

Start-up is silent until the main menu starts the title music; the opening
stops and empties the music until its own track starts; the ship fades in from
black through the palette.

## AmiWind Toolkit

World, Local and 3D Inspector tabs, grid buttons, marker highlight, keyboard
panning, scrollbars when zoomed in, and shift-click / shift-drag multi-selection
that copies out as JSON. See [AmiWind Toolkit](AMIWIND_TOOLKIT.md).

## Console

`dbg time` / `dbg time HHMM`, `dbg 24hrcycle`, `dbg luma`, `dbg lightgallery`,
`dbg lamps`, `dbg headlamp`; on/off words now work for every setting
([DBG-TOGGLE-WORDS-31](bugs/DBG-TOGGLE-WORDS-31.md)). All commands:
[console commands](AMIWIND_CONSOLE_COMMANDS.md).

## Builder

The image builder writes the night lamp, glowing glass and location fog tables
itself ([BUILD-NIGHT-TABLES-31](bugs/BUILD-NIGHT-TABLES-31.md)) and no longer
stops on an undefined name in its last step
([BUILD-FINALIZE-SCENE-31](bugs/BUILD-FINALIZE-SCENE-31.md)). The rule that the
repository builds the whole game from scratch is now in
[DEVELOPMENT.md](DEVELOPMENT.md); this release ships with one recorded exception,
below, and the release gate in [RELEASE_WORKFLOW.md](RELEASE_WORKFLOW.md)
applies from v0.0.32.

## Repaired in this release, awaiting a playtest check

- [MUSIC-STARTUP-TRACK-31](bugs/MUSIC-STARTUP-TRACK-31.md): A random world track plays under the startup logo
- [MUSIC-OPENING-CLIP-31](bugs/MUSIC-OPENING-CLIP-31.md): A clip of another track plays while the opening scene loads
- [AUDIO-LOGO-31](bugs/AUDIO-LOGO-31.md): Music crackles while the startup logo plays (WinUAE)
- [LAMPS-FLICKER-31](bugs/LAMPS-FLICKER-31.md): Night lamps switch on and off while turning or walking
- [GUARD-TORCH-BRIGHT-31](bugs/GUARD-TORCH-BRIGHT-31.md): Hlaalu guard torches over-bright at night
- [NIGHT-RUST-31](bugs/NIGHT-RUST-31.md): Night tint rounds dark colours to rust-red speckle
- [BUILD-NIGHT-TABLES-31](bugs/BUILD-NIGHT-TABLES-31.md): Repository image builds have no night lamp, glowing glass or location fog tables
- [BUILD-FINALIZE-SCENE-31](bugs/BUILD-FINALIZE-SCENE-31.md): Image finalisation stops on an undefined name before media staging
- [LIGHT-OFF-31](bugs/LIGHT-OFF-31.md): Lights flagged Off by default would bake as lit

## Known in this release

- [TOWN-VIS-OCCLUSION-31](bugs/TOWN-VIS-OCCLUSION-31.md): Converted buildings, rooms and rocks do not block Quake visibility (func_wall)
- [LAMPS-RANGE-31](bugs/LAMPS-RANGE-31.md): Only the nearest lamps light up at night
- [BUILD-SEYDA-REGEN-30](BUGS.md): Public build cannot regenerate the Seyda Neen sub-cells
- [SEYDA-LANTERNS-MISSING-31](bugs/SEYDA-LANTERNS-MISSING-31.md): Seyda Neen lanterns light the night but are not in its maps
- [NIGHT-0400-DARK-31](bugs/NIGHT-0400-DARK-31.md): Exterior suddenly much darker around 04:00
- [HORIZON-HOLES-31](bugs/HORIZON-HOLES-31.md): Distant buildings break up against the sky
- [OPENING-BRIGHT-31](bugs/OPENING-BRIGHT-31.md): The prison ship hold is brighter than the original
- [SEYDA-BLOCK-31](bugs/SEYDA-BLOCK-31.md): Invisible obstacle blocks the path on a Seyda Neen slope
- [PLACE-NAMES-INTERIOR-31](bugs/PLACE-NAMES-INTERIOR-31.md): Location label has no place name inside interiors
- [HUD-NOTIFY-OVERLAP-31](bugs/HUD-NOTIFY-OVERLAP-31.md): Console messages print over the location title
- [EMISSIVE-UNSHIPPED-31](bugs/EMISSIVE-UNSHIPPED-31.md): Glowing lantern glass never reached the shipped maps (only the Temple has it)
- [LIGHT-NEGATIVE-31](bugs/LIGHT-NEGATIVE-31.md): Negative (darkening) lights bake as bright white light
- [LIGHT-FALLOFF-31](bugs/LIGHT-FALLOFF-31.md): Interior lights stop dead at their radius
- [LIGHTMAP-GRID-31](bugs/LIGHTMAP-GRID-31.md): Some baked lightmaps sit one sample row or column off
- [SEYDA-WALL-SHAPE-31](bugs/SEYDA-WALL-SHAPE-31.md): Dark shape pokes out of a stone wall by the Seyda Neen shore
- Everything else open in the [bug register](BUGS.md).
