#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Magic effects as Quake sprites and particles (docs/MAGIC_EFFECTS.md): the image step's import.

From the user's own game data (never stored in the repository) this writes into the image's id1:
  gfx/magic.awm          the effect table the engine reads (aw_magic.h, aw_magic_rules.c): per chosen magic effect
                         its school and colour, and per phase (hand glow, cast, bolt, hit, area) the length, the
                         sprite, the sound and up to three particle emitters read from the effect mesh;
  progs/awmx_NN.spr      one Quake sprite per effect texture used (32x32, four fade frames), from the texture
                         itself: its colours in the image palette, its see-through or additive glow as a dither;
  sound/aw/magic/*.wav   the phase sounds (the effect's own, else its school's), converted like the combat sounds.

Which mesh plays when, and which texture an effect lends its meshes, follow OpenMW's rules (its spellcasting.cpp,
character.cpp, projectilemanager.cpp, nifloader.cpp; nothing copied): a phase without its own visual takes
VFX_DefaultCast / Bolt / Hit / Area; the hand glow is VFX_Hands; the effect's particle texture replaces only the
texture the mesh's root node names first. The engine shows the result only with aw_magic_fx 1 or 2 (default 0).
"""
import io
import json
import math
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

FORMAT = 'AWMG1'
TABLE = 'gfx/magic.awm'
SOUND_DIR = 'sound/aw/magic'
SCALE = 0.25                     # Morrowind units to map units (prepare_quake.SCALE)
SPRITE = 32                      # sprite side in pixels (aw_magic.h AW_MAGIC_SPRITE_PIXELS)
FADES = (1.0, 0.7, 0.45, 0.25)   # the four fade frames' strength
RAMP = 8
EMITTERS = 3
SCHOOLS = ('alteration', 'conjuration', 'destruction', 'illusion', 'mysticism', 'restoration')
# The effects dbg cast fires: one bolt per school at least (destruction's elements each), by magic effect index.
EFFECTS = (('fire', 14), ('frost', 16), ('shock', 15), ('poison', 27), ('drain', 18), ('burden', 7),
           ('levitate', 10), ('shield', 3), ('paralyze', 45), ('light', 41), ('dispel', 57), ('heal', 75),
           ('fortify', 79), ('turnundead', 101), ('summon', 102))
# phase: (record field, default visual, sound field, school sound word)
PHASES = (('hand', None, 'VFX_Hands', None, None), ('cast', 'CVFX', 'VFX_DefaultCast', 'CSND', 'cast'),
          ('bolt', 'BVFX', 'VFX_DefaultBolt', 'BSND', 'bolt'), ('hit', 'HVFX', 'VFX_DefaultHit', 'HSND', 'hit'),
          ('area', 'AVFX', 'VFX_DefaultArea', 'ASND', 'area'))
# the failed cast: a sound only, the school's "Spell Failure <School>" (rule from OpenMW mwworld/store.cpp and
# mwmechanics/spellcasting.cpp: a failed roll plays it at the caster and no effect)
FAIL = 'fail'
FAIL_LENGTH = 1.0
# the bubble: the translucent, coloured sphere that wraps a caster while casting and a target while a spell holds on
# it (the game's cast and hit shells; OpenMW mwrender/animation.cpp addEffect attaches them to the actor, looping for
# continuous effects): one sprite per effect, the shell texture rendered onto a sphere seen from outside
BUBBLE = 'bubble'
BUBBLE_LENGTH = 1.5
PHASE_ORDER = tuple(p[0] for p in PHASES) + (FAIL, BUBBLE)
SOUND_FIELDS = (('cast', 'CSND'), ('bolt', 'BSND'), ('hit', 'HSND'), ('area', 'ASND'))
# particles per phase, shared by its emitters (the bolt's: a second of trail): a 68040 budget, not the original's
CAPS = {'hand': 20, 'cast': 40, 'bolt': 30, 'hit': 40, 'area': 56}
# the sprite's world size (map units): the extent of the emitter's particle cloud (one sprite stands for the many
# overlapping particles of the original), kept within these. The particle's own size alone (4-12) showed as a few
# pixels: the textures' glow fills about a third of the tile (FS-UAE session fx1, 2026-10-27).
SPRITE_SIZE = {'hand': (0, 0), 'cast': (8, 24), 'bolt': (10, 24), 'hit': (16, 48), 'area': (24, 96)}
BAYER = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))


def zstring(raw):
    return raw.split(b'\0')[0].decode('cp1252', 'replace')


def read_records(data_files):
    """MGEF rows by index, visual models (STAT, WEAP) and sound files (SOUN) by lower-case id, GMST floats:
    Morrowind.esm, then Tribunal.esm and Bloodmoon.esm when present (a later master's record wins)."""
    from mwad.esm import records, subrecords, is_deleted
    from mwad.paths import child_ci
    mgef, models, sounds, gmst = {}, {}, {}, {}
    for name in ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm'):
        path = child_ci(Path(data_files), name, required=name == 'Morrowind.esm')
        if path is None:
            continue
        for kind, flags, payload in records(path.read_bytes()):
            if kind not in ('MGEF', 'STAT', 'WEAP', 'SOUN', 'GMST'):
                continue
            fields = list(subrecords(payload))
            if is_deleted(flags, fields):
                continue
            if kind == 'MGEF':
                row = {}
                for tag, value in fields:
                    if tag == 'INDX':
                        row['index'] = struct.unpack('<i', value)[0]
                    elif tag == 'MEDT':
                        school, _, flags, red, green, blue = struct.unpack_from('<ifiiii', value)
                        row.update(school=school, rgb=(red, green, blue), flags=flags)
                    elif tag in ('PTEX', 'CVFX', 'BVFX', 'HVFX', 'AVFX', 'CSND', 'BSND', 'HSND', 'ASND'):
                        row[tag] = zstring(value)
                if 'index' in row and 'school' in row:
                    mgef[row['index']] = row
                continue
            ident = next((zstring(v) for t, v in fields if t == 'NAME'), '').casefold()
            if kind in ('STAT', 'WEAP'):
                model = next((zstring(v) for t, v in fields if t == 'MODL'), '')
                if ident and model:
                    models[ident] = model
            elif kind == 'SOUN':
                sound = next((zstring(v) for t, v in fields if t == 'FNAM'), '')
                if ident and sound:
                    sounds[ident] = sound
            elif kind == 'GMST':
                value = next((v for t, v in fields if t == 'FLTV'), None)
                if ident and value is not None and len(value) == 4:
                    gmst[ident] = struct.unpack('<f', value)[0]
    return mgef, models, sounds, gmst


# ---- the meshes ----
def mesh_parts(raw, N, geometry=None):
    """(length, emitters, shapes) of one effect mesh. emitters: one dict per particle system (its controller's
    numbers, the texture its node names with whether that is the root's first texture (OpenMW's override rule),
    the alpha mode, gravity, the axis in the effect's space); shapes: (texture, root-first flag, radius) per
    textured triangle shape. GEOMETRY (a list): each textured triangle shape's vertices (in the effect's space),
    texture coordinates and triangles are appended to it (the shell baked into a sprite, shell_bytes)."""
    import numpy as np
    data = N.Data()
    data.read(io.BytesIO(raw))
    root = data.roots[0]
    first = next((p for p in getattr(root, 'properties', []) if p is not None and isinstance(p, N.NiTexturingProperty)),
                 None)
    length = 0.0
    for block in data.blocks:
        if isinstance(block, N.NiTimeController):
            length = max(length, float(block.stop_time))
    emitters, shapes = [], []

    def texture_of(node, inherited):
        tex, alpha = inherited
        for prop in getattr(node, 'properties', []):
            if prop is None:
                continue
            if isinstance(prop, N.NiTexturingProperty) and prop.has_base_texture and prop.base_texture.source:
                tex = (prop.base_texture.source.file_name.decode('cp1252'), prop is first and node is not root)
            if isinstance(prop, N.NiAlphaProperty):
                alpha = int(prop.flags)
        return tex, alpha

    def walk(node, parent, inherited):
        if not isinstance(node, N.NiAVObject):
            return
        world = np.array(node.get_transform().as_list()) @ parent
        state = texture_of(node, inherited)
        if isinstance(node, N.NiParticles):
            controller = node.controller
            while controller is not None:
                if isinstance(controller, N.NiParticleSystemController):
                    emitters.append(emitter(controller, state, world, N))
                controller = controller.next_controller
        elif isinstance(node, N.NiTriBasedGeom) and node.data is not None and state[0] is not None:
            verts = np.array([[v.x, v.y, v.z, 1.0] for v in node.data.vertices]) if node.data.vertices else np.zeros((0, 4))
            radius = float(np.sqrt(((verts @ world)[:, :3] ** 2).sum(1)).max()) if len(verts) else 0.0
            shapes.append((state[0][0], state[0][1], radius, state[1]))
            if geometry is not None and len(verts):
                uv = node.data.uv_sets[0] if getattr(node.data, 'uv_sets', None) else []
                tris = [tuple(t) for t in node.data.get_triangles()] if hasattr(node.data, 'get_triangles') else []
                if len(uv) == len(verts) and tris:
                    geometry.append({'texture': state[0][0], 'root_first': state[0][1], 'alpha': state[1],
                                     'verts': (verts @ world)[:, :3], 'uv': np.array([[t.u, t.v] for t in uv]),
                                     'tris': np.array(tris, dtype=int)})
        for child in getattr(node, 'children', []):
            if child is not None:
                walk(child, world, state)
    walk(root, np.eye(4), (None, None))
    return max(length, 0.0), emitters, shapes


def axis_spread(vertical_direction, vertical_angle, horizontal_direction, horizontal_angle):
    """The emission axis in the emitter's own space (z up) and the cone's tan(half angle); 50 = every direction.
    A NIF emitter aims vertical_direction down from +z, turned horizontal_direction about z, varied by the two
    angles; a full turn about z (or a vertical spread past 80 degrees) is taken as every direction."""
    v, h = float(vertical_direction), float(horizontal_direction)
    axis = (math.sin(v) * math.cos(h), math.sin(v) * math.sin(h), math.cos(v))
    if abs(float(vertical_angle)) > 1.4 or (abs(float(horizontal_angle)) > 1.5 and abs(math.sin(v)) > 0.2):
        return axis, 50.0
    half = max(abs(float(vertical_angle)), abs(float(horizontal_angle)) * abs(math.sin(v)))
    return axis, round(math.tan(min(half, 1.4)), 4)


def emitter(c, state, world, N):
    import numpy as np
    axis, spread = axis_spread(getattr(c, 'vertical_direction', 0), getattr(c, 'vertical_angle', 0),
                               getattr(c, 'horizontal_direction', 0), getattr(c, 'horizontal_angle', 0))
    axis = np.array(axis) @ world[:3, :3]
    norm = float(np.linalg.norm(axis))
    axis = (axis / norm) if norm > 1e-6 else np.array([0.0, 0.0, 1.0])
    gravity = 0
    modifier = c.particle_extra
    grow = fade = 0.0
    while modifier is not None:
        if isinstance(modifier, N.NiGravity) and float(modifier.force) > 0 and int(modifier.type) == 0 and \
                float(modifier.direction.z) < -0.5:
            gravity = 1
        if isinstance(modifier, N.NiParticleGrowFade):
            grow, fade = float(modifier.grow), float(modifier.fade)
        modifier = modifier.next_modifier
    jitter = getattr(c, 'start_random', None)
    return {'count': int(c.num_particles), 'size': float(c.size), 'life': float(c.lifetime),
            'life_rand': float(c.lifetime_random), 'speed': float(c.speed), 'speed_rand': float(c.speed_random),
            'axis': [round(float(x), 4) for x in axis], 'spread': spread, 'gravity': gravity,
            'start': float(c.emit_start_time), 'stop': float(c.emit_stop_time),
            'jitter': [abs(float(getattr(jitter, k, 0))) if jitter is not None else 0.0 for k in 'xyz'],
            'texture': state[0][0] if state[0] else None, 'root_texture': bool(state[0] and state[0][1]),
            'alpha': state[1], 'grow': grow, 'fade': fade}


def effective_texture(texture, root_first, particle_texture):
    """OpenMW's rule: the effect's particle texture replaces the texture only where the mesh's root names it first."""
    return particle_texture if root_first and particle_texture else texture


def additive(alpha_flags):
    """NiAlphaProperty: blending on, destination factor ONE = an additive glow (flags 13); else see-through."""
    return alpha_flags is not None and alpha_flags & 1 and ((alpha_flags >> 5) & 15) == 0


def caps(counts, cap):
    """Each emitter's share of the phase's cap, by its own count (at least 1 when it had any)."""
    total = sum(counts)
    if total <= 0:
        return [0 for _ in counts]
    scale = min(1.0, cap / total)
    return [max(1, int(round(n * scale))) if n > 0 else 0 for n in counts]


# ---- textures to sprites and colours ----
def boosted(rgb):
    """A glow's colour at full strength: an additive texel adds its colour onto the scene, so its hue counts
    more than its darkness (the dither carries the strength)."""
    import numpy as np
    rgb = np.asarray(rgb, dtype=float)
    peak = rgb.max(axis=-1, keepdims=True)
    return np.clip(rgb * np.minimum(3.0, 255.0 / np.maximum(peak, 1.0)), 0, 255)


def weights(rgba, glow):
    """Per texel strength 0..1: alpha for see-through textures; alpha x brightness for additive glows."""
    import numpy as np
    rgba = np.asarray(rgba, dtype=float)
    alpha = rgba[..., 3] / 255.0
    if not glow:
        return alpha
    luma = rgba[..., :3].max(axis=-1)
    return alpha * luma / max(1.0, float(luma.max()))


def ramp(rgba, glow=True):
    """RAMP colours of a texture, brightest first: the strongest texels in RAMP bands of falling strength."""
    import numpy as np
    rgba = np.asarray(rgba, dtype=float).reshape(-1, 4)
    w = weights(rgba, glow)
    keep = w > 0.08
    if not keep.any():
        keep = w >= w.max()
    colours = boosted(rgba[keep, :3]) if glow else rgba[keep, :3]
    order = np.argsort(-w[keep], kind='stable')
    bands = np.array_split(order, RAMP)
    out = []
    for band in bands:
        chosen = band if len(band) else order[:1]
        out.append([int(round(x)) for x in colours[chosen].mean(0)])
    return out


def nearest(rgb, palette):
    """Palette indices (0..254; 255 is the sprites' see-through) of an array of RGB colours."""
    import numpy as np
    pal = np.frombuffer(bytes(palette), np.uint8).reshape(256, 3)[:255].astype(float)
    flat = np.asarray(rgb, dtype=float).reshape(-1, 3)
    return ((flat[:, None, :] - pal[None, :, :]) ** 2).sum(2).argmin(1).astype(np.uint8)


def sprite_bytes(rgba, palette, glow):
    """A Quake sprite (IDSP version 1, facing the view, SPR_VP_PARALLEL like the tree sprites), SPRITE x SPRITE,
    one single frame per FADES strength: a texel shows when its strength beats the ordered dither."""
    import numpy as np
    from PIL import Image
    image = Image.fromarray(np.asarray(rgba, dtype=np.uint8), 'RGBA').resize((SPRITE, SPRITE), Image.Resampling.LANCZOS)
    pixels = np.asarray(image, dtype=float)
    w = weights(pixels, glow)
    colours = boosted(pixels[..., :3]) if glow else pixels[..., :3]
    index = nearest(colours, palette).reshape(SPRITE, SPRITE)
    threshold = np.array([[(BAYER[y % 4][x % 4] + 0.5) / 16 for x in range(SPRITE)] for y in range(SPRITE)])
    out = bytearray(struct.pack('<4siifiiifi', b'IDSP', 1, 2, SPRITE * 0.7072, SPRITE, SPRITE, len(FADES), 0.0, 0))
    for strength in FADES:
        frame = np.where(np.minimum(1.0, w * 1.4) * strength > threshold, index, 255).astype(np.uint8)
        out += struct.pack('<5i', 0, -SPRITE // 2, SPRITE // 2, SPRITE, SPRITE) + frame.tobytes()
    return bytes(out)


def bubble_bytes(rgba, rgb, palette, shell=None):
    """A Quake sprite of a translucent sphere (four fade frames like sprite_bytes): the shell texture wrapped around
    it (longitude by angle, latitude by radius) in the effect's colour, strongest at the rim where a see-through
    shell is seen edge-on (its path through the shell grows as 1 / cos), see-through in the middle. SHELL: the
    effect's hit model baked by shell_image, laid over it."""
    import numpy as np
    from PIL import Image
    tex = np.asarray(Image.fromarray(np.asarray(rgba, dtype=np.uint8), 'RGBA').resize((64, 64), Image.Resampling.LANCZOS),
                     dtype=float)
    y, x = np.mgrid[0:SPRITE, 0:SPRITE]
    dx, dy = (x + 0.5 - SPRITE / 2) / (SPRITE / 2), (y + 0.5 - SPRITE / 2) / (SPRITE / 2)
    r = np.sqrt(dx * dx + dy * dy)
    inside = r < 1.0
    depth = np.sqrt(np.clip(1 - r * r, 0.0, 1.0))
    path = 1.0 / np.maximum(depth, 0.18)                       # 1 in the middle, about 5.5 at the rim
    u = ((np.arctan2(dy, dx) / (2 * np.pi)) % 1.0 * 63).astype(int)
    v = np.clip(np.arcsin(np.clip(r, 0, 1)) / (np.pi / 2) * 63, 0, 63).astype(int)
    texel = tex[v, u]
    luma = texel[..., :3].max(axis=-1) / 255.0
    tint = np.asarray(boosted(np.asarray(rgb, dtype=float)), dtype=float)
    colour = np.clip(0.55 * tint + 0.45 * boosted(texel[..., :3]), 0, 255)
    w = np.where(inside, np.clip((path - 1) / 3.0 * (0.4 + 0.6 * luma) + 0.12 * luma, 0, 1), 0.0)
    if shell is not None:
        # the effect's own hit model baked from the front (shell_image) laid over the sphere: its pattern where it
        # is stronger, the sphere's translucent body elsewhere
        from PIL import Image as _I
        bc, bw = shell[0], shell[1]
        rgba = np.zeros(bw.shape + (4,))
        rgba[..., :3] = np.clip(0.6 * boosted(bc) + 0.4 * tint, 0, 255)
        rgba[..., 3] = bw * 255
        small = np.asarray(_I.fromarray(rgba.astype(np.uint8), 'RGBA').resize((SPRITE, SPRITE), _I.Resampling.BOX),
                           dtype=float)
        sw = np.clip(small[..., 3] / 255.0 * 1.6, 0, 1)
        w = w * 0.7
        take = sw > w
        colour = np.where(take[..., None], small[..., :3], colour)
        w = np.where(take, sw, w)
    index = nearest(colour, palette).reshape(SPRITE, SPRITE)
    threshold = np.array([[(BAYER[j % 4][i % 4] + 0.5) / 16 for i in range(SPRITE)] for j in range(SPRITE)])
    out = bytearray(struct.pack('<4siifiiifi', b'IDSP', 1, 2, SPRITE * 0.7072, SPRITE, SPRITE, len(FADES), 0.0, 0))
    for strength in FADES:
        frame = np.where(w * strength > threshold, index, 255).astype(np.uint8)
        out += struct.pack('<5i', 0, -SPRITE // 2, SPRITE // 2, SPRITE, SPRITE) + frame.tobytes()
    return bytes(out)


def shell_image(geometry, textures, grid=64):
    """The effect's own hit model seen from the front (x across, z up; orthographic), as a see-through glow: every
    triangle of its textured shapes rasterised with its texture, front and back layers added (a translucent shell
    is brightest where it is seen edge-on), additive textures by brightness x alpha, others by alpha. Returns (colour
    HxWx3, strength HxW 0..1, side in NIF units, centre z) or None when the model has no textured triangles."""
    import numpy as np
    pts = [g['verts'] for g in geometry if len(g['verts'])]
    if not pts:
        return None
    allv = np.concatenate(pts)
    zc = (allv[:, 2].min() + allv[:, 2].max()) / 2
    side = 2 * max(np.abs(allv[:, 0]).max(), np.abs(allv[:, 2] - zc).max()) * 1.08
    if not side > 0:
        return None
    acc = np.zeros((grid, grid, 3))
    weight = np.zeros((grid, grid))
    for g in geometry:
        tex = textures.get(g['texture'])
        if tex is None:
            continue
        tex = np.asarray(tex, dtype=float)
        th, tw = tex.shape[:2]
        glow = additive(g['alpha']) or g['alpha'] is None
        px = (g['verts'][:, 0] / side + 0.5) * grid
        py = (0.5 - (g['verts'][:, 2] - zc) / side) * grid
        for a, b, c in g['tris']:
            x0, x1, x2, y0, y1, y2 = px[a], px[b], px[c], py[a], py[b], py[c]
            area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
            if abs(area) < 1e-6:
                continue
            xs = np.arange(max(0, int(min(x0, x1, x2))), min(grid, int(max(x0, x1, x2)) + 1))
            ys = np.arange(max(0, int(min(y0, y1, y2))), min(grid, int(max(y0, y1, y2)) + 1))
            if not len(xs) or not len(ys):
                continue
            gx, gy = np.meshgrid(xs + 0.5, ys + 0.5)
            w1 = ((gx - x0) * (y2 - y0) - (x2 - x0) * (gy - y0)) / area
            w2 = ((x1 - x0) * (gy - y0) - (gx - x0) * (y1 - y0)) / area
            w0 = 1 - w1 - w2
            inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
            if not inside.any():
                continue
            uv = g['uv']
            u = (w0 * uv[a][0] + w1 * uv[b][0] + w2 * uv[c][0]) % 1.0
            v = (w0 * uv[a][1] + w1 * uv[b][1] + w2 * uv[c][1]) % 1.0
            texel = tex[(v * (th - 1)).astype(int), (u * (tw - 1)).astype(int)]
            alpha = texel[..., 3] / 255.0
            strength = alpha * texel[..., :3].max(axis=-1) / 255.0 if glow else alpha
            iy, ix = gy.astype(int)[inside], gx.astype(int)[inside]
            np.add.at(acc, (iy, ix), texel[..., :3][inside] * strength[inside][:, None])
            np.add.at(weight, (iy, ix), strength[inside])
    if not weight.max() > 0:
        return None
    colour = acc / np.maximum(weight, 1e-6)[..., None]
    strength = np.clip(weight / np.percentile(weight[weight > 0], 95), 0, 1)
    return colour, strength, float(side), float(zc)


def read_sprite(raw):
    """(frames, width, height) of a sprite sprite_bytes wrote; refuses anything else."""
    magic, version, kind, radius, width, height, frames, beam, sync = struct.unpack_from('<4siifiiifi', raw)
    if magic != b'IDSP' or version != 1 or kind != 2 or width != SPRITE or height != SPRITE or frames < 1:
        raise ValueError('Not a magic effect sprite')
    at = 36
    for _ in range(frames):
        kind, left, top, fw, fh = struct.unpack_from('<5i', raw, at)
        if kind != 0 or (fw, fh) != (width, height) or (left, top) != (-width // 2, height // 2):
            raise ValueError('Bad magic effect sprite frame')
        at += 20 + fw * fh
    if at != len(raw):
        raise ValueError('Magic effect sprite length')
    return frames, width, height


# ---- the table ----
def number(x):
    text = ('%.4f' % float(x)).rstrip('0').rstrip('.')
    return '0' if text in ('-0', '') else text


def emitter_line(name, phase, e):
    fields = [e['count'], e['size'], e['life'], e['life_rand'], e['speed'], e['speed_rand'], *e['axis'], e['spread'],
              e['gravity'], e['start'], e['stop'], *e['jitter']]
    ramp_values = [v for colour in e['ramp'] for v in colour]
    if len(e['ramp']) != RAMP:
        raise ValueError('An emitter needs %d ramp colours' % RAMP)
    return ' '.join(['em', name, phase, *(number(x) for x in fields), *(str(int(v)) for v in ramp_values)])


def table_text(bolt_speed, effects):
    """The engine's table (aw_magic_rules.c AW_MagicLine): effects = [{name, mgef, school, rgb, phases: {phase:
    {length, sprite, size, radius, sound, emitters: [...]}}}]."""
    lines = ['%s %s' % (FORMAT, number(bolt_speed)),
             '# fx NAME MGEF SCHOOL R G B FLAGS / ph NAME PHASE LENGTH SPRITE SIZE RADIUS SOUND / em NAME PHASE COUNT SIZE'
             ' LIFE LIFERAND SPEED SPEEDRAND AX AY AZ SPREAD GRAV START STOP JX JY JZ RAMP(8 x RGB)']
    for fx in effects:
        lines.append('fx %s %d %s %d %d %d %d' % (fx['name'], fx['mgef'], fx['school'], *fx['rgb'], fx.get('flags', 0)))
        for phase in PHASE_ORDER:
            ph = fx['phases'].get(phase)
            if ph is None:
                continue
            lines.append('ph %s %s %s %s %s %s %s' % (fx['name'], phase, number(ph['length']), ph['sprite'] or '-',
                                                     number(ph['size']), number(ph['radius']), ph['sound'] or '-'))
            for e in ph['emitters']:
                lines.append(emitter_line(fx['name'], phase, e))
    return '\n'.join(lines) + '\n'


def read_table(text):
    """The table as the engine reads it (the same checks in Python, for the tests and the image step's own check)."""
    lines = text.splitlines()
    head = lines[0].split()
    if len(head) != 2 or head[0] != FORMAT or not float(head[1]) > 0:
        raise ValueError('Not an %s table' % FORMAT)
    effects = {}
    for line in lines[1:]:
        tok = line.split()
        if not tok or tok[0].startswith('#'):
            continue
        if tok[0] == 'fx':
            if len(tok) not in (7, 8) or tok[1] in effects or tok[3] not in SCHOOLS or len(effects) >= 16:
                raise ValueError('Bad fx line: ' + line)
            effects[tok[1]] = {'phases': {}}
        elif tok[0] == 'ph':
            if len(tok) != 8 or tok[1] not in effects or tok[2] in effects[tok[1]]['phases']:
                raise ValueError('Bad ph line: ' + line)
            for path in (tok[4], tok[7]):
                if path != '-' and (len(path) >= 40 or '..' in path or path.startswith('/')):
                    raise ValueError('Bad path: ' + path)
            effects[tok[1]]['phases'][tok[2]] = {'length': float(tok[3]), 'sprite': tok[4], 'emitters': 0}
        elif tok[0] == 'em':
            if len(tok) != 19 + 3 * RAMP or tok[2] not in effects.get(tok[1], {}).get('phases', {}):
                raise ValueError('Bad em line: ' + line)
            ph = effects[tok[1]]['phases'][tok[2]]
            ph['emitters'] += 1
            if ph['emitters'] > EMITTERS:
                raise ValueError('Too many emitters: ' + line)
        else:
            raise ValueError('Unknown line: ' + line)
    if not effects or any('cast' not in fx['phases'] for fx in effects.values()):
        raise ValueError('Every effect needs its cast phase')
    return effects


# ---- the image step ----
def sound_file(ident, loop=False):
    """The image path of a converted sound; a looping copy (the bolt in flight) has its own name."""
    stem = ''.join(ch if ch.isalnum() else '_' for ch in ident.casefold())[:20 if loop else 24]
    return '%s/%s%s.wav' % (SOUND_DIR, 'loop_' if loop else '', stem)


def phase_sound(row, phase, school):
    """(sound record id, own) for a phase of a magic effect row: the effect's own CSND / BSND / HSND / ASND, else
    its school's "<school> cast|bolt|hit|area"; the failure is always the school's "Spell Failure <School>"
    (rules from OpenMW mwworld/store.cpp, mwmechanics/spellcasting.cpp, mwworld/projectilemanager.cpp)."""
    if phase == FAIL:
        return 'Spell Failure %s' % school.capitalize(), False
    field = dict(SOUND_FIELDS).get(phase)
    if field is None:
        return None, False
    own = row.get(field) or ''
    return (own, True) if own else ('%s %s' % (school, phase), False)


def sound_map(mgef, sound_files):
    """Every magic effect's sounds per phase (the build report's table): record id, whether the effect names it
    itself or takes its school's, and the game file it plays."""
    out = {}
    for index in sorted(mgef):
        row = mgef[index]
        if not 0 <= row['school'] < len(SCHOOLS):
            continue
        school = SCHOOLS[row['school']]
        phases = {}
        for phase in ('cast', 'bolt', 'hit', 'area', FAIL):
            ident, own = phase_sound(row, phase, school)
            phases[phase] = {'record': ident, 'own': own, 'file': sound_files.get(ident.casefold())}
        out[str(index)] = {'school': school, 'phases': phases}
    return out


def with_loop_point(raw):
    """A RIFF WAV with a cue chunk whose first cue point starts at sample 0: Quake's sound loader (snd_mem.c
    GetWavinfo) then loops it (snd_mix.c) until the sound is stopped, as its ambient sounds do."""
    if raw[:4] != b'RIFF' or raw[8:12] != b'WAVE':
        raise ValueError('Not a RIFF WAV')
    # count, then one cue point: id, position, chunk, chunk start, block start, sample offset
    cue = b'cue ' + struct.pack('<II', 28, 1) + struct.pack('<II4sIII', 1, 0, b'data', 0, 0, 0)
    body = raw[12:] + (b'\0' if len(raw) & 1 else b'') + cue   # chunks start on even offsets (RIFF padding)
    return b'RIFF' + struct.pack('<I', 4 + len(body)) + b'WAVE' + body


def loop_start(raw):
    """The loop start a Quake loader reads (its cue chunk's sample offset, 32 bytes into the chunk), or -1."""
    at = 12
    while at + 8 <= len(raw):
        tag, size = raw[at:at + 4], struct.unpack_from('<I', raw, at + 4)[0]
        if tag == b'cue ':
            return struct.unpack_from('<i', raw, at + 32)[0]
        at += 8 + size + (size & 1)
    return -1


def cloud_size(emitters):
    """The width (NIF units) of the largest emitter's particle cloud: its particles' size, the start box and how far
    a particle travels in its life."""
    return max(e['size'] + 2 * max(e['jitter']) + e['speed'] * e['life'] for e in emitters)


def sprite_size(phase, emitters, shapes):
    low, high = SPRITE_SIZE[phase]
    if phase == 'area' and shapes:
        size = max(r for _, _, r, _ in shapes) * SCALE * 1.2
    elif emitters:
        size = cloud_size(emitters) * SCALE
    elif shapes:
        size = max(r for _, _, r, _ in shapes) * SCALE * 2
    else:
        size = low
    return round(min(high, max(low, size)), 2)


def phase_sprite_texture(phase, emitters, shapes, particle_texture):
    """The phase's one picture: the bolt's model or the area's shell texture when it has one, else the emitter
    with the largest particles; the hand glow has none (its particles are the look)."""
    if phase == 'hand':
        return None
    if phase in ('bolt', 'area') and shapes:
        tex, root_first, _, alpha = max(shapes, key=lambda s: s[2])
        return effective_texture(tex, root_first, particle_texture), alpha
    if emitters:
        e = max(emitters, key=lambda x: x['size'])
        if e['texture']:
            return effective_texture(e['texture'], e['root_texture'], particle_texture), e['alpha']
    if shapes:
        tex, root_first, _, alpha = shapes[0]
        return effective_texture(tex, root_first, particle_texture), alpha
    return None


def prepare(data_files, id1):
    """Writes the table, sprites and sounds into ID1; returns the report (what each phase took, or why not)."""
    from mwad.audit import BSA
    from mwad.paths import child_ci, ensure_external
    from npc_geometry import Assets
    from prepare_scenery import nif_reader
    from prepare_combat import convert_wav
    data_files = ensure_external(Path(data_files), 'owned data')
    id1 = Path(id1)
    palette = (id1 / 'gfx' / 'palette.lmp').read_bytes()
    if len(palette) != 768:
        raise ValueError('The image palette must be 768 bytes')
    mgef, models, sound_files, gmst = read_records(data_files)
    assets = Assets(data_files, BSA(child_ci(data_files, 'Morrowind.bsa')))
    N = nif_reader()
    speed = gmst.get('ftargetspellmaxspeed', 1000.0) * SCALE
    meshes, sprites, sounds, effects = {}, {}, {}, []
    report = {'format': 'AmiWind magic effects 1', 'table': TABLE, 'bolt_speed': speed, 'effects': {}, 'sprites': {},
              'sounds': {}, 'sound_map': sound_map(mgef, sound_files), 'refused': []}

    def mesh(model):
        key = model.casefold().replace('\\', '/')
        if key not in meshes:
            try:
                meshes[key] = mesh_parts(assets.read('meshes/' + key), N)
            except Exception as error:  # noqa: BLE001 (a mesh the data lacks is left out with its reason)
                meshes[key] = error
        return meshes[key]

    def texture_rgba(name):
        return assets.texture(name)

    def sprite_for(texture, alpha):
        key = (texture.casefold(), bool(additive(alpha)))
        if key not in sprites:
            path = 'progs/awmx_%02d.spr' % len(sprites)
            raw = sprite_bytes(texture_rgba(texture), palette, glow=key[1])
            read_sprite(raw)
            (id1 / 'progs').mkdir(parents=True, exist_ok=True)
            (id1 / path).write_bytes(raw)
            sprites[key] = path
            report['sprites'][path] = {'texture': texture, 'additive': key[1], 'bytes': len(raw)}
        return sprites[key]

    def sound_for(ident, loop=False):
        if not ident:
            return None
        ident = ident.casefold()
        key = (ident, loop)
        if key not in sounds:
            sounds[key] = None
            source = sound_files.get(ident)
            if not source:
                report['refused'].append({'sound': ident, 'error': 'no sound record of that name'})
            else:
                path = sound_file(ident, loop)
                (id1 / SOUND_DIR).mkdir(parents=True, exist_ok=True)
                try:
                    seconds = convert_wav(assets.read('sound/' + source.replace('\\', '/').casefold()), id1 / path)
                    if loop:
                        (id1 / path).write_bytes(with_loop_point((id1 / path).read_bytes()))
                    sounds[key] = path[len('sound/'):]
                    report['sounds'][path] = {'record': ident, 'file': source, 'seconds': round(seconds, 3),
                                              'loop': loop}
                except Exception as error:  # noqa: BLE001
                    report['refused'].append({'sound': ident, 'error': str(error)})
        return sounds[key]

    for word, index in EFFECTS:
        row = mgef.get(index)
        if row is None:
            report['refused'].append({'effect': word, 'error': 'magic effect %d not in the data' % index})
            continue
        school = SCHOOLS[row['school']]
        particle_texture = row.get('PTEX') or None
        fx = {'name': word, 'mgef': index, 'school': school, 'rgb': [max(0, min(255, v)) for v in row['rgb']],
              'phases': {}}
        notes, pictures, phase_models = {}, {}, {}
        for phase, field, default, sound_field, sound_word in PHASES:
            visual = (row.get(field) or default) if field else default
            model = models.get(visual.casefold())
            parts = mesh(model) if model else None
            if not model or isinstance(parts, Exception):
                notes[phase] = 'no mesh for %s%s' % (visual, (': %s' % parts) if isinstance(parts, Exception) else '')
                continue
            length, emitters, shapes = parts
            phase_models[phase] = model
            chosen = sorted(emitters, key=lambda e: -e['count'])[:EMITTERS]
            shares = caps([e['count'] for e in chosen], CAPS[phase])
            out = []
            for e, share in zip(chosen, shares):
                if share <= 0 or not e['texture']:
                    continue
                tex = effective_texture(e['texture'], e['root_texture'], particle_texture)
                try:
                    colours = ramp(texture_rgba(tex), glow=bool(additive(e['alpha'])) or e['alpha'] is None)
                except Exception as error:  # noqa: BLE001
                    report['refused'].append({'effect': word, 'phase': phase, 'texture': tex, 'error': str(error)})
                    continue
                span = max(0.0, length)
                out.append({'count': share, 'size': round(e['size'] * SCALE, 3), 'life': max(0.05, min(10, e['life'])),
                            'life_rand': min(10, abs(e['life_rand'])), 'speed': round(abs(e['speed']) * SCALE, 3),
                            'speed_rand': round(abs(e['speed_rand']) * SCALE, 3), 'axis': e['axis'],
                            'spread': e['spread'], 'gravity': e['gravity'],
                            'start': round(max(0.0, min(e['start'], span or 10)), 3),
                            'stop': round(max(0.0, min(max(e['stop'], e['start']), span or 10)), 3),
                            'jitter': [round(min(512, j * SCALE), 3) for j in e['jitter']], 'ramp': colours,
                            'texture': tex})
            picture = phase_sprite_texture(phase, emitters, shapes, particle_texture)
            if picture:
                pictures[phase] = picture
            if not out and shapes and picture and phase != 'hand':
                # a mesh without particles (the area orbs, the frost and illusion bolts, the mysticism cast): its
                # largest shell becomes a burst of particles in the shell's own colours, out to the shell's size
                radius = max(r for _, _, r, _ in shapes) * SCALE
                span = max(0.3, min(3.0, length or 1.0))
                try:
                    colours = ramp(texture_rgba(picture[0]), glow=bool(additive(picture[1])) or picture[1] is None)
                    trail = phase == 'bolt'
                    out.append({'count': 12 if trail else CAPS[phase], 'size': round(min(256, radius * 0.5), 3),
                                'life': round(0.3 if trail else span * 0.8, 3), 'life_rand': round(0.1 if trail else span * 0.2, 3),
                                'speed': round(2.0 if trail else min(2000, radius / span), 3),
                                'speed_rand': round(1.0 if trail else radius / span * 0.3, 3), 'axis': [0, 0, 1],
                                'spread': 50.0, 'gravity': 0, 'start': 0.0, 'stop': 0.0 if not trail else round(span, 3),
                                'jitter': [round(min(512, radius * 0.2), 3)] * 3, 'ramp': colours,
                                'texture': picture[0], 'from_shape': True})
                except Exception as error:  # noqa: BLE001
                    report['refused'].append({'effect': word, 'phase': phase, 'texture': picture[0], 'error': str(error)})
            sprite = None
            if picture:
                try:
                    sprite = sprite_for(*picture)
                except Exception as error:  # noqa: BLE001
                    report['refused'].append({'effect': word, 'phase': phase, 'texture': picture[0], 'error': str(error)})
            sound = sound_for(phase_sound(row, phase, school)[0], loop=phase == 'bolt') if sound_field else None
            radius = max((r for _, _, r, _ in shapes), default=0.0) * SCALE if phase == 'area' else 0.0
            fx['phases'][phase] = {'length': round(max(0.3, min(10.0, length or 1.0)), 3), 'sprite': sprite,
                                   'size': sprite_size(phase, emitters, shapes), 'radius': round(min(2048, radius), 2),
                                   'sound': sound, 'emitters': out}
            notes[phase] = {'visual': visual, 'mesh': model, 'emitters': len(emitters), 'kept': len(out),
                            'particles': sum(e['count'] for e in out), 'sprite': sprite,
                            'sprite_texture': picture[0] if picture else None, 'sound': sound}
        if 'cast' not in fx['phases']:
            report['refused'].append({'effect': word, 'error': 'no cast mesh: %s' % notes.get('cast')})
            continue
        # the bubble: the effect's own hit model baked from the front into a see-through sprite (the shell that wraps
        # a character the spell holds on), its SIZE the model's width in map units for a standard character (the
        # engine scales it to the actor); without a textured hit model the sphere of its hit texture (SIZE 0)
        fx['flags'] = int(row.get('flags', 0))
        source = (pictures.get('hit') or pictures.get('cast') or ((particle_texture, 13) if particle_texture else None))
        if source or phase_models.get('hit'):
            try:
                key = ('bubble', word)
                path = 'progs/awmx_%02d.spr' % len(sprites)
                image, size, how = None, 0, 'sphere'
                if phase_models.get('hit'):
                    geometry = []
                    mesh_parts(assets.read('meshes/' + phase_models['hit'].casefold().replace('\\', '/')), N, geometry)
                    textures = {g['texture']: texture_rgba(effective_texture(g['texture'], g['root_first'],
                                                                             particle_texture)) for g in geometry}
                    image = shell_image(geometry, textures)
                if image is not None:
                    size, how = round(min(512, image[2] * SCALE), 2), 'hit model on sphere'
                import numpy as np
                body = texture_rgba(source[0]) if source else np.zeros((8, 8, 4), np.uint8)
                raw = bubble_bytes(body, fx['rgb'], palette, shell=image)
                read_sprite(raw)
                (id1 / 'progs').mkdir(parents=True, exist_ok=True)
                (id1 / path).write_bytes(raw)
                sprites[key] = path
                report['sprites'][path] = {'texture': source[0] if source else None, 'bubble': word, 'from': how,
                                           'bytes': len(raw)}
                fx['phases'][BUBBLE] = {'length': BUBBLE_LENGTH, 'sprite': path, 'size': size, 'radius': 0,
                                        'sound': None, 'emitters': []}
                notes[BUBBLE] = {'sprite': path, 'from': how, 'size': size, 'hit_model': phase_models.get('hit')}
            except Exception as error:  # noqa: BLE001
                report['refused'].append({'effect': word, 'phase': BUBBLE, 'error': str(error)})
        fail = sound_for(phase_sound(row, FAIL, school)[0])
        if fail:
            fx['phases'][FAIL] = {'length': FAIL_LENGTH, 'sprite': None, 'size': 0, 'radius': 0, 'sound': fail,
                                  'emitters': []}
            notes[FAIL] = {'sound': fail}
        effects.append(fx)
        report['effects'][word] = {'mgef': index, 'school': school, 'phases': notes}
    if not effects:
        raise ValueError('No magic effect could be converted')
    text = table_text(speed, effects)
    read_table(text)
    (id1 / 'gfx').mkdir(parents=True, exist_ok=True)
    (id1 / TABLE).write_text(text, encoding='utf-8', newline='\n')
    report['table_bytes'] = len(text)
    report['sprite_bytes'] = sum(s['bytes'] for s in report['sprites'].values())
    return report


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--data-files', required=True)
    parser.add_argument('--id1', required=True, help='an image id1 folder holding gfx/palette.lmp')
    args = parser.parse_args(argv)
    print(json.dumps(prepare(args.data_files, args.id1), indent=2, default=str))


if __name__ == '__main__':
    main()
