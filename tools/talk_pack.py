#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The talk pack (id1/talk.awt): the original heads' Talk morph, for the mouths of the skeletal actors
(NPC-TALK-MOUTH-STILL-69; docs/INTRO_SCRIPT_MAPPING.md "Voices and faces").

The original moves a speaking NPC's mouth by its head's Talk morph: every head of the game (meshes/b/*head*.nif, 162 in
the three masters) holds a NiGeomMorpherController whose "talk: start" .. "talk: stop" range opens the mouth, and while
the NPC says anything (a greeting, an idle or combat line, a script's Say, a conversation's line) the morph's time
follows the loudness of the line playing (rule from OpenMW 0.53 apps/openmw/mwrender/npcanimation.cpp 162-195
HeadAnimationTime::update and 834-846, apps/openmw/mwsound/soundmanagerimp.cpp 381-391). The opening's 21-frame actors
carry that morph as their talk frames 8..11 (tools/npc_faces.py); the skeletal actors, every other NPC, carry none.

This stage reads only the game data (no stage's output): for every head the NPC records use, the morph sampled at the
three open levels the engine's speech envelope selects (amounts 1/3, 2/3 and 1 of the talk range, as the talk frames
9..11), in the bone space of the table's head bone (the space the skeletal model's head vertices are stored in:
tools/skeletal_actor.py export_actor and onto_kept), for the vertices the morph moves and the still ones around them.
The engine moves a speaking actor's head vertices by these offsets, each by the offsets of the original vertices
around it (engine/aga/src/aw_talkpack.c), so the reduced heads of the skeletal models follow the original's morph
wherever their vertices lie. An NPC whose outfit puts a helmet in the head's place has no entry: the original draws
no head under such a helmet. No existing stage changes: the image stage copies the file.

Format (big-endian, the Amiga's order):
  "AWTP", u16 version 1, u16 heads, u32 records, u32 head bytes, u16 head bone, u16 0;
  records x {u32 FNV-1a 32 of the record id (ASCII letters lowered, other bytes as they are; aw_talkpack.c
             AW_TalkHash), u16 head, u16 0}, sorted by the hash, no hash twice;
  heads x {u32 offset into the head bytes, u16 vertices, u16 0};
  head bytes: per head, vertices x {i16 x y z (bone space, POSITION_UNITS a unit), i8 x y z per open level 1..3
             (bone space, OFFSET_UNITS a unit), u8 0}.

  python3 tools/talk_pack.py --data-files DIR --out DIR [--jobs N]
"""
import argparse
import io
import json
import struct
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools', ROOT / 'src'):
    while str(_p) in sys.path:
        sys.path.remove(str(_p))
    sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402

MAGIC = b'AWTP'
VERSION = 1
NAME = 'talk.awt'
REPORT = 'talk-report.json'
HEADER = 20
RECORD = '>IHH'
HEAD = '>IHH'
VERTEX_BYTES = 16
POSITION_UNITS = 256.0          # i16 position steps a bone-space unit (a head spans about +-30 units)
OFFSET_UNITS = 32.0             # i8 offset steps a unit (the largest talk offset of the 162 heads: 2.85 NIF units)
LEVELS = (1 / 3, 2 / 3, 1.0)    # the talk frames 9..11 of the 21-frame actor (tools/npc_faces.py actor_samples)
MOVES = 0.01                    # a vertex the full morph moves further than this (units) is a moving one
AROUND = 1.0                    # still vertices this near a moving one are kept as anchors (zero offsets)
HEAD_BONE = 'bip01 head'
MAX_ROWS = 256                  # the engine's AW_TALK_REGION: a head's kept vertices


def fnv1a(ident):
    """The record id's hash as aw_talkpack.c AW_TalkHash computes it: FNV-1a 32 over its Windows-1252 bytes, ASCII
    letters lowered (the engine compares record ids so: greeting_lut.id_bytes)."""
    h = 0x811C9DC5
    for b in ident.encode('cp1252', errors='replace'):
        if 65 <= b <= 90:
            b += 32
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return h


def head_part(appearance):
    """The part in the head's place of an appearance (mwad.npc.outfit: filter Head; a helmet when one is worn), or None."""
    return next((p for p in appearance.get('parts', ()) if str(p.get('filter', '')).casefold() == 'head'), None)


def morph_shape(nif, N):
    """The first shape of a NIF with a morph controller (the one tools/npc_faces.py sample_morph reads), or None."""
    for block in nif.get_global_iterator():
        if isinstance(block, N.NiTriShape) and block.data:
            c = block.controller
            while c and not isinstance(c, N.NiGeomMorpherController):
                c = c.next_controller
            if c is not None:
                return block
    return None


_context = None


def _head(task):
    """(key, rows or None, facts) of one head: its Talk morph in the head bone's space. rows: [(x, y, z, offsets
    (3 levels x 3))]; None when the part has no Talk morph (a helmet) or cannot be read so (the reason in facts)."""
    global _context
    data, mesh, skeleton_path = task
    from mwad.archives import layered_bsa
    from npc_geometry import Assets, Skeleton
    from npc_faces import sample_morph
    import skeletal_actor as SA
    if _context is None or _context[0] != data:
        _context = (data, Assets(data, layered_bsa(data)), {})
    _, assets, skeletons = _context
    if skeleton_path not in skeletons:
        skeletons[skeleton_path] = Skeleton(assets, skeleton_path)
    sk = skeletons[skeleton_path]
    key = (mesh, skeleton_path)
    nif = sk.N.Data()
    nif.read(io.BytesIO(assets.read('meshes/' + mesh.replace('\\', '/'))))
    shape = morph_shape(nif, sk.N)
    if shape is None:
        return key, None, {'mesh': mesh, 'skipped': 'no morph controller'}
    try:
        poses = [sample_morph(shape, nif, sk.N, a) for a in (0.0,) + LEVELS]
    except ValueError as error:
        return key, None, {'mesh': mesh, 'skipped': str(error)}
    part = {'slot': 0, 'attach': 'Head', 'filter': 'Head', 'id': 'talk', 'mesh': mesh}
    shapes = SA.export_actor(assets, {'parts': [part], 'skeleton': skeleton_path}, sk)
    if len(shapes) != 1 or len(shapes[0]['rest']) != len(poses[0]):
        return key, None, {'mesh': mesh, 'skipped': 'the head shape is not the morphed one'}
    world = sk.pose(sk.idle_times(1)[0][0])
    kept = SA.onto_kept(shapes[0], sk.parents, frozenset(SA.STICK_BONES), world)
    rest = np.asarray(kept['rest'], float)
    if sorted({kept['bones'][b] for b in np.asarray(kept['bone']).tolist()}) != [HEAD_BONE]:
        return key, None, {'mesh': mesh, 'skipped': 'the head is not on the head bone'}
    # the head's own frame into the bone's: the affine fit of the morph's rest pose onto the bone-space rest (exact for
    # a rigid part, checked)
    base = poses[0]
    hom = np.column_stack((base, np.ones(len(base))))
    fit, *_ = np.linalg.lstsq(hom, rest, rcond=None)
    if np.abs(hom @ fit - rest).max() > 1e-3:
        return key, None, {'mesh': mesh, 'skipped': 'the head part is not rigid'}
    offsets = np.stack([(p - base) @ fit[:3] for p in poses[1:]], axis=1)        # vertices x 3 levels x 3
    moving = np.abs(offsets[:, -1]).max(axis=1) > MOVES
    if not moving.any():
        return key, [], {'mesh': mesh, 'vertices': len(rest), 'moving': 0, 'kept': 0}
    from scipy.spatial import cKDTree
    near, _ = cKDTree(rest[moving]).query(rest)
    keep = moving | (near <= AROUND)
    if keep.sum() > MAX_ROWS:
        return key, None, {'mesh': mesh, 'skipped': 'more than %d vertices around the mouth' % MAX_ROWS}
    rows = [(*rest[v], offsets[v]) for v in np.flatnonzero(keep)]
    return key, rows, {'mesh': mesh, 'vertices': len(rest), 'moving': int(moving.sum()), 'kept': int(keep.sum()),
                       'largest': round(float(np.abs(offsets).max()), 3)}


def head_bone_index():
    """The index of the head bone in the shared tables (tools/skeletal_actor.py STICK_BONES, their bone order)."""
    import skeletal_actor as SA
    return list(SA.STICK_BONES).index(HEAD_BONE)


def pack(records, heads, head_bone):
    """The file: RECORDS {record id: head index}, HEADS [rows] in head index order, HEAD_BONE the tables' head bone."""
    rec = {}
    for ident, head in records.items():
        h = fnv1a(ident)
        if h in rec and rec[h] != head:
            raise ValueError('Two records of different heads share the talk hash %08x (%s)' % (h, ident))
        rec[h] = head
    blob, table = bytearray(), []
    for rows in heads:
        table.append(struct.pack(HEAD, len(blob), len(rows), 0))
        for x, y, z, off in rows:
            pos = [int(round(c * POSITION_UNITS)) for c in (x, y, z)]
            if any(not -32768 <= c <= 32767 for c in pos):
                raise ValueError('A head vertex lies outside the talk pack range')
            d = np.clip(np.rint(np.asarray(off, float) * OFFSET_UNITS), -127, 127).astype(int).reshape(-1)
            blob += struct.pack('>3h9bB', *pos, *d.tolist(), 0)
    out = bytearray(MAGIC + struct.pack('>HHIIHH', VERSION, len(heads), len(rec), len(blob), head_bone, 0))
    for h in sorted(rec):
        out += struct.pack(RECORD, h, rec[h], 0)
    for t in table:
        out += t
    return bytes(out + blob)


def read(raw):
    """(records {hash: head}, heads [(positions (n, 3), offsets (n, 3 levels, 3))], head bone): the file as Python
    values (tests, the measurement)."""
    if raw[:4] != MAGIC:
        raise ValueError('Not a talk pack')
    version, nh, nr, nb, bone, _ = struct.unpack_from('>HHIIHH', raw, 4)
    if version != VERSION or len(raw) != HEADER + 8 * nr + 8 * nh + nb:
        raise ValueError('Talk pack size or version mismatch')
    records = {}
    for k in range(nr):
        h, head, _ = struct.unpack_from(RECORD, raw, HEADER + 8 * k)
        records[h] = head
    heads = []
    base = HEADER + 8 * nr + 8 * nh
    for k in range(nh):
        off, n, _ = struct.unpack_from(HEAD, raw, HEADER + 8 * nr + 8 * k)
        rows = np.frombuffer(raw, np.uint8, n * VERTEX_BYTES, base + off).reshape(n, VERTEX_BYTES)
        pos = rows[:, :6].copy().view('>i2').astype(float) / POSITION_UNITS
        offs = rows[:, 6:15].copy().view(np.int8).astype(float).reshape(n, 3, 3) / OFFSET_UNITS
        heads.append((pos, offs))
    return records, heads, bone


def build(data, out, jobs=None):
    """The talk pack of DATA's selected masters into OUT/talk.awt, its report OUT/talk-report.json."""
    from mwad.masters import master_path
    from mwad.npc import load_master, outfit
    from build_jobs import resolve_jobs
    from build_parallel import governed_map
    t0 = time.time()
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    print('=== PHASE 1/3: the NPC records and the part in their head\'s place', flush=True)
    kinds, _, _ = load_master(master_path(data))
    by_record, left = {}, {}
    for ident in sorted(kinds.get('NPC_', {})):
        try:
            app = outfit(kinds, ident)
        except (KeyError, ValueError) as error:
            left[ident] = str(error)
            continue
        part = head_part(app)
        if part is None:
            left[ident] = 'no part in the head\'s place'
            continue
        by_record[ident] = (part['mesh'], app['skeleton'])
    tasks = sorted(set(by_record.values()))
    print('  %d records, %d left out; %d distinct head parts' % (len(by_record), len(left), len(tasks)), flush=True)
    print('=== PHASE 2/3: each head\'s Talk morph (%d parts)' % len(tasks), flush=True)
    done, results, facts = 0, {}, []
    for key, rows, fact in governed_map(_head, [(Path(data), m, s) for m, s in tasks], jobs=resolve_jobs(jobs),
                                        unit_mib=256, label='talk heads'):
        results[key] = rows
        facts.append(fact)
        done += 1
        if done % 20 == 0 or done == len(tasks):
            print('  %d / %d parts (%.0f s)' % (done, len(tasks), time.time() - t0), flush=True)
    print('=== PHASE 3/3: the pack', flush=True)
    order = sorted(k for k, rows in results.items() if rows)
    index = {k: i for i, k in enumerate(order)}
    records = {ident: index[key] for ident, key in by_record.items() if key in index}
    raw = pack(records, [results[k] for k in order], head_bone_index())
    (out / NAME).write_bytes(raw)
    report = {'format': 'AmiWind talk pack 1', 'records': len(records), 'heads': len(order), 'bytes': len(raw),
              'records_left_out': left, 'records_without_talk': sorted(set(by_record) - set(records)),
              'seconds': round(time.time() - t0, 1), 'parts': sorted(facts, key=lambda f: f['mesh'])}
    (out / REPORT).write_text(json.dumps(report, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    print('talk pack: %d records, %d heads, %d bytes (%.1f s)' % (len(records), len(order), len(raw), time.time() - t0),
          flush=True)
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--data-files', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--jobs', type=int)
    a = p.parse_args(argv)
    build(a.data_files, a.out, a.jobs)


if __name__ == '__main__':
    main()
