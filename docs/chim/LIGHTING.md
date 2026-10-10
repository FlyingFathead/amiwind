# CHIM lighting

Status: design and measurements, 9 October 2026. Owner rule: a cell is only complete when it is lit like the
original. The [cell tracker](CELL_TRACKER.md) checks this per cell with the lighting audit (`tools/cell_lighting.py`).
The open bugs are CHIM-MESHLESS-LIGHTS-33 (lights without a mesh give no light on CHIM),
LIGHT-ENTITIES-UNWIRED-33 (Morrowind lights never become Quake light entities, legacy maps included) and
CHIM-LIGHT-CONTENTS-33 (actors are not lit by CHIM terrain).

<!-- contents start -->
## Contents

- [Where CHIM lighting stands](#where-chim-lighting-stands)
- [How Quake lights a world](#how-quake-lights-a-world)
- [How the original lights a world](#how-the-original-lights-a-world)
- [The options, measured](#the-options-measured)
- [Texture effects and self-lit materials](#texture-effects-and-self-lit-materials)
- [Darkeners and glowing plants](#darkeners-and-glowing-plants)
- [Visibility](#visibility)
- [Decision: the hybrid lighting type](#decision-the-hybrid-lighting-type)
- [First slice](#first-slice)
- [How the numbers were measured](#how-the-numbers-were-measured)

<!-- contents end -->

The steps from here, with their checks and the pending decisions, are in the [CHIM lights roadmap](LIGHTING_ROADMAP.md).

## Where CHIM lighting stands

- Chunk terrain carries one lightmap block of a constant value (the legacy terrain bake had no light sources and
  stored 12 in every sample). Every ground face points at that block.
- Placed models carry no lightmaps. Their faces are drawn with the flat ambient level, dimmed at night.
- The only light sources are runtime ones: the night lamp table (`lamps.awl`, written by `tools/light_sources.py`
  from the lamp, torch, fire and candle classes), drawn as the nearest `aw_lamp_lights` (default 2) dynamic lights at
  night, plus the night-window glow and the guard torches.
- Island-wide (Vvardenfell, 1,292 land cells): 2,284 exterior lights have no mesh (1,936 plain lights, 332 glowing
  plants, 12 darkeners, 4 fires) and 690 have one (545 lamps and lanterns, 70 fires, 69 torches, 6 candles). None of
  them is baked. In the converted cells, 647 reach the frame only as night lamps and 2,279 not at all.
- Tracker result today: lit 0, partial 133, unlit 1,052 (the rest not converted).

## How Quake lights a world

Think in Quake first: Quake already has every piece.

- **Light entities.** A map's `light` entities (origin, `light` value, `_color`, `delay` falloff, `style`) are baked
  by the light compiler (ericw-tools `light`) into **lightmaps**. Each face has up to four styles, and each style is
  one byte per sample on a 16-texel grid (`(extent / 16) + 1` samples per axis).
- **Lightstyles.** `R_AnimateLight` turns each style's string (`a` = dark, `m` = normal, `z` = double) into a value
  ten times a second. `R_BuildLightMap` sums the face's style maps scaled by those values. A surface rebuilds in the
  surface cache only when a style value it uses changes.
- **Alias models** (actors, items) have no lightmaps. `R_LightPoint` samples the world lightmap under the model, and
  the model is drawn at that one level.
- **Dynamic lights** (`dlight_t`, at most 32) add light per frame. Every surface they touch is rebuilt in the
  surface cache every frame while they touch it.
- **Brush entities** (doors, platforms) have their own lightmaps, baked at their map position. Quake never draws one
  brush model at many places, so nothing in Quake keys a lightmap or a cached surface by instance.

AmiWind additions already in the engine:

- Styles 32 and up are never dimmed by daylight; `r_lamps 0` switches them off for A/B.
- Style 31 is the warm-lamp style.
- `emitN_` textures raise a surface's light floor (self-lit materials, `aw_emissive`).
- Night windows glow at night.

## How the original lights a world

From the OpenMW 0.51 source (the reference implementation the project compares against) and the game's records.

| Item | Behaviour |
| --- | --- |
| Light record fields | Radius, colour, flags. Only colour, radius, Negative, Flicker, Flicker Slow, Pulse, Pulse Slow and Off by default change the light. The Fire and Dynamic flags do not. |
| Radius | At least 16. |
| Off by default | The object gives no light. |
| Attenuation | Linear: illumination = 1 / (3 d / r). It is 1/3 at the radius, then fades smoothly to exactly 0 at twice the radius. |
| Negative lights | Their colour is subtracted from the sum. The total is clamped to 0..1 before it multiplies the texture. |
| Flicker | A random walk updated 15 times a second. The step is 0.1, or 0.05 for the slow variant. Brightness moves towards a random target between 0.25 and 1.0. |
| Pulse | The same walk, toggling between 0.25 and 1.0. |
| Objects and terrain | Lit per vertex: sun (one directional light, with N·L) + ambient from the weather and time of day + up to 7 point lights per object, chosen by radius / distance². Lights beyond 8,192 units fade out. |
| Terrain vertex colours | The terrain's vertex colours (VCLR) multiply both the light and the ambient. |
| Point lights by time of day | Always on: there is no time-of-day switch. By day the sun dominates, so a lamp shows mostly in shade. |
| Lights without a mesh | Placed as pure light sources. |
| Lights with a mesh | The light sits on the mesh's `AttachLight` node when it has one, otherwise on the object's origin. |
| Glow (emissive) | A material property of the mesh, separate from the light record. It is added after lighting and is not affected by lights. |

So an exterior cell needs three things to look like the original:

- sun and ambient shading of terrain and objects;
- the point lights around their sources, all of them, all the time;
- the self-lit materials.

## The options, measured

All figures are from a v0.0.33-rc1 development build's CHIM world (world format 0.5): Balmora (frame -3,-2: 576
chunks, 1,473 placements, 48 lights) and Seyda Neen (frame -2,-9: 441 chunks, 360 placements, 60 lights). Sizes
follow the engine's lightmap rule. Ring figures are the CHIM heap gate's own computation (`tools/chim/heap.py`,
target ABI sizes), with each option's bytes added to the chunk that brings them.

The active-ring budget is 6,242,304 bytes. Without lighting:

- Balmora peaks at 6,239,776 (**2,528 bytes of headroom**);
- Seyda Neen peaks at 5,683,920 (558,384 bytes of headroom).

| Option | What is stored | Balmora stored / active-ring peak (headroom) | Seyda Neen stored / active-ring peak (headroom) |
| --- | --- | --- | --- |
| today | constant terrain block, no model light | 0 / 6,239,776 (+2,528) | 0 / 5,683,920 (+558,384) |
| a: terrain lightmaps + per-placement lightmaps | geometry shared, one lightmap set per placement | 2,021,087 / 6,528,736 (**-286,432**, 19 positions over) | 1,201,306 / 6,289,680 (**-47,376**, 8 positions over) |
| b: terrain lightmaps + one light sample per placement | 4 bytes per placement | 329,508 / 6,256,992 (**-14,688**, 1 position over) | 277,392 / 5,710,752 (+531,552) |
| c: terrain lightmaps + per-placement vertex light | 1 byte per model vertex and placement | 458,201 / 6,288,816 (**-46,512**) | 314,970 / 5,739,936 (+502,368) |
| d: dynamic lights only | nothing | 0 / unchanged | 0 / unchanged |
| e: b + per-placement lightmaps only where a light reaches | lightmaps for 53 of 1,473 (Balmora) and 104 of 360 (Seyda) placements | 406,596 / 6,287,008 (**-44,704**) | 696,250 / 6,056,160 (+186,144) |

Lights that animate need a second style on the faces they reach. Upper bound, two styles on every face:

- a: -571,264 (Balmora) and -700,528 (Seyda);
- b: -33,152 and +503,168;
- e: -92,768 and -186,432.

The load ring (everything a moving player can hold locked) is already over budget in Balmora without lighting
(7,661,472). The engine gates the active ring.

**Where the light falls.** Source light reaches only part of the samples:

| Frame | Terrain samples lit by sources | Placed-model samples lit by sources (option a) |
| --- | --- | --- |
| Balmora | 6,914 of 378,262 (1.8 %) | 178,264 of 1,697,146 (10.5 %) |
| Seyda Neen | 66,358 of 315,370 (21 %) | 144,167 of 924,000 (15.6 %) |

Everywhere else a per-placement lightmap would only hold sun and ambient. On a flat face that is one value.

**Bake time.** Single thread, the measuring module's numpy baker, without shadows:

| Frame | Terrain | Every placed-model sample (option a) |
| --- | --- | --- |
| Balmora | 4.3 s | 119.5 s |
| Seyda Neen | 3.9 s | 29.4 s |

The baker is a per-face loop, so these are upper bounds for the same work vectorised or run on the worker pool. The
light compiler with shadows (ericw-tools `light` on a chunk image) is not measured yet.

**Dynamic lights (d).** Per player position, sampled every 64 units:

| Frame | Lights whose reach touches the view (540 units): median / 90 % / max | Reaching the player at once: max |
| --- | --- | --- |
| Balmora | 0 / 6 / 19 | 3 |
| Seyda Neen | 3 / 6 / 15 | 5 |

The engine shows 2 today (`aw_lamp_lights`). Every surface a dynamic light touches is rebuilt in the surface cache
every frame, so many dynamic lights cost frame rate, not memory.

**Look.** Not captured yet. Evidence frames (night and noon, headlamp off, plus headlamp-on pairs and OpenMW
reference views at the same poses) come with the first slice. Builds are on hold until the integration head carries
today's builder fixes.

What each option gives:

- **a** is how Quake lights brush models. It gives the original's light pools on walls next to lamps, but costs about
  1.2-2.0 MB per frame on disk and 0.3-0.6 MB in the ring. It does not fit either town.
- **b** gives shaded terrain with light pools on the ground. Objects get one level each, like Quake's alias models:
  correct brightness, but no pool of light across one wall.
- **c** is closest to the original's per-vertex lighting. The span renderer would have to build lightmaps from vertex
  values in the surface cache, and it costs more than b.
- **d** is free in memory, but expensive per frame and limited to the nearest few lights.
- **e** puts the lightmap bytes where the light is. It fits Seyda Neen, and is 45 KB over in Balmora.

## Texture effects and self-lit materials

The CHIM texture effects (`.chimfx`, [TEXTURE_EFFECTS.md](TEXTURE_EFFECTS.md)) are a build-time texel painter. They
rewrite chosen texels of chosen textures, with no runtime code, no extra stored bytes and no time-of-day variants. The
AmiWind palette has no full-bright rows: index 224 is the fog colour, 225-253 are the reserved interface bank, 255 is
transparent, and 7 sky-bank entries are tinted by the sky. So a texel can never ignore the lightmap. The self-lit tool
the engine has is `emitN_`: a surface whose texture name starts with `emitN_` gets a light floor of N/9, and light
adds on top.

For glowing plants (owner decision 2026-10-09) this becomes **per-plant glow effects generated by the builder**:

- The colours come from the plant's own texture and, where it has one, its light's colour, fitted to palette entries
  outside the reserved and sky-bank ranges, so the palette check stays clean.
- The glowing texels are marked through the same effect machinery.
- The texture is given an `emitN_` level, so the glow survives the night.
- Nothing asset-derived is committed: the generator, the format additions, the options (`--chim-plant-glow on|off`)
  and the tests are public, and every effect file is written at build time from your own data.

Limits:

- An effect cannot put light on neighbouring surfaces. That light is the plant's light record, baked or dynamic like
  any other light.
- A shared texture glows on every model that uses it.

## Darkeners and glowing plants

- **Darkeners (12 exterior, all without a mesh).** Negative lights bake as negative values in the same styles as the
  light they darken, so the sum of a face's light never goes below zero (LIGHT-NEGATIVE-31 was the opposite bug: they
  baked as white light). Dynamic darkeners are not possible: Quake dynamic lights only add.
- **Glowing plants (332 exterior light records, all without a mesh).** Two parts:
  - the plant's own glow is self-illumination: the per-plant effect plus an `emitN_` level;
  - the light record lights the ground and objects around it: baked, or dynamic, like any light.

## Visibility

Lighting adds no entity and no brush:

- light entities exist only at bake time;
- the per-placement sample is a field of the existing placement record;
- dynamic lights mark surfaces through the same leaves and nodes as today (`R_MarkLights`).

The renderer counters (entities sent, faces drawn, BSP nodes per face) must not change. Animated styles raise
surface-cache rebuilds only on faces those lights reach, as in Quake. The renderer counters (`dbg rcount`) and the
surface-cache build count are compared before and after on the benchmark cameras.

## Decision: the hybrid lighting type

The owner approved the hybrid on 9 October 2026. It is the builder's default for CHIM builds. The option is
`--chim-lighting-type` (config key `chim_lighting_type`; see `tools/chim/light_types.py`):

| Type | What it does | State |
| --- | --- | --- |
| `none` | No light sources: constant terrain light, models without lightmaps, an empty night lamp table | available |
| `lamps` | The v0.0.33 lighting: constant terrain light, models without lightmaps, the night lamp table (lamps, lanterns, torches, fires and candles as the nearest dynamic lights at night) | available |
| `hybrid` | The parts below | **default**; parts land step by step ([roadmap](LIGHTING_ROADMAP.md)) |
| `baked-e` | `hybrid` plus per-placement lightmaps for the placed models a light reaches | reserved: later, for an increased-memory version of the game |
| `full` | Per-chunk terrain lightmaps and per-placement lightmaps for every placed model | reserved: later, for an increased-memory version of the game |

The reserved types are refused with a message that says why. Previous methods stay selectable (DON'T DELETE ANY
METHOD): `lamps` is the v0.0.33 lighting.

The parts of `hybrid`:

1. **Terrain:** per-chunk lightmaps.
   - Sun and ambient go in style 0, dimmed by daylight.
   - Every light source goes in style 32, never dimmed: the original's lights never switch off.
   - Animated sources use styles 33-36 (flicker, slow flicker, pulse, slow pulse). Their strings are generated from
     the original's random-walk rates and set in QuakeC `worldspawn`.
   - Darkeners are negative in styles 0 and 32.
   - Cost: +17 KB (Balmora) and +27 KB (Seyda Neen) in the active ring with one style.
2. **Placed models:** one light sample per placement, taken from the baked light at the placement (sun, ambient and
   sources). It is drawn as Quake draws alias models: the per-entity level enters the surface cache's light check, so
   a cached surface rebuilds when it is drawn for a placement with another level. 4 bytes per placement.
3. **Light falling on objects near a source:** the nearest sources as dynamic lights, of every class that adds light
   (lights without a mesh included). This is the night lamp table widened from 694 to 2,962 exterior sources;
   darkeners stay out, because dynamic lights only add.
4. **Glowing plants:** per-plant glow effects plus `emitN_`, generated at build time.

What is in source today:

- the style scheme (LIGHT-STYLES-UNDEFINED-33);
- the widened lamp table (part 3, at night as before);
- the light-entity text (`light_sources.entity()`), with two entities per darkener.

The CHIM receipt records the type and the state of each part (`lighting` in `chim-receipt.json`).

Still open (owner decision pending): Balmora has 2,528 bytes of active-ring headroom, so any stored light needs room
made in Balmora's ring (CHIM-BALMORA-LIGHT-ROOM-33). The +17 KB of the terrain lightmaps can come from:

- a smaller hysteresis or draw distance in Balmora;
- the house models (258-292 KB each);
- a larger CHIM zone.

Seyda Neen and the open world have room. The legacy maps get the same light entities through the same shared
function (`light_sources.entity()`), which closes LIGHT-ENTITIES-UNWIRED-33 on that side.

## First slice

The first slice covers Seyda Neen on CHIM and one open-world ring of converted cells. Balmora follows once its ring
room is decided. The builds and bakes are queued until the open world is in (owner priority, 9 October 2026).

- the shared light-entity output (`light_sources.py`) for CHIM and the legacy converters;
- the style mapping, including the generated flicker and pulse strings (in source);
- the terrain bake in the CHIM builder;
- the per-placement sample, with the engine side of it;
- the lighting figures in the build stats (`stats.lighting`: type, terrain and model faces lit, lights baked), which
  the tracker reads;
- a lighting MiniWind preset.

Evidence:

- the same poses unlit and lit, at night and at noon, headlamp off, plus headlamp-on pairs;
- OpenMW reference views (Seyda Neen and Balmora streets with lamps, a glowing-plant area on the Bitter Coast, a
  darkener where one is in range);
- the heap audit per ring and the bake time.

## How the numbers were measured

- `tools/chim/lighting.py measure WORLD --sdk SDK --master Morrowind.esm [--styles N]`: stored bytes and ring peaks
  per option. The ring computation is `tools/chim/heap.py` `ring_peak` with each option's bytes as `chunk_extra`.
- `tools/chim/lighting.py bakework WORLD --master Morrowind.esm`: lights per frame, samples within a light's reach,
  bake time.
- Light classes come from `tools/light_sources.py`. The island-wide counts come from the tracker's lighting audit
  (`tools/cell_lighting.py`).
- Host: busy (other build jobs were running). Bake times are single-thread figures and relative, not final speed
  claims.
