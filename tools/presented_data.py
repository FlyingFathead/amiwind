# SPDX-License-Identifier: GPL-3.0-only
"""The presented data folder: the game data as the outdoor converter reads it when expansions are selected.

The outdoor converter and CHIMport read exterior grid cells from the data folder's base master. With Tribunal or
Bloodmoon selected, the cells they add are in other files, and Mournhold's outdoor districts are interior cells. This
tool makes ONE folder that holds all of it, for both expansions, without copying the game's files:

- `Morrowind.esm`: the merged master of the selected game files (src/mwad/masters.py), with the interior cells that
  behave like an exterior presented as exterior cell blocks of their own (tools/presented_exterior.py);
- every other selected master (`Tribunal.esm`, `Bloodmoon.esm`) as a header-only file that adds nothing, so the
  same masters stay selected and the archives are layered exactly as in any build;
- every other entry of the data folder (the archives, loose files and folders) as a link to the original;
- `presented-data.json`: the receipt (the inputs' SHA-256, the merged and the presented master's SHA-256, the
  presented cells with their blocks and offsets, what was linked).

With the base game alone no folder is made: the data folder itself is the answer, so a build without expansions
reads exactly what it read before.

    python3 tools/presented_data.py --data-files DATA --out FOLDER [--masters Morrowind.esm,Tribunal.esm,Bloodmoon.esm]
"""
import argparse
import hashlib
import json
import os
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools', ROOT / 'src'):
    while str(_p) in sys.path:
        sys.path.remove(str(_p))
    sys.path.insert(0, str(_p))

FORMAT = 'aw-presented-data-1'
RECEIPT = 'presented-data.json'


def header_only_master():
    """A master that holds nothing: one TES3 record with a HEDR that counts 0 records."""
    hedr = struct.pack('<fI32s256sI', 1.3, 1, b'', b'', 0)
    return struct.pack('<4sIII', b'TES3', 8 + len(hedr), 0, 0) + struct.pack('<4sI', b'HEDR', len(hedr)) + hedr


def _inputs(data_files, masters):
    from mwad.paths import child_ci
    return {name: hashlib.sha256(child_ci(Path(data_files), name).read_bytes()).hexdigest() for name in masters}


def expected(data_files, masters, config):
    """What decides the folder's content: the selected masters' SHA-256 in load order, the merge's and the
    presentation's formats and the block config."""
    from mwad.masters import FORMAT as MERGE_FORMAT
    import presented_exterior
    return {'format': FORMAT, 'masters': list(masters), 'inputs': _inputs(data_files, masters),
            'merge_format': MERGE_FORMAT, 'presented_format': presented_exterior.FORMAT, 'config': config}


def make(data_files, out, masters=None, config=None):
    """Make the presented data folder OUT for DATA_FILES and the selected MASTERS; returns (the folder to read, the
    receipt or None). Base game alone: (DATA_FILES, None), nothing written. An existing OUT made from the same inputs
    is taken as it is; one made from other inputs is refused (existing data is never overwritten)."""
    from mwad.esm import GAME_MASTERS
    from mwad.masters import BASE_MASTER, is_base_only, master_bytes, selected_masters
    import presented_exterior
    data_files, out = Path(data_files), Path(out)
    masters = selected_masters(masters)
    if is_base_only(masters):
        return data_files, None
    config = config or presented_exterior.load_config()
    want = expected(data_files, masters, config)
    receipt_path = out / RECEIPT
    if receipt_path.is_file():
        have = json.loads(receipt_path.read_text(encoding='utf-8'))
        if all(have.get(k) == v for k, v in want.items()):
            return out, have
        raise ValueError('%s was made from other inputs: choose a new folder' % out)
    if out.exists() and any(out.iterdir()):
        raise ValueError('%s exists and holds no receipt: choose a new folder' % out)
    out.mkdir(parents=True, exist_ok=True)
    merged = master_bytes(data_files, masters)
    presented, cells = presented_exterior.present(merged, config)
    (out / BASE_MASTER).write_bytes(presented)
    stubs = [name for name in masters if name != BASE_MASTER]
    for name in stubs:
        (out / name).write_bytes(header_only_master())
    skip = {m.casefold() for m in GAME_MASTERS}
    linked = []
    for entry in sorted(data_files.iterdir(), key=lambda p: p.name):
        if entry.name.casefold() in skip:
            continue                    # a game master is never linked: only the selected ones exist in the folder
        os.symlink(entry.resolve(), out / entry.name, target_is_directory=entry.is_dir())
        linked.append(entry.name)
    receipt = dict(want, merged_sha256=hashlib.sha256(merged).hexdigest(),
                   presented_sha256=hashlib.sha256(presented).hexdigest(), header_only=stubs,
                   linked=linked, presented_cells=cells['cells'],
                   exterior_cells_written=cells.get('exterior_cells_written', 0),
                   destinations_rewritten=cells.get('destinations_rewritten', 0))
    receipt_path.write_text(json.dumps(receipt, indent=1) + '\n', encoding='utf-8', newline='\n')
    return out, receipt


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    p.add_argument('--data-files', required=True)
    p.add_argument('--out', required=True, help='the folder to make (new, or one made from the same inputs)')
    p.add_argument('--masters', help='the selected masters in load order (default: AMIWIND_MASTERS)')
    a = p.parse_args(argv)
    try:
        folder, receipt = make(a.data_files, a.out, a.masters)
    except ValueError as exc:
        p.exit(1, 'Error: %s\n' % exc)
    if receipt is None:
        print('base game alone: no presented folder; read %s' % folder)
        return 0
    print('presented data folder %s: masters %s, %d entries linked, %d cell(s) presented as %d exterior cells, '
          '%d destinations rewritten' % (folder, ', '.join(receipt['masters']), len(receipt['linked']),
                                         len(receipt['presented_cells']), receipt['exterior_cells_written'],
                                         receipt['destinations_rewritten']))
    for row in receipt['presented_cells']:
        print('  %s: block %d,%d (%d x %d cells)' % (row['cell'], row['block'][0], row['block'][1],
                                                    row['size'][0], row['size'][1]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
