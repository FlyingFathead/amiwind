# SPDX-License-Identifier: GPL-3.0-only
"""A preview of the shared animation tables (docs/MODULAR_NPCS.md, "Getting NPC movement right"): the common
humanoid and the beast skeleton's stick-figure tables (skeletal_actor.stick_table), posed as the engine poses them
(from the stored keys), drawn as bones from the side and the front, group after group, at the table's rate.

With --npc, one character of the game (its head, hair, clothes and skin, reduced and atlased as the game's resident
bake does it) as a skeletal model on the same table, posed as the engine poses it (skeletal_actor.engine_pose: the
model's own byte vertices), each face drawn in its skin colour with a simple light: what the shared table does to a
real character.

Reads the game's own files from --data-files (Morrowind.bsa, Morrowind.esm); writes an animated GIF and a contact
sheet of each group's middle frame (bones), or a GIF of the character (--npc). The pictures are made from the
game's data: keep them private.

    python3 tools/skeleton_preview.py --data-files DIR --out DIR [--groups idle walkforward ...]
    python3 tools/skeleton_preview.py --data-files DIR --out DIR --npc "balyn omavel" --palette gfx/palette.lmp
"""
import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]

GROUPS = ('idle', 'walkforward', 'runforward', 'sneakforward', 'jump', 'weapononehand', 'weapontwohand', 'handtohand',
          'spellcast', 'knockdown', 'deathone')
SKELETONS = (('meshes/base_anim.nif', 'common'), ('meshes/base_animkna.nif', 'beast'))
ATTACHMENTS = ('weapon bone', 'shield bone')
W, H, PANEL = 960, 540, 240


def project(points, view):
    """Morrowind's x right, y forward, z up: the side view looks along x, the front view along y."""
    if view == 'side':
        return np.column_stack((points[:, 1], -points[:, 2]))
    return np.column_stack((points[:, 0], -points[:, 2]))


def span(table, group):
    """A group's frames; a phased group in two places (skeletal_actor.group_spans) shows its second, the casts."""
    return table['groups'].get(group + '_2', table['groups'][group])


def render(shown, groups, rate):
    """[(label, table, report)] -> frames (PIL images) and (first frame, length) per group."""
    from PIL import Image, ImageDraw
    import skeletal_actor as S
    frames, starts = [], []
    for g in groups:
        length = max(last - first + 1 for first, last in (span(t, g) for _, t, _ in shown))
        starts.append((len(frames), length))
        for i in range(length):
            img = Image.new('RGB', (W, H), (24, 24, 32))
            d = ImageDraw.Draw(img)
            d.text((10, 8), 'AmiWind shared skeleton tables (%g fps): %s  frame %d' % (rate, g, i),
                   fill=(230, 230, 230))
            d.text((10, H - 22), 'thin blue: weapon and shield attachment points', fill=(110, 170, 255))
            for col, (label, t, report) in enumerate(shown):
                first, last = span(t, g)
                world = S.table_world(t, min(first + i, last))
                pts = np.array([m[3, :3] for m in world])
                root = report['bone_names'].index('bip01')
                pts -= [pts[root][0], pts[root][1], 0]
                for v, view in enumerate(('side', 'front')):
                    ox, oy = 20 + (col * 2 + v) * PANEL + PANEL // 2, H - 60
                    xy = project(pts, view) * 3.2 + [ox, oy]
                    d.text((ox - 60, 30), '%s, %s' % (label, view), fill=(170, 200, 255))
                    d.line([(ox - 100, oy), (ox + 100, oy)], fill=(70, 70, 80))
                    for b, parent in enumerate(t['parents']):
                        if parent >= 0:
                            attach = report['bone_names'][b] in ATTACHMENTS
                            d.line([tuple(xy[b]), tuple(xy[parent])],
                                   fill=(110, 170, 255) if attach else (255, 210, 120), width=1 if attach else 3)
                    for p in xy:
                        d.ellipse([p[0] - 2, p[1] - 2, p[0] + 2, p[1] + 2], fill=(255, 120, 90))
            frames.append(img)
    return frames, starts


