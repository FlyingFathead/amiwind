# SPDX-License-Identifier: GPL-3.0-only
"""Interior cells that behave like an exterior, presented as exterior cells of their own.

Tribunal's Mournhold has five outdoor districts (Godsreach, the Great Bazaar, Plaza Brindisi Dorom, the Royal Palace
courtyard and the Temple courtyard). In the game data they are interior cells with the "behave like exterior" flag:
each has its own coordinates, no terrain, and doors instead of neighbours. The outdoor converter reads a square of
exterior grid cells, so this tool writes a PRESENTED master: a copy of a master (the merged master of the selected
game files) in which each such cell is an exterior cell block of its own, far from every island and from the other
blocks, with

- its placements moved by one offset (x and y; heights are kept) and split over the grid cells of its block;
- every door or marker destination that names the cell, in any cell, turned into an exterior destination at the
  moved position;
- the cell's own interior record left out.

Everything else is copied byte for byte, in order. A master without such a cell is returned unchanged (the same
bytes), so the base game alone is never touched. The blocks come from config/presented-exteriors.json (the first
block, the spacing) and the cells' names in sorted order, so the same game files always give the same places.

The receipt (JSON) lists, per cell: its block, its offset, its box before the move, and the counts; the stages that
move the player to such a cell by name (a script's PositionCell) read their position from it.

    python3 tools/presented_exterior.py --master MERGED.esm --out PRESENTED.esm --receipt RECEIPT.json
"""
import argparse
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT / 'tools', ROOT / 'src'):
    while str(_p) in sys.path:
        sys.path.remove(str(_p))
    sys.path.insert(0, str(_p))

from mwad.esm import records, subrecords  # noqa: E402

FORMAT = 'aw-presented-exterior-1'
CONFIG = ROOT / 'config' / 'presented-exteriors.json'
CELL_UNITS = 8192
INTERIOR = 0x01
BEHAVES_EXTERIOR = 0x80


def load_config(path=CONFIG):
    """{first_block: [x, y], spacing: cells between block origins along x, max_block: the largest block side}."""
    value = json.loads(Path(path).read_text(encoding='utf-8'))
    if value.get('format') != FORMAT:
        raise ValueError('%s: format is not %s' % (path, FORMAT))
    first, spacing, largest = value['first_block'], int(value['spacing']), int(value['max_block'])
    if len(first) != 2 or spacing <= largest or largest < 1:
        raise ValueError('%s: the spacing must be wider than the largest block, so blocks never touch' % path)
    return {'first_block': [int(first[0]), int(first[1])], 'spacing': spacing, 'max_block': largest}


def _sub(tag, data):
    return struct.pack('<4sI', tag.encode('ascii'), len(data)) + data


def _record(tag, flags, payload):
    return struct.pack('<4sIII', tag.encode('ascii'), len(payload), 0, flags) + payload


def _raw_records(master):
    """(tag, flags, payload, the record's own bytes) of every record, so an untouched record is copied as it is."""
    pos = 0
    for tag, flags, payload in records(master):
        end = pos + 16 + len(payload)
        yield tag, flags, payload, bytes(master[pos:end])
        pos = end


def _text(data):
    return bytes(data).split(b'\0', 1)[0].decode('cp1252')


def _split(payload):
    """(header subrecords, [reference subrecord groups]) of a CELL payload; a group starts at FRMR (or at the MVRF
    that precedes it)."""
    head, groups, current = [], [], None
    for tag, data in subrecords(payload):
        if tag in ('FRMR', 'MVRF') and not (current and current[-1][0] == 'MVRF' and tag == 'FRMR'):
            current = []
            groups.append(current)
        (head if current is None else current).append((tag, bytes(data)))
    return head, groups


def _field(subs, tag):
    return next((d for t, d in subs if t == tag), None)


def flagged_cells(master):
    """{folded name: {name, flags, head, groups, low, high}} of the interior cells with the exterior-behaviour flag
    that hold at least one placement with a position."""
    found = {}
    for tag, flags, payload in records(master):
        if tag != 'CELL':
            continue
        head, groups = _split(payload)
        data = _field(head, 'DATA')
        if data is None or len(data) != 12:
            continue
        bits = struct.unpack_from('<I', data)[0]
        if not (bits & INTERIOR and bits & BEHAVES_EXTERIOR):
            continue
        name = _text(_field(head, 'NAME') or b'')
        spots = [struct.unpack('<6f', d)[:3] for g in groups for t, d in g if t == 'DATA' and len(d) == 24]
        if not spots:
            continue
        if name.casefold() in found:
            raise ValueError('Two exterior-like cells named %r' % name)
        found[name.casefold()] = {
            'name': name, 'flags': bits, 'head': head, 'groups': groups,
            'low': [min(s[i] for s in spots) for i in range(3)], 'high': [max(s[i] for s in spots) for i in range(3)]}
    return found


