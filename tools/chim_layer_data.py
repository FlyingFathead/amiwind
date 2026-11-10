#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""A layered test data folder for one expansion's CHIM frames (DLC-BUILD-LATER, TEST BUILDS ONLY).

The CHIM exterior converters read one standalone master (Morrowind.esm, mwad.audit.load_esm refuses a plugin) and
one archive (Morrowind.bsa). To build and measure an expansion's frames before every reader takes a master list,
this writes a private data folder whose Morrowind.esm is the base master with the layer's records appended and whose
Morrowind.bsa holds the base archive's files plus the layer archive's (the layer's file wins). The converters then
build the layer's cells unchanged, and none of the base world's code or keys move: the folder feeds only the layer's
own test stage (chim-sol, keyed by its own masters in build_cache.STAGE_GAME_INPUTS).

Merge rules (the game's load order, plainly; what a test frame needs, not a full content loader):
- the layer's exterior CELL and LAND records at a grid position the base master has are left out (the layer's frames
  are its new ground; the four base cells it adds a placement to keep the base version here);
- an object id the base master already defines keeps the base record;
- the layer's land textures (LTEX) are numbered after the base's, and its LAND texture indices (VTEX) follow them;
- the layer's reference numbers (FRMR) get the layer's master index in bits 22 and up, the reference key of
  tools/mwscript/gamedata.py (MASTERS index x 2^22 + number), so they never meet a base number;
- the TES3 header keeps the base master's, with the record count of the merged file and no MAST.

    python3 tools/chim_layer_data.py --data-files DATA --layer Bloodmoon --out DIR
"""
import argparse
import hashlib
import json
import os
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / 'src', ROOT / 'tools'):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

FORMAT = 'aw-chim-layer-data-1'
MASTERS = ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')     # tools/mwscript/gamedata.py MASTERS
OBJECT_TAGS = set('STAT DOOR MISC WEAP CONT CREA LIGH NPC_ ARMO CLOT REPA ACTI APPA LOCK PROB INGR BOOK ALCH LEVI '
                  'LEVC'.split())


def _record(tag, flags, payload):
    return struct.pack('<4sIII', tag.encode('ascii'), len(payload), 0, flags) + payload


def _sub(tag, data):
    return struct.pack('<4sI', tag.encode('ascii'), len(data)) + data


def _fields(payload):
    from mwad.esm import subrecords
    return list(subrecords(payload))


def _head(subs):
    """The subrecords before the first FRMR (a CELL's header) as a dict."""
    out = {}
    for tag, data in subs:
        if tag == 'FRMR':
            break
        out.setdefault(tag, data)
    return out


def base_index(raw):
    """(exterior cells, LAND cells, object ids, highest LTEX number + 1) of the base master."""
    from mwad.esm import records, string
    cells, lands, objects, ltex = set(), set(), set(), 0
    for tag, flags, payload in records(raw):
        if tag == 'CELL':
            s = _head(_fields(payload))
            bits, x, y = struct.unpack('<Iii', s['DATA'])
            if not bits & 1:
                cells.add((x, y))
        elif tag == 'LAND':
            s = dict(_fields(payload))
            lands.add(struct.unpack('<ii', s['INTV']))
        elif tag in OBJECT_TAGS:
            s = dict(_fields(payload))
            if 'NAME' in s:
                objects.add(string(s['NAME'], tag + ' NAME').casefold())
        elif tag == 'LTEX':
            s = dict(_fields(payload))
            ltex = max(ltex, struct.unpack('<I', s['INTV'])[0] + 1)
    return cells, lands, objects, ltex


def layer_records(raw, base, master_index):
    """The layer's records to append (bytes each) and what was left out, by the merge rules above."""
    from mwad.esm import records, string
    cells, lands, objects, ltex = base
    out, left = [], {'base_cells': 0, 'base_lands': 0, 'base_objects': 0, 'header': 0}
    shift = master_index << 22
    for tag, flags, payload in records(raw):
        subs = _fields(payload)
        if tag == 'TES3':
            left['header'] += 1
            continue
        if tag == 'CELL':
            s = _head(subs)
            bits, x, y = struct.unpack('<Iii', s['DATA'])
            if not bits & 1 and (x, y) in cells:
                left['base_cells'] += 1
                continue
            rebuilt = b''
            for key, data in subs:
                if key == 'FRMR':
                    number = struct.unpack('<I', data)[0]
                    if number >> 22:
                        raise ValueError('Reference %d edits a master placement: a full content loader is needed'
                                         % number)
                    data = struct.pack('<I', number | shift)
                rebuilt += _sub(key, data)
            out.append(_record(tag, flags, rebuilt))
            continue
        if tag == 'LAND':
            s = dict(subs)
            if struct.unpack('<ii', s['INTV']) in lands:
                left['base_lands'] += 1
                continue
            rebuilt = b''
            for key, data in subs:
                if key == 'VTEX':
                    values = struct.unpack('<256H', data)
                    data = struct.pack('<256H', *(v + ltex if v else 0 for v in values))
                rebuilt += _sub(key, data)
            out.append(_record(tag, flags, rebuilt))
            continue
        if tag == 'LTEX':
            rebuilt = b''
            for key, data in subs:
                if key == 'INTV':
                    data = struct.pack('<I', struct.unpack('<I', data)[0] + ltex)
                rebuilt += _sub(key, data)
            out.append(_record(tag, flags, rebuilt))
            continue
        if tag in OBJECT_TAGS:
            s = dict(subs)
            if 'NAME' in s and string(s['NAME'], tag + ' NAME').casefold() in objects:
                left['base_objects'] += 1
                continue
        out.append(_record(tag, flags, payload))
    return out, left


def merged_master(base_raw, layer_raw, master_index):
    from mwad.esm import records
    base = base_index(base_raw)
    appended, left = layer_records(layer_raw, base, master_index)
    body, count, header = [], 0, None
    for tag, flags, payload in records(base_raw):
        if tag == 'TES3':
            header = (flags, payload)
            continue
        body.append(_record(tag, flags, payload))
        count += 1
    flags, payload = header
    subs = _fields(payload)
    rebuilt = b''
    for key, data in subs:
        if key == 'HEDR':
            data = data[:296] + struct.pack('<I', count + len(appended))
        rebuilt += _sub(key, data)
    return _record('TES3', flags, rebuilt) + b''.join(body) + b''.join(appended), \
        {'base_records': count, 'layer_records': len(appended), 'left_out': left, 'ltex_offset': base[3]}


def merged_archive(paths, out):
    """One TES3 BSA of every file of PATHS (later archives win); hashes are written as zero (no reader here uses
    them)."""
    from mwad.audit import BSA
    entries = {}
    for path in paths:
        bsa = BSA(path)
        for name, row in bsa.entries.items():
            entries[name] = (path, row)
    names = sorted(entries)
    blob, offsets = b'', []
    for name in names:
        offsets.append(len(blob))
        blob += name.replace('/', '\\').encode('ascii') + b'\0'
    count = len(names)
    sizes, data_offset = [], 0
    for name in names:
        sizes.append((entries[name][1]['bytes'], data_offset))
        data_offset += entries[name][1]['bytes']
    directory = (b''.join(struct.pack('<II', *s) for s in sizes) + b''.join(struct.pack('<I', o) for o in offsets)
                 + blob)
    with open(out, 'xb') as f:
        f.write(struct.pack('<III', 0x100, len(directory), count))
        f.write(directory)
        f.write(bytes(8 * count))
        for i, name in enumerate(names):
            path, row = entries[name]
            with open(path, 'rb') as src:
                src.seek(row['offset'])
                raw = src.read(row['bytes'])
            if len(raw) != row['bytes']:
                raise ValueError('Truncated archive entry ' + name)
            f.write(raw)
            if (i + 1) % 2000 == 0:
                print('  archive: %d / %d files' % (i + 1, count), flush=True)
    return count


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def make(data_files, layer, out):
    from mwad.paths import child_ci
    data_files, out = Path(data_files), Path(out)
    master = layer + '.esm'
    if master not in MASTERS[1:]:
        raise ValueError('Unknown expansion layer: ' + layer)
    out.mkdir(parents=True, exist_ok=False)
    print('=== PHASE 1/3: merged master (Morrowind.esm + %s) ===' % master, flush=True)
    base_esm, layer_esm = child_ci(data_files, 'Morrowind.esm'), child_ci(data_files, master)
    raw, counts = merged_master(base_esm.read_bytes(), layer_esm.read_bytes(), MASTERS.index(master))
    (out / 'Morrowind.esm').write_bytes(raw)
    print('  %s' % json.dumps(counts), flush=True)
    print('=== PHASE 2/3: merged archive (Morrowind.bsa + %s.bsa) ===' % layer, flush=True)
    archives = [child_ci(data_files, 'Morrowind.bsa'), child_ci(data_files, layer + '.bsa')]
    files = merged_archive(archives, out / 'Morrowind.bsa')
    print('=== PHASE 3/3: loose asset folders linked, receipt ===', flush=True)
    for name in ('Meshes', 'Textures', 'Icons', 'BookArt', 'Fonts', 'Splash', 'Sound', 'Music'):
        source = child_ci(data_files, name, required=False)
        if source is not None and source.is_dir():
            os.symlink(source, out / name)
    receipt = {'format': FORMAT, 'layer': layer, 'test_only': True,
               'inputs': {p.name: sha256(p) for p in (base_esm, layer_esm, *archives)},
               'outputs': {'Morrowind.esm': sha256(out / 'Morrowind.esm'), 'Morrowind.bsa': sha256(out / 'Morrowind.bsa')},
               'master': counts, 'archive_files': files}
    (out / 'layer-data.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8', newline='\n')
    return receipt


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--data-files', type=Path, required=True)
    ap.add_argument('--layer', choices=('Tribunal', 'Bloodmoon'), required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(argv)
    try:
        print(json.dumps(make(a.data_files, a.layer, a.out), indent=2))
    except (OSError, ValueError) as exc:
        ap.exit(1, 'Error: %s\n' % exc)
    return 0


if __name__ == '__main__':
    sys.exit(main())
