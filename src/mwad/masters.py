# SPDX-License-Identifier: GPL-3.0-only
"""The one merging reader: the base game file plus the selected expansion masters, in load order, merged the way the
game merges them, as one standalone master that every existing reader can parse unchanged.

The rules (OpenMW 0.51, read for the logic only: apps/openmw/mwworld/store.cpp Store<T>::load, Store<ESM::Cell>::load
and handleMovedCellRefs, Store<ESM::Dialogue>::load, components/esm3/infoorder.hpp InfoOrder::insertInfo):
- a later record with the same id replaces the earlier one in place; a deleted one removes it;
- a cell merges by its grid position (exterior) or its name (interior): the later header's subrecords replace the
  earlier ones of the same tag, the references are added; a later reference with the same reference number (its owning
  file and index) replaces the earlier one, a deleted one removes it; a moved reference (MVRF + CNDT) leaves its old
  cell and joins the exterior cell CNDT names;
- a dialogue topic is reopened by a later DIAL of the same id; each INFO is inserted after its previous-response link
  (PNAM), at the front for an empty link, at the end for an unknown one; the same id with the same link replaces it in
  place; the merged responses are written with their PNAM / NNAM chain matching the merged order;
- land textures (LTEX) are numbered per file: a later file's are numbered after the earlier files' and its LAND VTEX
  indices follow them;
- reference numbers: a later file's FRMR names its owning file in the top byte (0 the file itself, k its k-th master,
  OpenMW components/esm3/loadcell.cpp adjustRefNum); the merged number is the owner's place in GAME_MASTERS x
  ADDON_KEY_STRIDE + the low bits, the key of tools/mwscript/gamedata.py, so the base game's numbers are unchanged;
- the TES3 header is the base file's, with the merged record count and no master list.

With only the base game file selected the result IS that file, byte for byte (master_bytes returns its bytes and
master_path its own path), so the base world's keys and outputs do not move.

The selected layers: selected_masters() (the environment variable AMIWIND_MASTERS, a comma list of master names in
load order, default the base game file alone). Every reader takes an explicit MASTERS list too.
"""
import hashlib
import os
import struct
from pathlib import Path

from .esm import GAME_MASTERS, DELETED_FLAG, FormatError, records, require, string, subrecords

BASE_MASTER = GAME_MASTERS[0]
ADDON_KEY_STRIDE = 1 << 22       # tools/mwscript/gamedata.py ADDON_KEY_STRIDE
MASTERS_ENV = 'AMIWIND_MASTERS'
FORMAT = 'aw-merged-master-1'    # part of the merged file's cache key: bump when the merge rules change


def selected_masters(value=None):
    """The selected masters in load order: VALUE (a list or a comma string), else AMIWIND_MASTERS, else the base game
    file alone. The base game file is always first; a name may appear once."""
    if value is None:
        value = os.environ.get(MASTERS_ENV, '')
    names = [n.strip() for n in value.split(',')] if isinstance(value, str) else [str(n).strip() for n in value]
    names = [n for n in names if n]
    if not names:
        return (BASE_MASTER,)
    require(names[0].casefold() == BASE_MASTER.casefold(), f'The first master must be {BASE_MASTER}, not {names[0]}')
    folded = [n.casefold() for n in names]
    require(len(set(folded)) == len(folded), f'A master is named twice: {", ".join(names)}')
    known = {m.casefold(): m for m in GAME_MASTERS}
    for n in names:
        require(n.casefold() in known, f'Unknown master {n} (the game masters are {", ".join(GAME_MASTERS)})')
    return tuple(known[n.casefold()] for n in names)


def is_base_only(masters):
    return len(masters) == 1


def _paths(data_files, masters):
    from .paths import child_ci
    return [(name, child_ci(Path(data_files), name)) for name in masters]


def master_bytes(data_files, masters=None):
    """The merged master of the selected MASTERS in DATA_FILES as bytes (the base file's own bytes when alone)."""
    masters = selected_masters(masters)
    paths = _paths(data_files, masters)
    if is_base_only(masters):
        return paths[0][1].read_bytes()
    return merge([(name, path.read_bytes()) for name, path in paths])


