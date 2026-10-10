#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Compare two NPC galleries model by model (docs/MODULAR_NPCS.md).

Typical use: the gallery built with --npc-models parts against the one built
whole. Every model key of the reference catalogue is checked: identical bytes,
or the measured differences (faces, vertex grid steps, skin texels, header
scale/origin, bounding box). Optionally writes an A/B preview sheet of the most
different models (flat front views; private evidence, never repository content).
"""
import argparse
import json
import struct
import sys
from pathlib import Path

import numpy as np


def parse(raw):
    h = struct.unpack_from('<4si3f3ff3f8if', raw)
    if h[0] != b'IDPO' or h[1] != 6:
        raise ValueError('Not an alias model')
    sw, sh, nv, nt, nf = h[13], h[14], h[15], h[16], h[17]
    at = 88
    skin = np.frombuffer(raw, np.uint8, sw * sh, at).reshape(sh, sw); at += sw * sh
    st = np.frombuffer(raw, '<i4', nv * 3, at).reshape(nv, 3); at += nv * 12
    tri = np.frombuffer(raw, '<i4', nt * 4, at).reshape(nt, 4); at += nt * 16
    frames = []
    for _ in range(nf):
        at += 28
        frames.append(np.frombuffer(raw, np.uint8, nv * 4, at).reshape(nv, 4)[:, :3]); at += nv * 4
    scale = np.array(h[2:5]); origin = np.array(h[5:8]); frames = np.array(frames)
    return {'skin': skin, 'st': st, 'tri': tri, 'frames': frames, 'scale': scale, 'origin': origin,
            'faces': nt, 'vertices': nv, 'world': frames.astype(float) * scale + origin}


def compare(a, b):
    """Differences of model a against reference b (both raw MDL bytes)."""
    if a == b:
        return {'identical': True}
    A, B = parse(a), parse(b)
    out = {'identical': False, 'faces': A['faces'] - B['faces'], 'bytes': len(a) - len(b),
           'scale_rel': float(np.max(np.abs(A['scale'] - B['scale']) / np.maximum(np.abs(B['scale']), 1e-9))),
           'origin': float(np.max(np.abs(A['origin'] - B['origin']))),
           'bounds': float(max(np.abs(A['world'].min((0, 1)) - B['world'].min((0, 1))).max(),
                               np.abs(A['world'].max((0, 1)) - B['world'].max((0, 1))).max()))}
    if A['faces'] == B['faces'] and A['skin'].shape == B['skin'].shape:
        d = np.abs(A['frames'].astype(int) - B['frames'].astype(int)).max(axis=(0, 2))
        out.update(same_topology=bool((A['tri'] == B['tri']).all() and (A['st'] == B['st']).all()),
                   vertices_moved=int((d > 0).sum()), vertices_moved_over_1=int((d > 1).sum()), vertex_steps_max=int(d.max()),
                   skin_texels=int((A['skin'] != B['skin']).sum()), skin_share=round(float((A['skin'] != B['skin']).mean()), 5))
    return out


def preview(model, palette, height=160):
    """Flat front view: faces filled with their tile's mean colour (not an in-game frame)."""
    from PIL import Image, ImageDraw
    pal = np.array(list(palette)).reshape(256, 3)
    p = model['world'][0]; lo = p.min(0); hi = p.max(0); s = (height - 8) / max(hi[2] - lo[2], 1e-3)
    image = Image.new('RGB', (height // 2 + 16, height), (40, 40, 48)); draw = ImageDraw.Draw(image)
    tris = p[model['tri'][:, 1:]]; cx = (lo[1] + hi[1]) / 2
    for fi in np.argsort(tris[:, :, 0].mean(1))[::-1]:
        u, v = model['st'][model['tri'][fi, 1], 1:]
        colour = pal[model['skin'][v:v + 8, u:u + 8]].reshape(-1, 3).mean(0)
        draw.polygon([((x[1] - cx) * s + image.width / 2, height - 4 - (x[2] - lo[2]) * s) for x in tris[fi]],
                     fill=tuple(int(c) for c in colour))
    return image


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate', type=Path, required=True, help='Gallery output folder (with gallery/catalog.txt)')
    p.add_argument('--reference', type=Path, required=True, help='Reference gallery output folder')
    p.add_argument('--out', type=Path, required=True, help='JSON report')
    p.add_argument('--sheet', type=Path, help='Optional A/B PNG of the most different models (private)')
    p.add_argument('--sheet-count', type=int, default=40)
    a = p.parse_args()
    audit = json.loads((a.reference / 'gallery-audit.json').read_text())
    keys = sorted(k for k, r in audit['models'].items() if r.get('status') == 'ready')
    kinds = {k: 'NPC_' for e in audit['entries'] if e['kind'] == 'NPC_' for k in e['models']}
    rows = {}; missing = []
    for key in keys:
        ref = a.reference / 'gallery' / (key + '.mdl'); cand = a.candidate / 'gallery' / (key + '.mdl')
        if not cand.is_file():
            missing.append(key); continue
        rows[key] = compare(cand.read_bytes(), ref.read_bytes())
    def stat(name, pick=lambda r: True):
        values = [r[name] for r in rows.values() if name in r and pick(r)]
        return {'max': max(values, default=0), 'mean': round(float(np.mean(values)), 6) if values else 0,
                'nonzero': sum(1 for v in values if v)}
    different = [r for r in rows.values() if not r['identical']]
    summary = {'format': 'AmiWind gallery comparison 1', 'reference_models': len(keys), 'compared': len(rows),
               'missing': missing, 'identical': len(rows) - len(different), 'different': len(different),
               'humanoid_identical': sum(1 for k, r in rows.items() if r['identical'] and kinds.get(k)),
               'same_faces': sum(1 for r in different if r['faces'] == 0),
               'same_topology': sum(1 for r in different if r.get('same_topology')),
               'faces_delta': {'min': min((r['faces'] for r in different), default=0),
                               'max': max((r['faces'] for r in different), default=0),
                               'histogram': {}},
               'scale_rel': stat('scale_rel'), 'origin': stat('origin'), 'bounds': stat('bounds'),
               'vertices_moved': stat('vertices_moved'), 'vertices_moved_over_1': stat('vertices_moved_over_1'),
               'vertex_steps_max': stat('vertex_steps_max'), 'skin_share': stat('skin_share')}
    for r in different:
        bucket = str(int(np.clip(r['faces'], -20, 20)))
        summary['faces_delta']['histogram'][bucket] = summary['faces_delta']['histogram'].get(bucket, 0) + 1
    a.out.write_text(json.dumps({'summary': summary, 'models': rows}, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(summary, indent=1))
    if a.sheet:
        from PIL import Image, ImageDraw
        palette = (a.reference / 'gfx/palette.lmp').read_bytes()
        worst = sorted(((abs(r['faces']), r.get('vertices_moved_over_1', 0), r.get('skin_share', 0), k)
                        for k, r in rows.items() if not r['identical']), reverse=True)[:a.sheet_count]
        tiles = []
        for _, _, _, key in worst:
            A = parse((a.candidate / 'gallery' / (key + '.mdl')).read_bytes())
            B = parse((a.reference / 'gallery' / (key + '.mdl')).read_bytes())
            left, right = preview(B, palette), preview(A, palette)
            tile = Image.new('RGB', (left.width * 2, left.height + 12), (16, 16, 20))
            tile.paste(left, (0, 12)); tile.paste(right, (left.width, 12))
            ImageDraw.Draw(tile).text((2, 0), f'{key[:9]} {rows[key]["faces"]:+d}f', fill=(230, 230, 230))
            tiles.append(tile)
        if tiles:
            cols = 8; w, h = tiles[0].size
            sheet = Image.new('RGB', (cols * w, ((len(tiles) + cols - 1) // cols) * h))
            for i, t in enumerate(tiles):
                sheet.paste(t, (i % cols * w, i // cols * h))
            sheet.resize((sheet.width * 2, sheet.height * 2), Image.Resampling.NEAREST).save(a.sheet)
    return 1 if missing else 0


if __name__ == '__main__':
    sys.exit(main())
