# SPDX-License-Identifier: GPL-3.0-only
"""Bounded shared harvest alias conversion from original source packets.

Use source surfaces and the existing MDL serializer. Split at repeat-UV tile
boundaries rather than clamp the original texture coordinates. All models use
the same 32-pixel material resolution as the retained brush experiment.
"""
import hashlib
import math
import struct
import numpy as np
from PIL import Image
from mwad.scene import read_asset, unpack_geometry
from npc_geometry import animated_mdl


def clip(poly, axis, bound, greater):
    result = []
    for a, b in zip(poly, poly[1:] + poly[:1]):
        da, db = a[3 + axis] - bound, b[3 + axis] - bound
        ina = da >= -1e-10 if greater else da <= 1e-10
        inb = db >= -1e-10 if greater else db <= 1e-10
        if ina:
            result.append(a)
        if ina != inb:
            q = a + (b - a) * (da / (da - db))
            q[3 + axis] = bound
            result.append(q)
    return result


def split_repeats(vertices, faces):
    """Return material-indexed triangles; preserve physical surface area.

    Numerical clipping may create collinear points. Degenerate triangles are
    discarded by area, but original nondegenerate triangles must retain area.
    The bounded tiling check refuses pathological repeat coordinates.
    """
    result, original_areas = [], []
    for face_number, face in enumerate(faces):
        triangle = np.array(vertices[face[:3], :5], dtype=float)
        source_area = np.linalg.norm(np.cross(triangle[1, :3] - triangle[0, :3],
                                              triangle[2, :3] - triangle[0, :3])) / 2
        if source_area <= 1e-12:
            raise ValueError('Degenerate original surface')
        lo = np.floor(triangle[:, 3:5].min(0)).astype(int)
        hi = np.maximum(lo, np.ceil(triangle[:, 3:5].max(0)).astype(int) - 1)
        if np.any(hi - lo > 16):
            raise ValueError('UV repeat span exceeds bounded converter')
        area = 0.
        for u in range(lo[0], hi[0] + 1):
            for v in range(lo[1], hi[1] + 1):
                poly = list(triangle.copy())
                for axis, lower in ((0, u), (1, v)):
                    poly = clip(poly, axis, lower, True)
                    poly = clip(poly, axis, lower + 1, False)
                for k in range(1, len(poly) - 1):
                    tri = np.array([poly[0], poly[k], poly[k + 1]])
                    part = np.linalg.norm(np.cross(tri[1, :3] - tri[0, :3],
                                                   tri[2, :3] - tri[0, :3])) / 2
                    if part <= source_area * 1e-12:
                        continue
                    area += part
                    tri[:, 3:5] -= (u, v)
                    result.append((tri, int(face[3]), face_number))
        if not math.isclose(source_area, area, rel_tol=1e-8, abs_tol=1e-8):
            raise ValueError('UV splitting changed physical surface coverage')
        original_areas.append(source_area)
    return result, original_areas


def texture_tiles(archive, index, model, palette, size=32):
    pal = Image.new('P', (1, 1)); pal.putpalette(palette)
    count = len(model['materials']); stride = size + 1
    if not 1 <= count <= 3 or size != 32 or len(palette) != 768:
        raise ValueError('Shared alias requires 1..3 opaque materials at 32 pixels')
    width = (count * stride + 3) & ~3
    skin = Image.new('P', (width, stride)); skin.putpalette(palette)
    hashes = []
    for i, material in enumerate(model['materials']):
        if material.get('alpha', 1) != 1:
            raise ValueError('Translucent source cannot use this opaque alias representation')
        texture = index['textures'][material['texture_index']]
        raw = read_asset(archive, texture)
        if len(raw) < 8:
            raise ValueError('Truncated texture packet')
        magic, w, h = struct.unpack_from('>4sHH', raw)
        if magic != b'MWT1' or not w or not h or len(raw) != 8 + 4*w*h:
            raise ValueError('Invalid texture packet')
        pixels = np.frombuffer(raw[8:], np.uint8).reshape(h, w, 4)
        if np.any(pixels[:, :, 3] != 255):
            raise ValueError('Texture alpha needs a separate representation')
        diffuse = np.asarray(material['diffuse'], dtype=float)
        if diffuse.shape != (3,) or not np.isfinite(diffuse).all():
            raise ValueError('Invalid material diffuse colour')
        rgb = pixels[:, :, :3].astype(float) * diffuse
        im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).resize((size, size))
        im = im.quantize(palette=pal, dither=Image.Dither.NONE)
        # UVs are clipped into [0,1] and the renderer samples integer texels.
        # Only the high endpoint needs a periodic gutter (u/v==1 maps to the
        # first texel); no bilinear taps can reach a low-side gutter.
        padded = np.pad(np.array(im), ((0, 1), (0, 1)), mode='wrap')
        tile = Image.fromarray(padded, mode='P'); tile.putpalette(palette)
        skin.paste(tile, (i * stride, 0))
        hashes.append({'texture': material['texture_index'], 'source_sha256': hashlib.sha256(raw).hexdigest(),
                       'target_sha256': hashlib.sha256(im.tobytes()).hexdigest()})
    return skin, hashes