def plan(cells, config):
    """The block and the offset of every flagged cell, by sorted name: {folded name: {block, size, offset}}. A block
    is the smallest whole number of grid cells that holds the cell's box; the box is centred in it."""
    out = {}
    x0, y0 = config['first_block']
    for i, key in enumerate(sorted(cells)):
        cell = cells[key]
        size = [max(1, math.ceil((cell['high'][a] - cell['low'][a]) / CELL_UNITS)) for a in (0, 1)]
        if max(size) > config['max_block']:
            raise ValueError('%s spans %d x %d cells, more than the largest block (%d): raise max_block and spacing '
                             'in config/presented-exteriors.json' % (cell['name'], size[0], size[1], config['max_block']))
        block = [x0 + i * config['spacing'], y0]
        offset = [(block[a] + size[a] / 2) * CELL_UNITS - (cell['low'][a] + cell['high'][a]) / 2 for a in (0, 1)]
        out[key] = {'block': block, 'size': size, 'offset': [float(round(v)) for v in offset]}
    return out


def _moved_group(group, offset, places):
    """A reference's subrecords with its position moved by OFFSET and, when its door destination names a presented
    cell, that destination made an exterior one at its moved position. (new subrecords, grid cell or None)."""
    out, cell = [], None
    target = _field(group, 'DNAM')
    target = places.get(_text(target).casefold()) if target is not None else None
    for tag, data in group:
        if tag == 'DATA' and len(data) == 24 and offset is not None:
            v = list(struct.unpack('<6f', data))
            v[0] += offset[0]
            v[1] += offset[1]
            cell = (math.floor(v[0] / CELL_UNITS), math.floor(v[1] / CELL_UNITS))
            data = struct.pack('<6f', *v)
        elif tag == 'DODT' and len(data) == 24 and target is not None:
            v = list(struct.unpack('<6f', data))
            v[0] += target['offset'][0]
            v[1] += target['offset'][1]
            data = struct.pack('<6f', *v)
        elif tag == 'DNAM' and target is not None:
            continue                                    # an exterior destination has no cell name
        out.append((tag, data))
    return out, cell


def _payload(head, groups):
    return b''.join(_sub(t, d) for t, d in head) + b''.join(_sub(t, d) for g in groups for t, d in g)


