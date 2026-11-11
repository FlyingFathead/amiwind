# SPDX-License-Identifier: GPL-3.0-only
"""Alternative models in one CHIM store: a second tree method selected at run time (aw_tree_crowns, TREES-DEPTH-56).

A store built with the original trees (BASE) and the same frames built with another tree method (ALT, for example the
star crowns of tools/chim_tree_star.py) become one store: the base store byte for byte, plus compact sector files that hold only ALT's
model and texture records (never its chunk, terrain or placement records), one per ALT sector file that holds any, under
cells no frame uses (the frame's cell x + CELL_SHIFT, so the engine's own file path rule names them and no frame or
prefetch plan ever reads them). Only the models the map pairs are carried (same name in both builds, made
differently), and only the textures they use that the base lacks (a texture of the same name and bytes is the base's
own); they follow the base ones in the index (names with '#alt<method>'), the texture ids inside the carried model
images renumbered to the merged ids, and a map file
chim/alt-models.bin: per method value, the pairs (base model id, alternative model id) of the models both builds
hold under the same name. The engine reads the map with the index and, when the setting names a method, takes the
alternative id at chunk load (engine/aga/src/chim/chim_chunks.c). Only models whose two builds differ are paired.

Format of alt-models.bin (big-endian, as the store): 'AWA1', u32 methods; per method: u8 value, 3 pad bytes,
u32 pairs, then pairs x (u32 base id, u32 alternative id), sorted by the base id.
TEST BUILDS ONLY for now (tools/build.py --chim-sol-tree-copies switch)."""
import hashlib
import shutil
import struct
from pathlib import Path

from chim import format as F

ALT_FILE = 'alt-models.bin'
CELL_SHIFT = 1000            # the cell x of an alternative sector file: the frame's own x plus this
MAGIC = b'AWA1'


def patch_texture_ids(image, shift):
    """IMAGE (a brush image: a model record) with every id of its texture reference lump (lump 2) moved by SHIFT
    (an int) or mapped through SHIFT (a dict: old id -> new id), in place of the same bytes (no size change)."""
    out = bytearray(image)
    o, n = struct.unpack_from('<ii', out, 4 + 8 * 2)
    ids = F.read_texture_refs(bytes(out[o:o + n]))
    move = shift.__getitem__ if isinstance(shift, dict) else (lambda i: i + shift)
    struct.pack_into('<%di' % len(ids), out, o + 4, *[move(i) if i >= 0 else i for i in ids])
    return bytes(out)


def alt_map_bytes(methods):
    """alt-models.bin of METHODS: {value: [(base id, alternative id)]}."""
    out = [MAGIC + struct.pack('>I', len(methods))]
    for value in sorted(methods):
        pairs = sorted(methods[value])
        out.append(struct.pack('>B3xI', value, len(pairs)))
        out.append(b''.join(struct.pack('>II', a, b) for a, b in pairs))
    return b''.join(out)


def read_alt_map(raw):
    if raw[:4] != MAGIC:
        raise ValueError('not an alternative model map')
    n = struct.unpack_from('>I', raw, 4)[0]
    at, methods = 8, {}
    for _ in range(n):
        value, count = struct.unpack_from('>B3xI', raw, at)
        at += 8
        methods[value] = [struct.unpack_from('>II', raw, at + 8 * i) for i in range(count)]
        at += 8 * count
    return methods


