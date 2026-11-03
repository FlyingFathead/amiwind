#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The items index (ITEMS-INDEX-57): every item the player can pick up that the game's records place in the world.

For every live placed reference of the base master whose record is a carriable item (weapon, armour, clothing,
potion, ingredient, book, misc item split into plain, gold and keys, a light that can be carried, apparatus,
lockpick, probe, repair tool): its cell, position (game units), item id, kind and owner (the reference's owner ANAM,
else its owning faction CNAM, the rule of OpenMW 0.51 mwmechanics/mechanicsmanagerimp.cpp itemTaken).

It reuses the focus table's readers (tools/prepare_focus.py: cells_of for the placed references, objects_of for what
counts as an item, the same filters as the framed box and the pick-up) and the stable reference ids
(tools/ref_identity.py); nothing here parses the master on its own.

  build   --data-files DIR --out DIR   writes DIR/items-index.json: the compact index (game data, private output)
          plus its summary. Keyed by content only: the master's SHA-256 and the SHA-256 of the reading code; an
          existing index with the same key is reused, never recomputed (it says so).
  render  --index FILE --doc docs/ITEMS_INDEX.md --release X.Y.Z   writes the public page from the summary only (totals by kind and
          by region, the most notable single items); never the entries.
  check   --index FILE --doc docs/ITEMS_INDEX.md --release X.Y.Z   exit 1 when the page is not what render would write.

