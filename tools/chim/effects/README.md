# CHIM effects library

Texture effects for CHIM worlds, one `.chimfx` file each. They are off by default; select one with
the builder's `--chim-texture-effect NAME` (or `tools/chim_build.py --texture-effect NAME`), where
NAME is the file name without `.chimfx`.

A `.chimfx` file is plain text, one `key = value` per line, `#` for comments:

    effect  = speckle
    name    = my_effect
    colour  = 255 174 66 47      # R G B weight, one line per colour
    density = 0.02               # share of texels with a speck
    size    = 1                  # speck size in texels
    seed    = 1                  # same seed, same specks
    targets = ground|* model|*   # texture patterns (identity or source texture path)

The full format and how the specks are drawn: docs/chim/TEXTURE_EFFECTS.md.

| Effect | Look |
| --- | --- |
| autumn_glitter_leaves | bright orange and cream specks over every texture, glowing at dusk |
