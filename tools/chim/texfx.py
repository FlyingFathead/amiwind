# SPDX-License-Identifier: GPL-3.0-only
"""CHIM texture effects: small text files (.chimfx) that change chosen CHIM textures on purpose.

An effect file is plain UTF-8 text, one `key = value` per line, `#` starts a comment:

    effect  = speckle                       # the only kind so far
    name    = autumn_glitter_leaves         # recorded in the CHIM receipt
    colour  = 255 174 66 47                 # R G B weight; repeat the line for more colours
    density = 0.02                          # share of texels that get a speck (0 < density <= 0.25)
    size    = 1                             # speck size in texels at full size (1 to 4)
    seed    = 1                             # any whole number; the same seed gives the same specks
    targets = ground|* model|*              # texture globs, space separated (see below)

`targets` are shell-style patterns matched against a texture's identity in the CHIM world
(`ground|g100`, `model|120|64|...`; docs/chim/WORLD_FORMAT.md) and against its source texture
path when it has one (`textures/tx_bc_mud.dds`); `*` targets every texture.

Each colour is matched to the nearest entry of the palette the image shows: the build palette
with the image's sky colour bank (sky_palette_overlay.banked_palette) when the palette passes the
bank's guard. A colour on a sky-bank entry is drawn in that entry's colour and follows the sky's
dawn and dusk tint, as every texel follows Quake's colormap under the lightmap.

Specks are placed once at full size and stay put across mip levels: a speck of the full-size
texture is kept at mip level L with probability 4**-L (the same share of texels at every level),
at the texel under its corner, `size >> L` texels wide (at least one). The result depends only on
the effect file and the texture identity, so builds stay byte-identical.

The builder applies effects after the sky-bank translation (CHIM-TEXTURE-SPECKS-33). With no effect
selected (the default) no texture changes. Shipped effects live in tools/chim/effects/; the first,
autumn_glitter_leaves.chimfx, is the bright specks of CHIM-TEXTURE-SPECKS-33 kept as an opt-in look."""
import fnmatch
import hashlib
import struct
from pathlib import Path

import numpy as np

EFFECT_KINDS = ('speckle',)
EFFECTS_DIR = Path(__file__).resolve().parent / 'effects'
KEYS = {'effect', 'name', 'colour', 'density', 'size', 'seed', 'targets'}


def _fail(path, line, message):
    raise ValueError('%s:%s: %s' % (path, line, message) if line else '%s: %s' % (path, message))


def parse_effect(text, path='<effect>'):
    """The effect of a .chimfx text: dict(effect, name, colours [(r, g, b, weight)], density, size,
    seed, targets [glob]). Raises ValueError naming the file and line of the first problem."""
    values, colours = {}, []
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.split('#', 1)[0].strip()
        if not line:
            continue
        if '=' not in line:
            _fail(path, n, 'expected key = value')
        key, value = (part.strip() for part in line.split('=', 1))
        if key not in KEYS:
            _fail(path, n, 'unknown key %r (known: %s)' % (key, ', '.join(sorted(KEYS))))
        if key == 'colour':
            parts = value.split()
            try:
                nums = [int(p) for p in parts]
            except ValueError:
                nums = []
            if len(nums) not in (3, 4) or not all(0 <= v <= 255 for v in nums[:3]) or (
                    len(nums) == 4 and not 1 <= nums[3] <= 1000):
                _fail(path, n, 'colour: expected R G B (0-255) and an optional weight (1-1000)')
            colours.append(tuple(nums) + ((1,) if len(nums) == 3 else ()))
            continue
        if key in values:
            _fail(path, n, '%s given twice' % key)
        values[key] = value
    for key in ('effect', 'name', 'density', 'seed', 'targets'):
        if key not in values:
            _fail(path, None, 'missing %s' % key)
    if values['effect'] not in EFFECT_KINDS:
        _fail(path, None, 'effect: expected one of %s' % ', '.join(EFFECT_KINDS))
    if not colours:
        _fail(path, None, 'at least one colour line is needed')
    name = values['name']
    if not name.replace('_', '').replace('-', '').isalnum() or not name.isascii():
        _fail(path, None, 'name: letters, digits, _ and - only')
    try:
        density = float(values['density'])
        size = int(values.get('size', '1'))
        seed = int(values['seed'])
    except ValueError:
        _fail(path, None, 'density must be a number, size and seed whole numbers')
    if not 0 < density <= 0.25:
        _fail(path, None, 'density: expected more than 0 and at most 0.25')
    if not 1 <= size <= 4:
        _fail(path, None, 'size: expected 1 to 4')
    targets = values['targets'].split()
    if not targets:
        _fail(path, None, 'targets: at least one pattern')
    return {'effect': values['effect'], 'name': name, 'colours': colours, 'density': density,
            'size': size, 'seed': seed, 'targets': targets}