Compact format "AWII1" (JSON): kinds and cells as lists, each entry [reference, cell index, x, y, z, item id,
kind index, owner id or "", 1 when a faction owns it].
"""
import argparse
import hashlib
import json
import math
import struct
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]   # src first: the mwad package, not tools/mwad.py
from mwad.esm import records, subrecords, string, first  # noqa: E402
from prepare_focus import ITEM_DATA, MASTER, cells_of, objects_of  # noqa: E402
from ref_identity import RefIdentityError, stable_ref  # noqa: E402

FORMAT = 'AWII1'
KINDS = ('weapon', 'armour', 'clothing', 'ingredient', 'misc', 'gold', 'key', 'book', 'potion', 'apparatus',
         'lockpick', 'probe', 'repair', 'light')
TAG_KIND = {'WEAP': 'weapon', 'ARMO': 'armour', 'CLOT': 'clothing', 'INGR': 'ingredient', 'MISC': 'misc',
            'BOOK': 'book', 'ALCH': 'potion', 'APPA': 'apparatus', 'LOCK': 'lockpick', 'PROB': 'probe',
            'REPA': 'repair', 'LIGH': 'light'}
MISC_KEY = 1              # MCDT flags: a key
INTERIORS = 'Interiors'   # the region line of every interior cell
NOTABLE = 12             # rows per notable list on the page
KEY_SOURCES = ('tools/items_index.py', 'tools/prepare_focus.py', 'tools/ref_identity.py', 'src/mwad/esm.py')


def item_kinds(raw):
    """Folded record id -> (kind, display name, value) of every carriable item record (prepare_focus.objects_of
    decides what is an item; this adds the record type, with keys and gold split off the misc items)."""
    objects = objects_of(raw)
    out = {}
    for tag, flags, payload in records(raw):
        if tag not in ITEM_DATA or flags & 0x20:
            continue
        fields = list(subrecords(payload))
        ident = string(first(fields, 'NAME'), 'NAME', errors='replace').casefold()
        obj = objects.get(ident)
        if not obj or obj[0] != 'I':
            continue
        kind = TAG_KIND[tag]
        if tag == 'MISC':
            data = first(fields, 'MCDT')
            if ident.startswith('gold_'):
                kind = 'gold'
            elif len(data) >= 12 and struct.unpack_from('<i', data, 8)[0] & MISC_KEY:
                kind = 'key'
        out[ident] = (kind, obj[1], obj[3])
    return out


def region_names(raw):
    out = {}
    for tag, flags, payload in records(raw):
        if tag == 'REGN' and not flags & 0x20:
            fields = list(subrecords(payload))
            out[string(first(fields, 'NAME'), 'NAME', errors='replace').casefold()] = \
                string(first(fields, 'FNAM'), 'FNAM', errors='replace')
    return out


def owner_field(ref):
    """(owner id, 1 when a faction owns it) of a placed reference; ('', 0) when nobody owns it."""
    for key, faction in (('ANAM', 0), ('CNAM', 1)):
        if ref.get(key):
            ident = string(ref[key], key, errors='replace').strip().casefold()
            if ident:
                return ident, faction
    return '', 0


def door_targets(raw):
    """Folded names of every interior cell some placed door leads to (a reference's DNAM)."""
    out = set()
    for _cell, _interior, _grid, _region, refs in cells_of(raw):
        for ref in refs:
            if ref.get('DNAM') and 'DELE' not in ref:
                out.add(string(ref['DNAM'], 'DNAM', errors='replace').strip().casefold())
    return out


def unreachable(cell, interior, targets):
    """The test-cell rule: an interior cell is left out when its name has 'test' in it (the developers' cells such
    as ToddTest) or when no door of the master leads to it (the player cannot walk in; only the console reaches
    it). Exterior cells are always kept."""
    name = cell.strip().casefold()
    return interior and ('test' in name or name not in targets)


def index(raw):
    """The compact index of RAW (a master's bytes): {format, kinds, cells, regions, items, names, values, dropped}."""
    kinds = item_kinds(raw)
    regions = region_names(raw)
    targets = door_targets(raw)
    cells, cell_at, entries = [], {}, []
    dropped = {}
    for cell, interior, grid, region, refs in cells_of(raw):
        if unreachable(cell, interior, targets):
            n = sum(1 for r in refs if 'DELE' not in r and 'NAME' in r and
                    string(r['NAME'], 'NAME', errors='replace').casefold() in kinds)
            if n:
                dropped[cell.strip()] = n
            continue
        label = cell.strip() if interior else '%s (%d, %d)' % (cell.strip() or regions.get(region, '') or 'Wilderness',
                                                               grid[0], grid[1])
        area = INTERIORS if interior else (regions.get(region, '') or 'No region')
        for ref in refs:
            if 'DELE' in ref or 'NAME' not in ref or len(ref.get('DATA', b'')) != 24:
                continue
            ident = string(ref['NAME'], 'NAME', errors='replace').casefold()
            if ident not in kinds:
                continue
            try:
                reference = stable_ref(MASTER, ref['number'])
            except RefIdentityError:
                reference = ref['number']
            x, y, z = struct.unpack_from('<fff', ref['DATA'])
            if not all(map(math.isfinite, (x, y, z))):
                continue
            key = (label, area, bool(interior))
            if key not in cell_at:
                cell_at[key] = len(cells)
                cells.append([label, area, int(bool(interior))])
            owner, faction = owner_field(ref)
            entries.append([reference, cell_at[key], round(x), round(y), round(z), ident,
                            KINDS.index(kinds[ident][0]), owner, faction])
    used = sorted({e[5] for e in entries})
    return {'format': FORMAT, 'kinds': list(KINDS), 'cells': cells, 'items': sorted(entries),
            'names': {i: kinds[i][1] for i in used}, 'values': {i: kinds[i][2] for i in used},
            'dropped': dict(sorted(dropped.items()))}


def summary(idx):
    """The public summary of an index: totals by kind and region (with the owned share) and the notable singles."""
    kinds, cells, items = idx['kinds'], idx['cells'], idx['items']
    by_kind, by_region = defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
    placed = Counter(e[5] for e in items)
    for e in items:
        owned = int(bool(e[7]))
        for table, key in ((by_kind, kinds[e[6]]), (by_region, cells[e[1]][1])):
            table[key][0] += 1
            table[key][1] += owned
    exterior_cells = {e[1] for e in items if not cells[e[1]][2]}
    interior_cells = {e[1] for e in items if cells[e[1]][2]}

    def row(e):
        return {'item': idx['names'][e[5]], 'id': e[5], 'kind': kinds[e[6]], 'value': idx['values'][e[5]],
                'cell': cells[e[1]][0], 'owned': bool(e[7])}
    singles = sorted((e for e in items if placed[e[5]] == 1 and kinds[e[6]] not in ('gold', 'key')),
                     key=lambda e: (-idx['values'][e[5]], e[5]))
    # loose weapons outdoors: unowned, in an exterior cell (the iron axe in the pit by Seyda Neen is one)
    lone = [e for e in items if not cells[e[1]][2] and kinds[e[6]] == 'weapon' and not e[7]]
    lone.sort(key=lambda e: (-idx['values'][e[5]], e[5], e[0]))
    dropped = idx.get('dropped', {})
    return {'dropped_cells': len(dropped), 'dropped_items': sum(dropped.values()),
            'placed': len(items), 'owned': sum(1 for e in items if e[7]), 'distinct_items': len(placed),
            'exterior_cells': len(exterior_cells), 'interior_cells': len(interior_cells),
            'by_kind': {k: by_kind[k] for k in kinds if k in by_kind},
            'by_region': dict(sorted(by_region.items(), key=lambda kv: (kv[0] == INTERIORS, -kv[1][0], kv[0]))),
            'single_placements': len(singles), 'notable_singles': [row(e) for e in singles[:NOTABLE]],
            'lone_weapons_outdoors': len(lone), 'notable_lone_weapons': [row(e) for e in lone[:NOTABLE]]}


def content_key(master_sha256):
    """The index's key: the master's SHA-256 and the SHA-256 of every source file that reads it."""
    h = hashlib.sha256(master_sha256.encode('ascii'))
    for rel in KEY_SOURCES:
        h.update(rel.encode('ascii') + b'\0' + hashlib.sha256((ROOT / rel).read_bytes()).digest())
    return h.hexdigest()


def build(data_files, out):
    from mwad.paths import resolve_data_files, child_ci
    started = time.time()
    print('=== PHASE 1/3: hash the master ===', flush=True)
    raw = child_ci(resolve_data_files(Path(data_files)), MASTER).read_bytes()
    master_sha = hashlib.sha256(raw).hexdigest()
    key = content_key(master_sha)
    target = Path(out) / 'items-index.json'
    if target.is_file():
        try:
            old = json.loads(target.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            old = {}
        if old.get('key') == key and old.get('format') == FORMAT:
            print('[items-index] reused %s (key %s): %d placed items' % (target, key[:16], old['summary']['placed']),
                  flush=True)
            return old, True
    print('=== PHASE 2/3: read the placed references ===', flush=True)
    idx = index(raw)
    # the build date is recorded once with the index (a reused index keeps it): the page's Last-updated date
    idx.update(key=key, master=MASTER, master_sha256=master_sha, built=time.strftime('%Y-%m-%d'),
               summary=summary(idx))
    print('=== PHASE 3/3: write %s ===' % target, flush=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(idx, separators=(',', ':'), ensure_ascii=False) + '\n', encoding='utf-8',
                      newline='\n')
    s = idx['summary']
    print('[items-index] %d placed items (%d owned), %d distinct, %d exterior and %d interior cells, took %.1f s'
          % (s['placed'], s['owned'], s['distinct_items'], s['exterior_cells'], s['interior_cells'],
             time.time() - started), flush=True)
    return idx, False


def pct(part, whole):
    return '%d %%' % round(100.0 * part / whole) if whole else '-'


MONTHS = ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
          'November', 'December')


def long_date(iso):
    """'2026-11-03' -> '3 November 2026' (the docs' Last-updated style)."""
    y, m, d = (int(p) for p in iso.split('-'))
    return '%d %s %d' % (d, MONTHS[m - 1], y)


def render(s, version, date):
    """The public page (markdown) of summary S: small by design, no entry list. DATE (YYYY-MM-DD) is the index's
    own build date, stored with it, so render and check never read the clock."""
    out = ['# Items index: what can be picked up in the world', '',
           '_Last updated with AmiWind v%s (%s)._' % (version, long_date(date)), '',
           '_Generated from the game data by tools/items_index.py._', '',
           'Every item the player can pick up that the game\'s own records place in the world (not the contents of '
           'containers or what actors carry): its cell, position, item, kind and owner. The full index is a build '
           'output made from the player\'s own copy of the game; this page shows only its totals and a few '
           'notable entries. An item is owned when its placement names an owner or an owning faction: taking it '
           'is theft.', '',
           '- Placed items: %d, of which owned: %d (%s)' % (s['placed'], s['owned'], pct(s['owned'], s['placed'])),
           '- Different items: %d' % s['distinct_items'],
           '- Cells holding them: %d exterior, %d interior' % (s['exterior_cells'], s['interior_cells']),
           '- Left out: %d items in %d developer test cells the player cannot reach (an interior cell whose name '
           'contains "test", or one that no door leads to)' % (s['dropped_items'], s['dropped_cells']), '',
           '## By kind', '', '| Kind | Placed | Owned | Owned share |', '| --- | ---: | ---: | ---: |']
    out += ['| %s | %d | %d | %s |' % (k, n, o, pct(o, n)) for k, (n, o) in s['by_kind'].items()]
    out += ['', '## By region', '', 'Exterior cells by their region; every interior cell on one line.', '',
            '| Region | Placed | Owned | Owned share |', '| --- | ---: | ---: | ---: |']
    out += ['| %s | %d | %d | %s |' % (r, n, o, pct(o, n)) for r, (n, o) in s['by_region'].items()]

    def table(rows):
        lines = ['| Item | Kind | Value | Cell | Owned |', '| --- | --- | ---: | --- | --- |']
        lines += ['| %s (`%s`) | %s | %d | %s | %s |' % (r['item'], r['id'], r['kind'], r['value'], r['cell'],
                                                        'yes' if r['owned'] else 'no') for r in rows]
        return lines
    out += ['', '## Notable single items', '',
            '%d items are placed exactly once in the whole world (gold and keys left out); the %d most valuable:'
            % (s['single_placements'], len(s['notable_singles'])), ''] + table(s['notable_singles'])
    out += ['', '## Loose weapons outdoors', '',
            '%d weapons lie outdoors with no owner, free to take; the %d most valuable:'
            % (s['lone_weapons_outdoors'], len(s['notable_lone_weapons'])), ''] + table(s['notable_lone_weapons'])
    return '\n'.join(out) + '\n'


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('build')
    b.add_argument('--data-files', required=True, type=Path)
    b.add_argument('--out', required=True, type=Path)
    for name in ('render', 'check'):
        r = sub.add_parser(name)
        r.add_argument('--index', required=True, type=Path)
        r.add_argument('--doc', required=True, type=Path)
        # the release the page is written for (the repository's version file); passed in, so the build stage's
        # key never includes the version (tests/test_stage_version_key.py)
        r.add_argument('--release', required=True)
    a = p.parse_args()
    if a.cmd == 'build':
        build(a.data_files, a.out)
        return 0
    idx = json.loads(a.index.read_text(encoding='utf-8'))
    text = render(idx['summary'], a.release, idx['built'])
    if a.cmd == 'render':
        a.doc.write_text(text, encoding='utf-8', newline='\n')
        print('[items-index] wrote %s (%d bytes)' % (a.doc, len(text.encode('utf-8'))), flush=True)
        return 0
    current = a.doc.read_text(encoding='utf-8') if a.doc.is_file() else ''
    if current != text:
        print('[items-index] %s is not what render writes from %s' % (a.doc, a.index), flush=True)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
