# Character sprite pipeline proposal

This is a design for future work. No character baker or sprite renderer is
implemented in the current version. OpenMW is the intended host-side rendering
foundation; its capture integration still needs to be built. See `OPENMW_BAKER.md`.

## Body templates and appearance recipes

`config/character_templates.json` records the initial design. It is configuration
for planning, not a working baker or a map of original equipment records.

Separate reusable body/rig templates from appearance and behaviour:

| Layer | Examples | What can be shared |
| --- | --- | --- |
| Rig family | Compatible humanoid skeleton; other anatomy separately | Animation sampling and pose definitions |
| Body profile | Race/proportions, male/female model variant | Body assembly rules for that profile |
| Appearance | Head, hair, skin and equipped items | One recipe reused by multiple NPC instances |
| Combat style | Unarmed, one-handed, two-handed, ranged, spellcasting | Compatible clip sets and event conventions |
| NPC instance | Position, dialogue and gameplay state | References to the shared appearance assets |

Male/female variants alone do not guarantee skeleton compatibility. Body
proportions, anatomy and the original animation conventions may require separate
families. Use the original actor assembly rather than forcing every model onto
one invented skeleton.

A bare-knuckle fighter and a spellcaster can share a compatible body template
while using different action clips. A sword/shield outfit needs weapon attachment,
hand pose, occlusion and attack timing appropriate to that equipment. Combat
style is an animation selection property, not a baked personality of the NPC.

For each character, resolve the appearance and current combat style, select a
compatible clip, and look up the required baked frame. The first baker should
produce complete dressed frames. Templates reduce duplicated assembly and
animation setup; visibly different clothes still produce different pixels.

## Bake on the PC

Build an appearance recipe from body/race, sex, head, hair, equipped clothing,
armour and weapons. Assemble the original models, play a selected animation,
capture controlled viewpoints and times, then quantize and pack the frames into
Amiga planar bitmaps plus masks. Keep frame duration, ground anchor and event
markers alongside the pixels. All outputs live in the external workspace.

OpenMW documents equipment access and mutation through its Actor API, and
animation control through `openmw.animation`. Those are useful building blocks.
A deterministic batch renderer still needs integration: isolated scene, known
lighting/background, fixed camera, animation sampling and reproducible capture.
The documented Lua API alone does not establish a complete offline exporter.

## Avoid the full combination explosion

Do not bake every item on every character in every possible combination.

1. Begin with the actual equipped appearances used by NPCs in the chosen area.
2. Give each unique appearance a stable key. Many NPC instances can share it;
   dialogue and gameplay state remain separate from the image asset.
3. Add only the animation states needed for the current prototype.
4. Bake a small number of directions and sizes, with more detail nearby later.
5. Cache converted frames by recipe rather than NPC identity. Invalidate them
   when inputs, palette, sampling settings or renderer version change.

The key should cover source asset hashes, appearance/gear, animation track and
sample times, camera directions, output sizes, palette and converter version.
Use a dependency manifest so changing one item rebuilds only affected recipes.
Identical resulting frames can also be deduplicated.

## Concrete footprint example

A 32 × 64 frame using four colour bitplanes and one mask is 1,280 bytes, before
alignment metadata, compression or extra copies. This is 1.25 KiB per frame.

| Example at one size | Frames | Uncompressed bitmap/mask bytes |
| --- | ---: | ---: |
| 8 views × 6 walking frames | 48 | 60 KiB |
| 8 views × (2 idle + 6 walk + 6 attack + 2 hit + 6 death) | 176 | 220 KiB |
| Same set at 64 × 64 | 176 | 440 KiB |

These are proposed sample counts, not extracted Morrowind animation lengths.
Weapon swings and large creatures may require wider/taller bounds. Additional
outfits and scales multiply storage. Compression reduces disk/cache bytes but
not the size of the decoded bitmaps in Chip RAM.

Do not keep complete sets for every nearby character in Chip RAM. Keep current
frames and a small look-ahead cache; prefetch likely directions/actions using
world state. Share frames between identical appearances. Test abrupt direction
changes and attack transitions to establish how much look-ahead is sufficient.

## Clothing and equipment changes

For the first scene, bake complete dressed actors. This preserves occlusion,
body-part replacement and weapon placement with the least runtime complexity.

Dynamic equipment needs more work. Options include a bounded library of supported
appearance combinations or reusable body/equipment layers. Layers can avoid some
combination growth, but a simple shirt pasted over a flat body image is not enough:
arms, shields, robes and weapons pass in front of and behind one another throughout
animations. Correct layered output needs viewpoint/pose-specific masks and depth
or ordering information, and possibly precomposed cached frames.

Do not promise arbitrary equipment combinations until that compositor has been
demonstrated. A first-person-only prototype can avoid rendering the player's
full third-person body, but that does not solve NPC equipment changes.

## Animation details that matter

Attack frames need game-time event markers for contact, recovery and projectile
release; displaying a sword swing does not implement combat. Keep animation
timing independent of rendering frame rate. Different weapon families may need
different tracks. Movement, hit reactions, death and later casting/swimming add
their own states. Mirroring can save assets only where handedness, equipment and
asymmetric clothing remain correct.

Use stable ground anchors and common camera framing to avoid jitter. Bake to a
shared world/actor palette or a measured palette strategy; each character cannot
simply bring an unrelated 16-colour palette to the same OCS screen.

## What can be offloaded

| Work | Intended location |
| --- | --- |
| Mesh assembly, skeleton animation, lighting, capture, palette conversion | PC before play |
| Scene position, visible direction, animation state, sorting and cache requests | 68000 |
| Masked planar bitmap drawing | Blitter where measurements favour it |
| Music/speech/effects sample playback | Paula DMA, with CPU/storage refills |

The blitter can draw masked bitmaps but cannot assemble NIF characters, run their
skeletons, or provide free arbitrary sprite scaling. Pre-bake sizes or measure
a restricted scaling path. BOB drawing consumes Chip RAM bandwidth; it is not
free alongside the terrain renderer and display DMA.

## First bake experiment

One humanoid, one outfit, eight views, idle plus walking and one attack, one
output size. Confirm appearance, anchors, event timing, bytes and masked blit
cost before expanding to the whole town. Then change one clothing item and
measure rebuild/caching behaviour. The original game files stay user supplied.

References: [OpenMW animation API](https://openmw.readthedocs.io/en/latest/reference/lua-scripting/openmw_animation.html),
[OpenMW actor/types API](https://openmw.readthedocs.io/en/latest/reference/lua-scripting/openmw_types.html),
[Commodore blitter hardware](https://www.theflatnet.de/pub/cbm/amiga/AmigaDevDocs/hard_6.html).