def merge(base_store, alt_store, out_store, method):
    """Write OUT_STORE (a store folder: world.cwi and its files) = BASE_STORE plus ALT_STORE's models as method
    METHOD. Returns the record: counts and bytes added."""
    base_store, alt_store, out_store = Path(base_store), Path(alt_store), Path(out_store)
    if out_store.exists():
        raise ValueError('%s already exists' % out_store)
    for path in sorted(base_store.rglob('*')):        # contents only, never the build's read-only modes
        if path.is_file():
            target = out_store / path.relative_to(base_store)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    raw_b = (base_store / 'world.cwi').read_bytes()
    raw_a = (alt_store / 'world.cwi').read_bytes()
    version = F.read_header(raw_b, b'INDX')['version']
    sb, fb, mb, tb = F.read_index(raw_b)
    sa, fa, ma, ta = F.read_index(raw_a)
    files = [dict(f) for f in fb]
    row_of = {}                               # ALT file row -> merged row (its sector files only)
    # only the models the switch can select: same name in both builds, made differently (a model both builds made
    # the same way, or one the base lacks, is never drawn through the map and is not carried)
    base_by_name = {m['name']: i for i, m in enumerate(mb)}
    kept = []                                 # (ALT index, base id)
    for k, m in enumerate(ma):
        b = base_by_name.get(m['name'])
        if b is not None and _model_sha(base_store, fb, mb[b]) != _model_sha(alt_store, fa, m):
            kept.append((k, b))
    # the textures those models use: the base's own when it has the same name and bytes, else carried
    srcs = {}

    def _src(store, flist, row):
        key = (str(store), row)
        if key not in srcs:
            srcs[key] = (Path(store) / flist[row]['path']).read_bytes()
        return srcs[key]

    def _tex_sha(store, flist, t):
        return hashlib.sha256(_src(store, flist, t['file'])[t['offset']:t['offset'] + t['bytes']]).hexdigest()

    base_tex = {}
    for i, t in enumerate(tb):
        base_tex.setdefault((t['name'], t['bytes'], t['width'], t['height']), []).append(i)
    used = set()
    for k, _b in kept:
        m = ma[k]
        img = _src(alt_store, fa, m['file'])[m['offset']:m['offset'] + m['bytes']]
        o, n = struct.unpack_from('<ii', img, 4 + 8 * 2)
        used.update(i for i in F.read_texture_refs(img[o:o + n]) if i >= 0)
    tex_map, carried = {}, []
    for t_i in sorted(used):
        t = ta[t_i]
        sha = _tex_sha(alt_store, fa, t)
        same = [i for i in base_tex.get((t['name'], t['bytes'], t['width'], t['height']), ())
                if _tex_sha(base_store, fb, tb[i]) == sha]
        if same:
            tex_map[t_i] = same[0]
        else:
            tex_map[t_i] = len(tb) + len(carried)
            carried.append(t_i)
    models_in = {}
    for k, _b in kept:
        models_in.setdefault(ma[k]['file'], []).append(k)
    added = 0
    textures_in = {}
    for t_i in carried:
        textures_in.setdefault(ta[t_i]['file'], []).append(t_i)
    model_id = {k: len(mb) + j for j, (k, _b) in enumerate(kept)}
    new_at = {}                               # ('m' | 't', ALT index) -> offset in its compact file
    for i, f in enumerate(fa):
        # the sector files that hold an alternative model or texture (a texture may live where no model does);
        # each becomes a compact sector file of only those records: never the build's chunk or terrain records
        if i not in models_in and i not in textures_in:
            continue
        if f['kind'] != b'SECT':
            raise ValueError('an alternative model or texture lives in a file that is not a sector file: row %d' % i)
        src = (alt_store / f['path']).read_bytes()
        records, keys = [], []
        for k in models_in.get(i, ()):
            m = ma[k]
            records.append((b'MODL', model_id[k],
                            patch_texture_ids(src[m['offset']:m['offset'] + m['bytes']], tex_map)))
            keys.append(('m', k))
        for t_i in textures_in.get(i, ()):
            t = ta[t_i]
            records.append((b'TEXR', tex_map[t_i], src[t['offset']:t['offset'] + t['bytes']]))
            keys.append(('t', t_i))
        data = F.sector_file(records, version)
        offsets, _ = F.sector_layout(records)
        for key, (kind, rid, _d) in zip(keys, records):
            new_at[key] = offsets[(kind, rid)]
        cell = (f['cell'][0] + CELL_SHIFT, f['cell'][1])
        path = 'frames/x%+03d/y%+03d/%s' % (cell[0], cell[1], f['path'].rsplit('/', 1)[1])
        target = out_store / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        row_of[i] = len(files)
        files.append(dict(f, cell=cell, path=path, crc=F.crc32(data), bytes=len(data), entries=len(records)))
        added += len(data)
    tag = '#alt%d' % method
    models = [(m['name'], m['file'], m['offset'], m['bytes'], m['render']) for m in mb]
    textures = [(t['name'], t['file'], t['offset'], t['bytes'], t['width'], t['height']) for t in tb]
    for t_i in carried:
        t = ta[t_i]
        textures.append((t['name'] + tag, row_of[t['file']], new_at[('t', t_i)], t['bytes'], t['width'], t['height']))
    pairs = []
    for k, b in kept:
        m = ma[k]
        pairs.append((b, len(models)))
        models.append((m['name'] + tag, row_of[m['file']], new_at[('m', k)], m['bytes'], m['render']))
    settings = dict(sb, models=len(models), textures=len(textures))
    (out_store / 'world.cwi').write_bytes(F.index_file(settings, files, models, textures, version))
    old = read_alt_map((out_store / ALT_FILE).read_bytes()) if (out_store / ALT_FILE).is_file() else {}
    old[method] = pairs
    (out_store / ALT_FILE).write_bytes(alt_map_bytes(old))
    return {'method': method, 'pairs': len(pairs), 'models_added': len(kept), 'textures_added': len(carried),
            'textures_shared': len(used) - len(carried), 'files_added': len(row_of), 'bytes_added': added}


def _model_sha(store, files, m):
    """SHA-256 of a model record with its texture reference lump left out (the two builds may number the same
    textures differently): equal for a model both builds made the same way."""
    data = bytearray((Path(store) / files[m['file']]['path']).read_bytes()[m['offset']:m['offset'] + m['bytes']])
    o, n = struct.unpack_from('<ii', data, 4 + 8 * 2)
    data[o:o + n] = bytes(n)
    return hashlib.sha256(bytes(data)).hexdigest()
