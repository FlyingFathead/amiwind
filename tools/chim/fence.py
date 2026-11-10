# SPDX-License-Identifier: GPL-3.0-only
"""See-through ("fence") textures of the CHIM world (ROOM-DECAL-ALPHA-62, CHIM-MODEL-FENCE-FACES-64).

The original meshes draw cobwebs, hanging vines and moss, decals and grates as planes whose texture has an alpha
channel: the texels under half alpha are not drawn. The engine draws world, room and model faces through the surface
cache and the span renderer, which had no such texel kind, so every one of them showed as a solid sheet. Now:

- a texture whose alpha channel leaves at least FENCE_MIN_SHARE of its texels under FENCE_ALPHA is a fence texture;
- its image is quantized without palette index 255, and every transparent texel is set to 255 (the index the engine
  already skips in sprites and pictures, tools/chim/texfx.py);
- its engine name starts with '{' (engine/aga/src/model.h AW_FENCE_TEXTURE_PREFIX); the engine draws such faces in
  its fence pass (engine/aga/src/d_fence.c, aw_fence).

Every other texture is untouched: its unit stays a 'texture' unit with the same key, its bytes stay the same. A fence
texture is its own unit kind ('texture-fence', chim.units), so this module's code keys only those.
"""
import struct

import numpy as np

FENCE_PREFIX = '{'
FENCE_INDEX = 255
FENCE_ALPHA = 128           # a texel under this alpha is transparent (an alpha test at half, as the original's)
FENCE_MIN_SHARE = 0.01      # at least this share of transparent texels makes a fence texture
_SHARE = {}                 # texture record sha256 (or path) -> transparent share, per process


def texture_rgba(archive, record):
    """The texture's RGBA texels as an (h, w, 4) uint8 array (the scenery archive's format: '>4sHH' + RGBA)."""
    from mwad.scene import read_asset
    try:
        raw = read_asset(archive, record)
    except ValueError as exc:
        # name the record and the archive (CHIM-FENCE-WRONG-ARCHIVE-64); read_asset itself stays unchanged, since it
        # is in the code key of every mesh and texture unit
        raise ValueError('%s: %s at offset %s, %s bytes, archive %s' % (
            exc, record.get('source') or record.get('name') or record.get('path') or str(record.get('sha256', '?'))[:16],
            record.get('offset'), record.get('bytes'), getattr(archive, 'name', '?'))) from exc
    _, w, h = struct.unpack_from('>4sHH', raw)
    return np.frombuffer(raw[8:8 + w * h * 4], np.uint8).reshape(h, w, 4)


def transparent_share(archive, record):
    """Share of texels under FENCE_ALPHA in the texture of RECORD (a scenery index texture record)."""
    key = record.get('sha256') or repr(sorted(record.items()))
    if key not in _SHARE:
        alpha = texture_rgba(archive, record)[:, :, 3]
        _SHARE[key] = float((alpha < FENCE_ALPHA).mean()) if alpha.size else 0.0
    return _SHARE[key]


def material_record(texture_records, model, material):
    """The texture record of MODEL's MATERIAL as the model names it (its texture_index), the record that pairs with
    the model's own archive (model['_archive'] when it has one), or None. A record found by the texture's hash can
    belong to another archive's index (CHIM-FENCE-WRONG-ARCHIVE-64)."""
    mats = model.get('materials') or []
    if not isinstance(material, int) or not 0 <= material < len(mats):
        return None
    ti = mats[material].get('texture_index')
    return texture_records[ti] if ti is not None and 0 <= ti < len(texture_records) else None


def is_fence(archive_path, record):
    """True when the texture of RECORD is see-through (FENCE_MIN_SHARE of its texels under FENCE_ALPHA)."""
    if record is None or not archive_path:
        return False
    with open(archive_path, 'rb') as archive:
        return transparent_share(archive, record) >= FENCE_MIN_SHARE


def engine_name(kind, glow, texture_id):
    """The miptex name the engine sees: '{surfaceN' for a fence texture, else chim.models.engine_texture_name."""
    if kind == 'fence':
        return FENCE_PREFIX + 'surface%d' % texture_id
    from chim.models import engine_texture_name
    return engine_texture_name(kind, glow, texture_id)


def fence_image(archive, index, model, material, size, palette_image):
    """The fence texture's quantized image: prepare_mesh_bsp.material_image's colours (diffuse tint, resize) quantized
    without index 255, then 255 on every texel whose resized alpha is under FENCE_ALPHA."""
    from PIL import Image
    mat = model['materials'][material]
    rgba = texture_rgba(archive, index['textures'][mat['texture_index']]).astype(float)
    rgb = rgba[:, :, :3] * np.array(mat['diffuse'])
    colour = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).resize((size, size))
    alpha = np.asarray(Image.fromarray(rgba[:, :, 3].astype(np.uint8)).resize((size, size)))
    # a palette without index 255: its colour is index 0's, so the nearest colour is never 255
    pal = list(palette_image.getpalette()[:768])
    pal += [0] * (768 - len(pal))
    pal[765:768] = pal[0:3]
    no255 = Image.new('P', (1, 1))
    no255.putpalette(pal)
    pixels = np.array(colour.quantize(palette=no255, dither=Image.Dither.NONE))
    pixels[pixels == FENCE_INDEX] = 0
    pixels[alpha < FENCE_ALPHA] = FENCE_INDEX
    return Image.fromarray(pixels.astype(np.uint8), 'P')


def fence_texture_unit(task):
    """One fence texture as a miptex with a placeholder name (a pool worker; chim.models.texture_unit's task)."""
    from PIL import Image
    from prepare_quake import miptex
    pal = Image.new('P', (1, 1))
    pal.putpalette(task['palette'])
    with open(task['archive'], 'rb') as archive:
        im = fence_image(archive, {'textures': task['textures']}, task['model'], task['material'], task['size'], pal)
    return {'miptex': miptex(engine_name('fence', 0, 0), im), 'size': list(im.size), 'kind': 'fence', 'glow': 0}
