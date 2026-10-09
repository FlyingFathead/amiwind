# CHIM texture effects

A CHIM texture effect is a small text file (`.chimfx`) that changes chosen textures of a CHIM world
on purpose, the same way in every build. Effects are off by default: a build applies only the
effects you select. The shipped library is `tools/chim/effects/`; anyone can add effects there or
keep their own files elsewhere. The reader is `tools/chim/texfx.py`.

## Selecting effects

- Builder (`build.sh` and friends, with `--builder chim`): `--chim-texture-effect NAME_OR_FILE`,
  repeatable, applied in the order given; or the build config key `chim_texture_effects`, a list of
  names or files (the command line replaces the config's list). The build receipt records each
  effect's name and SHA-256.
- CHIM builder alone (`tools/chim_build.py`): `--texture-effect NAME_OR_FILE`, repeatable.

A name such as `autumn_glitter_leaves` means `tools/chim/effects/autumn_glitter_leaves.chimfx`. The
CHIM receipt (`chim-receipt.json`, `texture_effects`) lists every texture each effect changed.

## File format

Plain UTF-8 text, one `key = value` per line; `#` starts a comment; blank lines are ignored.

| Key | Value |
| --- | --- |
| `effect` | the kind of effect: `speckle` (the only kind so far) |
| `name` | letters, digits, `_` and `-`; recorded in the receipts |
| `colour` | `R G B` (0-255) and an optional weight (1-1000, default 1); one line per colour |
| `density` | share of texels that get a speck, more than 0 and at most 0.25 |
| `size` | speck size in texels of the full-size texture, 1 to 4 (default 1) |
| `seed` | any whole number; the same seed gives the same specks |
| `targets` | texture patterns, separated by spaces (below) |

`targets` are shell-style patterns (`*`, `?`, `[...]`). A texture is changed when a pattern
matches its identity in the CHIM world (`ground|g100` for terrain, `model|...` for model
textures; see [WORLD_FORMAT.md](WORLD_FORMAT.md)) or, for model textures, its source texture path
(`textures/tx_bc_mud.dds`). `*` targets every texture.

## How a speckle effect draws

- Each colour is matched to the nearest entry of the palette the image shows, which includes the
  image's sky colour bank (seven entries repainted as sky colours). A colour on a sky-bank entry
  follows the sky's tint at dawn and dusk.
- Specks are ordinary texels: Quake's colormap shades them under the baked lightmap in the surface
  cache, so they react to light like the rest of the surface.
- Specks are placed once on the full-size texture. A smaller mip level keeps a speck with
  probability 4 to the power of minus the level, so every level has the same share of specked
  texels, and each kept speck stays under its full-size position: specks do not jump when the mip
  level changes. Transparent texels (index 255) are never changed.
- The result depends only on the effect file and the texture's identity, so builds stay
  byte-identical.

Effects run after the sky-bank translation that every CHIM texture gets
([CHIM-TEXTURE-SPECKS-33](../bugs/CHIM-TEXTURE-SPECKS-33.md)). The CHIM validator refuses texels
on the sky bank in every texture except those an effect changed.

## Shipped effects

| File | Look |
| --- | --- |
| `autumn_glitter_leaves.chimfx` | bright orange and cream specks over every texture, glowing at dusk: the look of CHIM-TEXTURE-SPECKS-33, kept as an option |