def convert(archive, index, model, palette):
    original, faces, _ = unpack_geometry(read_asset(archive, model))
    original = np.asarray(original, dtype=float); faces = np.asarray(faces, dtype=int)
    triangles, areas = split_repeats(original, faces)
    skin, textures = texture_tiles(archive, index, model, palette)
    vertices, uv, output_faces, keys = [], [], [], {}
    stride = 33
    for triangle, material, _ in triangles:
        if not 0 <= material < len(model['materials']):
            raise ValueError('Invalid source material index')
        face = []
        for point in triangle:
            # Position remains in the shared model's source coordinate system,
            # scaled to game units once. Source placement scale stays separate.
            p = point[:3] * .25
            tex = np.clip(point[3:5], 0, 1) * 32 + (material * stride, 0)
            key = tuple(np.round(np.concatenate((p, tex)), 8))
            if key not in keys:
                keys[key] = len(vertices); vertices.append(p); uv.append(tex)
            face.append(keys[key])
        # Source NIF faces and the existing software alias draw convention have
        # opposite winding (same conversion as npc_geometry.bake).
        output_faces.append([face[0], face[2], face[1]])
    vertices = np.array(vertices); uv = np.array(uv); output_faces = np.array(output_faces)
    raw = animated_mdl(vertices[None, :, :], output_faces, uv, skin)
    lo = vertices.min(0); scale = np.maximum((vertices.max(0) - lo) / 255, .0001)
    decoded = np.rint((vertices - lo) / scale) * scale + lo
    quantized_seams = {}
    for p, q in zip(vertices, decoded):
        key = tuple(np.round(p, 7))
        if key in quantized_seams and not np.array_equal(quantized_seams[key], q):
            raise AssertionError('Material seams quantized to distinct positions')
        quantized_seams[key] = q
    return raw, dict(source_triangles=len(faces), source_vertices=len(original),
                     triangles=len(output_faces), vertices=len(vertices),
                     source_surface_area=sum(areas), repeat_split_surface_coverage='exact within 1e-8 relative tolerance',
                     materials=len(model['materials']), textures=textures, skin=list(skin.size),
                     model_local_max_position_error=float(np.max(np.abs(vertices - decoded))),
                     model_local_position_error_bound=(scale / 2).tolist(),
                     uv_error='MDL integer texel coordinates: less than one texel per axis',
                     seam_positions='same shared quantizer across all materials',
                     pose='Original rotation and placement scale not baked into each asset',
                     native_appearance='not tested; alias lighting differs from brush surface lighting')


def alias_cost(raw, sizes):
    """Same actual loader allocations as guard_torch_heap, bounded to 1 frame."""
    skins, w, h, nv, nt, nf = struct.unpack_from('<6i', raw, 48)
    if raw[:4] != b'IDPO' or struct.unpack_from('<i', raw, 4)[0] != 6 or skins != 1 or nf != 1:
        raise ValueError('Expected one-frame alias')
    frame = 88 + w * h + nv * 12 + nt * 16
    if len(raw) != frame + 28 + nv * 4 or struct.unpack_from('<i', raw, frame)[0]:
        raise ValueError('Invalid alias allocation envelope')
    align = lambda n: (n + 15) & ~15
    alloc = lambda n: sizes['hunk'] + align(n)
    header = alloc(sizes['aliashdr'] + sizes['mdl'] + nv * sizes['stvert'] + nt * sizes['mtriangle'])
    decoded = header + alloc(sizes['maliasskindesc']) + alloc(w * h) + alloc(nv * sizes['trivertx'])
    return dict(file_bytes=len(raw), vertices=nv, triangles=nt, frames=nf,
                decoded_hunk_bytes=decoded, cache_bytes=align(decoded + sizes['cache_system']),
                source_file_hunk_fallback_bytes=alloc(len(raw) + 1), external_malloc_peak_bytes=len(raw) + decoded)