def master_path(data_files, masters=None, merged_dir=None):
    """A path to the merged master of the selected MASTERS in DATA_FILES: the base file's own path when alone, else a
    merged file named Morrowind.esm in a folder keyed by the inputs' SHA-256 (MERGED_DIR, default
    out/scratch/merged-masters/ of the source tree), written once and reused."""
    masters = selected_masters(masters)
    paths = _paths(data_files, masters)
    if is_base_only(masters):
        return paths[0][1]
    raws = [(name, path.read_bytes()) for name, path in paths]
    key = hashlib.sha256(FORMAT.encode())
    for name, raw in raws:
        key.update(name.casefold().encode() + b'\0' + hashlib.sha256(raw).digest())
    # never the system temp folder; no environment name of its own here either (an AMIWIND_* name in a stage's code
    # reach is keyed by tools/build_cache.py: only MASTERS_ENV is meant to key the stages that read the layers)
    root = Path(merged_dir) if merged_dir else Path(__file__).resolve().parents[2] / 'out' / 'scratch' / 'merged-masters'
    out = root / key.hexdigest()[:32] / BASE_MASTER
    if not out.is_file():
        out.parent.mkdir(parents=True, exist_ok=True)
        part = out.with_name(out.name + '.%d.part' % os.getpid())
        part.write_bytes(merge(raws))
        os.replace(part, out)
    return out


# --- the merge ----------------------------------------------------------------------------------------------------

def _sub(tag, data):
    return struct.pack('<4sI', tag.encode('ascii'), len(data)) + data


def _record(tag, unused, flags, payload):
    return struct.pack('<4sIII', tag.encode('ascii'), len(payload), unused, flags) + payload


def _raw_records(data):
    """(tag, unused, flags, payload) of every record (mwad.esm.records keeps no header word)."""
    pos = 0
    for tag, flags, payload in records(data):
        unused = struct.unpack_from('<I', data, pos + 8)[0]
        pos += 16 + len(payload)
        yield tag, unused, flags, payload


def _text(data):
    return string(data, errors='replace')


def _deleted(flags, subs):
    return bool(flags & DELETED_FLAG) or any(t == 'DELE' for t, _ in subs)


def _record_id(tag, subs):
    """The merge key of a non-cell, non-dialogue record, or None (kept as it comes)."""
    fields = {}
    for t, d in subs:
        fields.setdefault(t, d)
    if tag in ('SKIL', 'MGEF'):
        return (tag, bytes(fields.get('INDX', b''))) if 'INDX' in fields else None
    if tag == 'LAND':
        return (tag, bytes(fields['INTV'][:8])) if 'INTV' in fields else None
    if tag == 'PGRD':
        return (tag, _text(fields.get('NAME', b'')).casefold(), bytes(fields.get('DATA', b'')[:8]))
    if tag == 'SCPT':
        return (tag, _text(fields.get('SCHD', b'')[:32]).casefold()) if 'SCHD' in fields else None
    if 'NAME' in fields:
        return (tag, _text(fields['NAME']).casefold())
    return None


class _Cell:
    __slots__ = ('unused', 'flags', 'header', 'refs')

    def __init__(self, unused, flags, header):
        self.unused, self.flags, self.header = unused, flags, header
        self.refs = {}          # ref key -> [(tag, data)] (FRMR first, its number already the merged key)


def _cell_key(header):
    data = next((d for t, d in header if t == 'DATA'), b'')
    require(len(data) >= 12, 'CELL without a 12-byte DATA')
    bits, x, y = struct.unpack_from('<Iii', data)
    if bits & 1:
        return ('int', _text(next((d for t, d in header if t == 'NAME'), b'')).casefold())
    return ('ext', x, y)


def _split_cell(subs):
    """(header subrecords, [(moved target or None, [ref subrecords])]) of a CELL record. NAM0 is a header field
    wherever it stands."""
    header, blocks, current, target = [], [], None, None
    for tag, data in subs:
        if tag == 'MVRF':
            current = None
            target = 'pending'
            continue
        if tag == 'CNDT' and target == 'pending':
            target = struct.unpack('<ii', data[:8])
            continue
        if tag == 'FRMR':
            current = [(tag, data)]
            blocks.append((target if target != 'pending' else None, current))
            target = None
            continue
        if current is None or tag == 'NAM0':
            header.append((tag, data))
        else:
            current.append((tag, data))
    return header, blocks


