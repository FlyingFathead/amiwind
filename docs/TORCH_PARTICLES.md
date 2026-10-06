# Torch particles and light reach

The dev4 source candidate adds an optional first-person spark variant:

```text
dbg torch flame sparks
```

Saved config `aw_torch_flame_style 3` selects it. `1` / `classic` retains the
current default and `2` / `brightbase` retains the earlier bright-root variant.
Sparks have a brief near-white phase, then bright yellow and orange. The active
palette supplies the nearest colours; this is an indexed software effect,
not HDR bloom. The candidate's in-game appearance and frame cost remain pending.

## AmiQuake source study

Reviewed the pinned [AmiQuake revision](https://github.com/terriblefire/amiquake/tree/9c62d905151614af3e788ae3145a0d4ecc8a7bb8),
the same upstream revision recorded by the AGA runtime:

- [`r_part.c`](https://github.com/terriblefire/amiquake/blob/9c62d905151614af3e788ae3145a0d4ecc8a7bb8/src/r_part.c):
  a reusable particle pool, short-lived directed particles, rocket fire colour
  ramps, rising fire motion and gravity for other particle types.
- [`d_part.c`](https://github.com/terriblefire/amiquake/blob/9c62d905151614af3e788ae3145a0d4ecc8a7bb8/src/d_part.c):
  projected indexed-colour points with bounded pixel size and depth testing.

The generic explosion routines create hundreds of particles and Quake's numeric
palette ramps assume its own palette. They are not suitable to call unchanged
for a small continuously burning converted torch. The candidate adapts lifetime,
motion and palette-ramp ideas with four bounded phase slots, no allocations,
no shared random-number consumption and no additional dynamic lights.

The first-person candidate uses the selected hand model's matching authored
emitter and the existing flame overlay clipping. It is currently specific to
3D first-person hands. Guard/world embers need their own depth-tested acceptance;
this change does not claim that those emit sparks. Existing guard bright-base
colouring is shared. No upstream binary, texture or game data is imported.

## Surface lighting is independent

The carried light already has a three-dimensional point origin. Current saved
`aw_torch_radius` defaults to 192, with a bounded 32-288 range:

```text
dbg torch radius 240
dbg torch radius 192
```

The second command restores the current default. The control affects the player
and admitted guard lights. It does not add lights or change flame size.
Range and the surface-distance falloff determine which floors, side walls and
overhead surfaces receive useful light. Sprite/alias objects and fullbright or
saturated surfaces require separate checks; bright particles prove no additional
surface illumination. Keep the established dev3 lighting available for A/B use.

The dev4 follow-up asks for a fuller pool of light above and beside the player.
Compare the same position at radii 192, 240 and 288, with off/on captures looking
down, sideways and upward, before choosing a new default or a new falloff method.
Record actual indexed-pixel changes and frame cost; do not increase ambient light
to conceal a local-light defect.

## Verification status

Focused Linux Docker checks exercised the actual flame framebuffer with padded
rows and an offset viewport, all three spark colours, repeated frozen draws,
legacy restoration and unchanged light-radius state. A separate real-lightmap
probe produced matching responses for equivalent floor, ceiling and four wall
orientations. These are synthetic renderer results, not native scene acceptance.
Amiga object compilation and native presentation are recorded separately.