def contact_sheet(frames, starts):
    from PIL import Image
    rows = (len(starts) + 1) // 2
    sheet = Image.new('RGB', (W, rows * H // 2), (0, 0, 0))
    for k, (start, length) in enumerate(starts):
        sheet.paste(frames[start + length // 2].resize((W // 2, H // 2)), ((k % 2) * W // 2, (k // 2) * H // 2))
    return sheet


def model_faces(model, palette):
    """A skeletal model's triangles (nt, 3 vertex indices) and each face's colour: its skin texel at the face's
    middle texture coordinate (the back half of the skin for a back face on the seam, as Quake's alias models)."""
    import struct
    import skeletal_actor as S
    _, w, h, nv, nt, _ = struct.unpack_from('<6i', model, 48)
    at = S.MDL_HEAD + 4
    skin = np.frombuffer(model, np.uint8, w * h, at).reshape(h, w)
    at += w * h
    st = np.frombuffer(model, '<i4', nv * 3, at).reshape(nv, 3)
    at += nv * 12
    tris = np.frombuffer(model, '<i4', nt * 4, at).reshape(nt, 4)
    pal = np.frombuffer(palette, np.uint8).reshape(256, 3).astype(float)
    colour = np.zeros((nt, 3))
    for i, (front, *ids) in enumerate(tris):
        u = np.mean([st[v, 1] + (w // 2 if not front and st[v, 0] else 0) for v in ids])
        v = np.mean([st[v, 2] for v in ids])
        colour[i] = pal[skin[min(h - 1, int(v)), min(w - 1, int(u))]]
    return tris[:, 1:], colour


def render_body(model, palette, table, groups, title, yaw=35.0, size=(360, 480), zoom=3.4):
    """The character's frames, group after group: engine_pose at every table frame, a 3/4 view, far faces first."""
    from PIL import Image, ImageDraw
    import skeletal_actor as S
    m = S.read_skeletal(model)
    tris, colour = model_faces(model, palette)
    a = np.radians(yaw)
    rot = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    light = np.array([0.4, -0.6, 0.7]) / np.linalg.norm([0.4, -0.6, 0.7])
    w, h = size
    frames = []
    for g in groups:
        first, last = span(table, g)
        for f in range(first, last + 1):
            p = (S.engine_pose(m, table, f) * m['pose_step'] + m['pose_origin']) @ rot.T
            img = Image.new('RGB', size, (28, 30, 38))
            d = ImageDraw.Draw(img)
            d.text((8, 6), '%s: %s frame %d' % (title, g, f - first), fill=(220, 220, 220))
            verts = p[tris]
            normal = np.cross(verts[:, 1] - verts[:, 0], verts[:, 2] - verts[:, 0])
            length = np.maximum(np.linalg.norm(normal, axis=1), 1e-9)
            shade = 0.35 + 0.65 * np.abs(normal @ light) / length
            for i in np.argsort(-verts[:, :, 1].mean(axis=1)):        # y is depth: far first
                xy = [(w / 2 + v[0] * zoom, h - 30 - v[2] * zoom) for v in verts[i]]
                d.polygon(xy, fill=tuple(int(c) for c in np.clip(colour[i] * shade[i], 0, 255)))
            frames.append(img)
    return frames


def npc_preview(assets, data, npc, palette, groups, out, rate):
    """--npc: the character's skeletal model on its skeleton's shipped table, rendered to npc-preview.gif."""
    from mwad.npc import load_master, outfit
    from mwad.paths import child_ci
    from npc_geometry import Skeleton
    import skeletal_actor as S
    kinds, _, _ = load_master(child_ci(data, 'Morrowind.esm'))
    app = outfit(kinds, npc.casefold())
    sk = Skeleton(assets, app['skeleton'])
    table_bytes, report = S.stick_table(sk)
    model, _ = S.skeletal_model(assets, app, sk, palette, table_bytes, report['bone_names'], head_detail='budget')
    table = S.read_table(table_bytes)
    shown = [g for g in groups if g in table['groups']]
    frames = render_body(model, palette, table, shown, 'AmiWind: %s on the shared table' % npc)
    frames[0].save(out / 'npc-preview.gif', save_all=True, append_images=frames[1:],
                   duration=int(round(1000 / rate)), loop=0)
    print('%s: model %d bytes, table %d bytes; groups %s: %d frames' % (npc, len(model), len(table_bytes),
                                                                       ' '.join(shown), len(frames)))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--data-files', required=True, help='the folder holding Morrowind.bsa')
    parser.add_argument('--out', required=True, help='folder for skeleton-preview.gif and skeleton-sheet.png')
    parser.add_argument('--groups', nargs='*', default=list(GROUPS))
    parser.add_argument('--npc', help='one character by its record id: npc-preview.gif instead of the bones')
    parser.add_argument('--palette', type=Path, help='the game palette (gfx/palette.lmp of a build) for --npc')
    args = parser.parse_args(argv)
    from mwad.audit import BSA
    from mwad.paths import child_ci
    from npc_geometry import Assets, Skeleton
    import skeletal_actor as S
    data = Path(args.data_files)
    assets = Assets(data, BSA(child_ci(data, 'Morrowind.bsa')))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.npc:
        if not args.palette:
            parser.error('--npc needs --palette')
        npc_preview(assets, data, args.npc, args.palette.read_bytes(), args.groups, out, S.TABLE_RATE)
        return
    shown = []
    for source, label in SKELETONS:
        table, report = S.stick_table(Skeleton(assets, source))
        shown.append((label, S.read_table(table), report))
    groups = [g for g in args.groups if all(g in t['groups'] for _, t, _ in shown)]
    frames, starts = render(shown, groups, S.TABLE_RATE)
    frames[0].save(out / 'skeleton-preview.gif', save_all=True, append_images=frames[1:],
                   duration=int(round(1000 / S.TABLE_RATE)), loop=0)
    contact_sheet(frames, starts).save(out / 'skeleton-sheet.png')
    print('groups %s: %d frames' % (' '.join(groups), len(frames)))


if __name__ == '__main__':
    main()