class _Merge:
    def __init__(self):
        self.order = []            # merge keys in first-seen order
        self.entries = {}          # key -> ('rec', tag, unused, flags, payload) | _Cell | ('dial', ...)
        self.ref_cell = {}         # ref key -> cell key
        self.ltex_next = 0
        self.header = None

    def _put(self, key, value):
        if key not in self.entries:
            self.order.append(key)
        self.entries[key] = value

    def _drop(self, key):
        if key in self.entries:
            del self.entries[key]
            self.order.remove(key)

    def load(self, index, name, raw, masts):
        ltex_base = self.ltex_next
        dial = None
        loose = 0
        for tag, unused, flags, payload in _raw_records(raw):
            subs = list(subrecords(payload))
            if tag == 'TES3':
                if index == 0:
                    self.header = (unused, flags, subs)
                continue
            if tag == 'DIAL':
                dial = self._dial(unused, flags, subs)
                continue
            if tag == 'INFO':
                require(dial is not None, f'{name}: INFO before any DIAL')
                if dial is not False:
                    self._info(dial, unused, flags, subs)
                continue
            dial = None
            if tag == 'CELL':
                self._cell(index, name, unused, flags, subs, masts)
                continue
            if tag == 'LTEX':
                number = struct.unpack('<I', dict(subs)['INTV'][:4])[0]
                self.ltex_next = max(self.ltex_next, ltex_base + number + 1)
                if ltex_base:
                    subs = [(t, struct.pack('<I', struct.unpack('<I', d[:4])[0] + ltex_base) if t == 'INTV' else d)
                            for t, d in subs]
                    payload = b''.join(_sub(t, d) for t, d in subs)
                self._put(('LTEX', index, number), ('rec', tag, unused, flags, payload))
                continue
            if tag == 'LAND' and ltex_base:
                subs = [(t, struct.pack('<256H', *(v + ltex_base if v else 0 for v in struct.unpack('<256H', d)))
                         if t == 'VTEX' and len(d) == 512 else d) for t, d in subs]
                payload = b''.join(_sub(t, d) for t, d in subs)
            key = _record_id(tag, subs)
            if key is None:
                loose += 1
                key = ('loose', index, loose)
            if _deleted(flags, subs):
                self._drop(key)
            else:
                self._put(key, ('rec', tag, unused, flags, payload))

    # dialogue
    def _dial(self, unused, flags, subs):
        ident = _text(dict(subs).get('NAME', b'')).casefold()
        key = ('DIAL', ident)
        if _deleted(flags, subs):
            self._drop(key)
            return False
        old = self.entries.get(key)
        infos = old[4] if old else ([], {})
        self._put(key, ('dial', unused, flags, subs, infos))
        return infos

    def _info(self, infos, unused, flags, subs):
        order, deleted = infos
        fields = {}
        for t, d in subs:
            fields.setdefault(t, d)
        ident = _text(fields.get('INAM', b'')).casefold()
        prev = _text(fields.get('PNAM', b'')).casefold()
        item = (ident, prev, unused, flags, subs)
        deleted[ident] = _deleted(flags, subs)
        at = next((i for i, it in enumerate(order) if it[0] == ident), None)
        if at is not None and order[at][1] == prev:
            order[at] = item
            return
        if at is not None:
            del order[at]
        if not prev:
            where = 0
        else:
            where = next((i + 1 for i, it in enumerate(order) if it[0] == prev), len(order))
        order.insert(where, item)

    # cells
    def _ref_key(self, index, number, masts):
        top, low = number >> 24, number & 0xFFFFFF
        if top == 0:
            owner = index
        else:
            require(top <= len(masts), f'Reference {number:#x} names master {top} of {len(masts)}')
            owner = next((i for i, m in enumerate(self.names) if m.casefold() == masts[top - 1].casefold()), None)
            require(owner is not None, f'Reference {number:#x} names {masts[top - 1]}, not loaded')
        require(low < ADDON_KEY_STRIDE or GAME_MASTERS.index(self.names[owner]) == 0,
                f'Reference number {low} past the key stride')
        return GAME_MASTERS.index(self.names[owner]) * ADDON_KEY_STRIDE + low

    def _cell_entry(self, key, unused, flags, header):
        cell = self.entries.get(key)
        if cell is None:
            cell = _Cell(unused, flags, list(header))
            self._put(key, cell)
            return cell
        cell.unused, cell.flags = unused, flags
        for tag, data in header:
            at = next((i for i, (t, _) in enumerate(cell.header) if t == tag), None)
            if at is None:
                cell.header.append((tag, data))
            else:
                cell.header[at] = (tag, data)
        return cell

    def _cell(self, index, name, unused, flags, subs, masts):
        header, blocks = _split_cell(subs)
        key = _cell_key(header)
        if _deleted(flags, header):
            old = self.entries.get(key)
            if isinstance(old, _Cell):
                for ref in old.refs:
                    self.ref_cell.pop(ref, None)
            self._drop(key)
            return
        cell = self._cell_entry(key, unused, flags & ~DELETED_FLAG, header)
        for target, block in blocks:
            ref = self._ref_key(index, struct.unpack('<I', block[0][1][:4])[0], masts)
            block = [('FRMR', struct.pack('<I', ref))] + block[1:]
            home = key
            if target is not None:
                home = ('ext', target[0], target[1])
                if home not in self.entries:
                    self._put(home, _Cell(0, 0, [('NAME', b'\0'), ('DATA', struct.pack('<Iii', 2, *target))]))
            old_home = self.ref_cell.get(ref)
            if old_home is not None and old_home != home and isinstance(self.entries.get(old_home), _Cell):
                self.entries[old_home].refs.pop(ref, None)
            target_cell = self.entries[home]
            if any(t == 'DELE' for t, _ in block):
                target_cell.refs.pop(ref, None)
                self.ref_cell.pop(ref, None)
            else:
                target_cell.refs[ref] = block
                self.ref_cell[ref] = home

    # output
    def write(self):
        require(self.header is not None, 'The base master has no TES3 header')
        body, count = [], 0
        for key in self.order:
            entry = self.entries[key]
            if isinstance(entry, _Cell):
                payload = b''.join(_sub(t, d) for t, d in entry.header)
                payload += b''.join(_sub(t, d) for block in entry.refs.values() for t, d in block)
                body.append(_record('CELL', entry.unused, entry.flags, payload))
                count += 1
            elif entry[0] == 'dial':
                _, unused, flags, subs, (order, deleted) = entry
                body.append(_record('DIAL', unused, flags, b''.join(_sub(t, d) for t, d in subs)))
                count += 1
                kept = [it for it in order if not deleted.get(it[0])]
                for i, (ident, _, iu, iflags, isubs) in enumerate(kept):
                    prev = kept[i - 1][4] if i else None
                    nxt = kept[i + 1][4] if i + 1 < len(kept) else None
                    rebuilt = []
                    for t, d in isubs:
                        if t == 'PNAM':
                            d = dict(prev).get('INAM', b'\0') if prev else b'\0'
                        elif t == 'NNAM':
                            d = dict(nxt).get('INAM', b'\0') if nxt else b'\0'
                        rebuilt.append((t, d))
                    body.append(_record('INFO', iu, iflags, b''.join(_sub(t, d) for t, d in rebuilt)))
                    count += 1
            else:
                _, tag, unused, flags, payload = entry
                body.append(_record(tag, unused, flags, payload))
                count += 1
        unused, flags, subs = self.header
        head = []
        for t, d in subs:
            if t == 'MAST' or t == 'DATA':
                continue
            if t == 'HEDR':
                require(len(d) >= 300, 'TES3 HEDR shorter than 300 bytes')
                d = d[:296] + struct.pack('<I', count) + d[300:]
            head.append((t, d))
        return _record('TES3', unused, flags, b''.join(_sub(t, d) for t, d in head)) + b''.join(body)


def merge(files):
    """One standalone master from FILES, [(master name, bytes)] in load order (the base game file first)."""
    require(files, 'No master to merge')
    names = selected_masters([n for n, _ in files])
    m = _Merge()
    m.names = names
    for index, (name, raw) in enumerate(files):
        masts = []
        for tag, _, _, payload in _raw_records(raw):
            if tag == 'TES3':
                masts = [_text(d) for t, d in subrecords(payload) if t == 'MAST']
            break
        if index == 0:
            require(not masts, f'{name} lists masters: the base game file must be standalone')
        m.load(index, name, raw, masts)
    return m.write()


__all__ = ['ADDON_KEY_STRIDE', 'BASE_MASTER', 'FormatError', 'master_bytes', 'master_path', 'merge',
           'selected_masters']