def load_effect(path):
    """parse_effect of a file, plus its path and SHA-256 (recorded in the receipt)."""
    path = Path(path)
    try:
        raw = path.read_bytes()
        text = raw.decode('utf-8')
    except (OSError, UnicodeError) as exc:
        raise ValueError('Cannot read CHIM texture effect %s: %s' % (path, exc)) from exc
    effect = parse_effect(text, str(path))
    effect.update(file=path.name, sha256=hashlib.sha256(raw).hexdigest())
    return effect


def shown_palette(palette):
    """The palette the image shows: with the sky colour bank when the build palette passes its guard."""
    from sky_palette_overlay import bank_safe, banked_palette
    return banked_palette(palette) if bank_safe(palette) else bytes(palette)


def nearest_indices(colours, palette):
    """Palette index nearest to each (r, g, b, ...) colour (squared RGB distance; lowest index on ties).
    Index 255 (transparent in sprites and fences) is never chosen."""
    pal = np.frombuffer(bytes(palette)[:768], np.uint8).reshape(256, 3).astype(int)[:255]
    out = []
    for c in colours:
        d = ((pal - np.array(c[:3])) ** 2).sum(axis=1)
        out.append(int(np.argmin(d)))
    return out


def targeted(effect, identity, source=None):
    """Whether the effect applies to a texture of this identity (and source path)."""
    names = [identity] + ([source] if source else [])
    return any(fnmatch.fnmatchcase(n, pat) for pat in effect['targets'] for n in names)


def speckle_miptex(mip, effect, identity, palette):
    """The miptex with the effect's specks (all four mip levels); transparent texels (255) stay."""
    w, h, *offsets = struct.unpack_from('<6I', mip, 16)
    indices = nearest_indices(effect['colours'], shown_palette(palette))
    weights = np.array([c[3] for c in effect['colours']], float)
    size = effect['size']
    digest = hashlib.sha256(('%s|%d|%s' % (effect['name'], effect['seed'], identity)).encode('utf-8')).digest()
    rng = np.random.default_rng(int.from_bytes(digest[:8], 'little'))
    count = int(rng.binomial(w * h, min(1.0, effect['density'] / (size * size))))
    xs = rng.integers(0, w, count)
    ys = rng.integers(0, h, count)
    keep = rng.random(count)
    pick = rng.choice(len(indices), count, p=weights / weights.sum()) if count else np.zeros(0, int)
    out = bytearray(mip)
    for level, at in enumerate(offsets):
        lw, lh = w >> level, h >> level
        if not at or not lw or not lh:
            continue
        pixels = np.frombuffer(bytes(out[at:at + lw * lh]), np.uint8).reshape(lh, lw).copy()
        side = max(1, size >> level)
        for x, y, k, p in zip(xs, ys, keep, pick):
            if k >= 4.0 ** -level:
                continue
            x0, y0 = int(x) >> level, int(y) >> level
            block = pixels[y0:y0 + side, x0:x0 + side]
            block[block != 255] = indices[p]
        out[at:at + lw * lh] = pixels.tobytes()
    return bytes(out)


def apply_effects(textures, effects, palette):
    """CHIM frame textures ({key: dict(identity, miptex, ..., source?)}) with the effects applied in
    order. Returns (textures, record) where record lists each effect with the identities it changed."""
    if not effects:
        return textures, []
    out = dict(textures)
    record = []
    for effect in effects:
        changed = []
        for key, tex in sorted(out.items(), key=lambda kv: kv[1]['identity']):
            if not targeted(effect, tex['identity'], tex.get('source')):
                continue
            mip = speckle_miptex(tex['miptex'], effect, tex['identity'], palette)
            if mip != tex['miptex']:
                out[key] = dict(tex, miptex=mip)
                changed.append(tex['identity'])
        record.append({'name': effect['name'], 'file': effect.get('file'), 'sha256': effect.get('sha256'),
                       'textures': changed})
    return out, record


def effect_path(value):
    """An effect named on the command line or in a build config: a path, or the name of a shipped
    effect (tools/chim/effects/NAME.chimfx)."""
    path = Path(value)
    if path.suffix != '.chimfx' and not path.exists():
        shipped = EFFECTS_DIR / (value + '.chimfx')
        if shipped.is_file():
            return shipped
    return path