def present(master, config=None):
    """(presented master bytes, receipt) of MASTER (bytes). Without an exterior-like cell: MASTER itself."""
    config = config or load_config()
    cells = flagged_cells(master)
    receipt = {'format': FORMAT, 'config': config, 'source_sha256': hashlib.sha256(master).hexdigest(), 'cells': []}
    if not cells:
        receipt['presented_sha256'] = receipt['source_sha256']
        return master, receipt
    places = plan(cells, config)
    taken = set()
    for tag, flags, payload in records(master):
        if tag == 'CELL' or tag == 'LAND':
            for key, data in subrecords(payload):
                if tag == 'CELL' and key == 'DATA' and len(data) == 12:
                    bits, x, y = struct.unpack('<Iii', data)
                    if not bits & INTERIOR:
                        taken.add((x, y))
                    break
                if tag == 'LAND' and key == 'INTV' and len(data) == 8:
                    taken.add(struct.unpack('<ii', data))
                    break
    blocks = {}
    for key, place in places.items():
        for dx in range(-1, place['size'][0] + 1):          # the block and a ring of one cell around it stay free
            for dy in range(-1, place['size'][1] + 1):
                spot = (place['block'][0] + dx, place['block'][1] + dy)
                if spot in taken:
                    raise ValueError('The block of %s touches the game\'s own exterior cell %d,%d: move first_block '
                                     'in config/presented-exteriors.json' % (cells[key]['name'], spot[0], spot[1]))
                if blocks.setdefault(spot, key) != key:
                    raise ValueError('The blocks of %s and %s touch' % (cells[key]['name'], cells[blocks[spot]]['name']))
    out, added, rewired = [], 0, 0          # out: raw record bytes, or (tag, flags, payload) for a written record
    header = None
    for tag, flags, payload, raw in _raw_records(master):
        if tag == 'TES3' and header is None:
            header = len(out)
            out.append((tag, flags, payload))
            continue
        if tag != 'CELL':
            out.append(raw)
            continue
        head, groups = _split(payload)
        name = _text(_field(head, 'NAME') or b'')
        data = _field(head, 'DATA')
        bits = struct.unpack_from('<I', data)[0] if data is not None and len(data) == 12 else 0
        if bits & INTERIOR and name.casefold() in places:
            continue                                        # written below as exterior cells
        if not any(_field(g, 'DNAM') is not None and _text(_field(g, 'DNAM')).casefold() in places for g in groups):
            out.append(raw)                                 # untouched: the same bytes
            continue
        new = []
        for g in groups:
            moved, _ = _moved_group(g, None, places)
            rewired += moved != g
            new.append(moved)
        out.append((tag, flags, _payload(head, new)))
    for key in sorted(places):
        cell, place = cells[key], places[key]
        per_cell = {}
        inner_rewired = 0
        for g in cell['groups']:
            moved, spot = _moved_group(g, place['offset'], places)
            if spot is None:
                spot = tuple(place['block'])                # a reference without a position stays with the block
            target = _field(g, 'DNAM')
            inner_rewired += target is not None and _text(target).casefold() in places
            per_cell.setdefault(spot, []).append(moved)
        for spot in per_cell:
            if not (place['block'][0] <= spot[0] < place['block'][0] + place['size'][0]
                    and place['block'][1] <= spot[1] < place['block'][1] + place['size'][1]):
                raise ValueError('A placement of %s falls outside its block' % cell['name'])
        keep = [(t, d) for t, d in cell['head'] if t not in ('DATA', 'NAM0', 'AMBI', 'WHGT', 'INTV')]
        flags_out = cell['flags'] & ~(INTERIOR | BEHAVES_EXTERIOR)
        for dx in range(place['size'][0]):
            for dy in range(place['size'][1]):
                spot = (place['block'][0] + dx, place['block'][1] + dy)
                head = []
                for t, d in keep:
                    head.append((t, d))
                    if t == 'NAME':
                        head.append(('DATA', struct.pack('<Iii', flags_out, spot[0], spot[1])))
                out.append(('CELL', 0, _payload(head, per_cell.get(spot, []))))
                added += 1
        rewired += inner_rewired
        receipt['cells'].append({
            'cell': cell['name'], 'block': place['block'], 'size': place['size'], 'offset': place['offset'],
            'box_low': [round(v, 3) for v in cell['low']], 'box_high': [round(v, 3) for v in cell['high']],
            'placements': len(cell['groups']), 'destinations_rewritten_inside': inner_rewired})
    if header is None:
        raise ValueError('The master has no TES3 header record')
    tag, flags, payload = out[header]
    subs = [(t, bytes(d)) for t, d in subrecords(payload)]
    count = len(out) - 1
    fixed = []
    for t, d in subs:
        if t == 'HEDR' and len(d) == 300:
            d = d[:296] + struct.pack('<I', count)
        fixed.append((t, d))
    out[header] = (tag, flags, b''.join(_sub(t, d) for t, d in fixed))
    result = b''.join(r if isinstance(r, bytes) else _record(*r) for r in out)
    receipt.update({'exterior_cells_written': added, 'destinations_rewritten': rewired,
                    'presented_sha256': hashlib.sha256(result).hexdigest()})
    return result, receipt


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    p.add_argument('--master', required=True, help='the master to present (the merged master of the selected files)')
    p.add_argument('--out', required=True, help='the presented master to write (a new file)')
    p.add_argument('--receipt', required=True, help='the receipt to write (JSON)')
    p.add_argument('--config', default=str(CONFIG))
    a = p.parse_args(argv)
    out = Path(a.out)
    if out.exists():
        p.error('%s exists: existing data is never overwritten' % out)
    result, receipt = present(Path(a.master).read_bytes(), load_config(a.config))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(result)
    Path(a.receipt).write_text(json.dumps(receipt, indent=1) + '\n', encoding='utf-8', newline='\n')
    for row in receipt['cells']:
        print('%s: block %d,%d (%d x %d cells), offset %.0f %.0f, %d placements' % (
            row['cell'], row['block'][0], row['block'][1], row['size'][0], row['size'][1], row['offset'][0],
            row['offset'][1], row['placements']))
    print('presented %d cell(s): %d exterior cells written, %d destinations rewritten' % (
        len(receipt['cells']), receipt.get('exterior_cells_written', 0), receipt.get('destinations_rewritten', 0)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
