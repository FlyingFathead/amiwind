# SPDX-License-Identifier: GPL-3.0-only
"""What the script compiler reads from the game data: scripts, globals, sounds, start scripts, the records that
carry a script and the placed references of those records.

Masters load in order (Morrowind, Tribunal, Bloodmoon); a later master's record with the same id replaces the
earlier one, as in the game. Placed references are read from Morrowind.esm (Vvardenfell, the world the image has);
the add-ons' references are counted, not bound (their reference numbers need the add-on's load-order index).
"""
import hashlib
import struct
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from mwad.esm import records, subrecords, string  # noqa: E402

MASTERS = ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')
# Record types that may name a script (SCRI) and be placed in a cell.
SCRIPTED = ('ACTI', 'ALCH', 'APPA', 'ARMO', 'BOOK', 'CLOT', 'CONT', 'CREA', 'DOOR', 'INGR', 'LIGH', 'LOCK', 'MISC',
            'NPC_', 'PROB', 'REPA', 'WEAP', 'STAT')


def _text(data):
    return string(data, errors='replace')


def _deleted(flags, parts):
    return bool(flags & 0x20) or any(t == 'DELE' for t, _ in parts)


class Script:
    __slots__ = ('id', 'master', 'text', 'source_bytes', 'original_bytes', 'counts', 'local_names', 'sha256')

    def __init__(self, ident, master, text, source_bytes, original_bytes, counts, local_names):
        self.id, self.master, self.text = ident, master, text
        self.source_bytes, self.original_bytes = source_bytes, original_bytes
        self.counts, self.local_names = counts, local_names
        self.sha256 = hashlib.sha256(text.encode('cp1252', 'replace')).hexdigest()


class GameData:
    def __init__(self):
        self.scripts = {}          # folded id -> Script (the winning record)
        self.scripts_by_master = {m: [] for m in MASTERS}   # every SCPT record each master holds
        self.globals = {}          # folded name -> (type letter, initial value, spelling)
        self.sounds = {}           # folded SOUN id -> {'id', 'file', 'volume', 'min', 'max', 'master'}
        self.start_scripts = []    # folded script ids (SSCR), in order
        self.bases = {}            # folded record id -> (type, folded script id)
        self.references = []       # Morrowind.esm placed refs whose base has a script
        self.reference_counts = {m: 0 for m in MASTERS}     # placed scripted references per master
        self.object_refs = {}      # folded base id -> [reference numbers] (Morrowind.esm, every placed ref)
        self.cells = []            # interior cell names (folded) in first-seen order
        self.master_sha256 = {}
        self.gmst = {}             # folded float game settings
        self.interior_ids = []     # [(master, [interior cell ids])] (tools/cell_numbers.py)
        self.interior_numbers = {} # folded interior cell id -> its stable number (_aw_cell_int)

    def sound_range(self, soun):
        """(min, max) hearing distance of a SOUN record in game units: its bytes times the game settings
        fAudioMinDistanceMult/fAudioMaxDistanceMult, the defaults when both are 0 (rule from OpenMW
        apps/openmw/mwsound/soundbuffer.cpp; the values are the game data's own GMSTs)."""
        g = self.gmst
        lo, hi = (soun['min'], soun['max']) if soun else (0, 0)
        if lo == 0 and hi == 0:
            lo, hi = g.get('faudiodefaultmindistance', 5.0), g.get('faudiodefaultmaxdistance', 40.0)
        lo *= g.get('faudiomindistancemult', 20.0)
        hi *= g.get('faudiomaxdistancemult', 50.0)
        return int(round(lo)), int(round(max(lo, hi)))

    def load(self, data_files, masters=MASTERS):
        from mwad.paths import child_ci
        for name in masters:
            path = child_ci(Path(data_files), name, required=False)
            if path is None:
                continue
            raw = path.read_bytes()
            self.master_sha256[name] = hashlib.sha256(raw).hexdigest()
            self._master(name, raw)
            from cell_numbers import interior_cell_ids
            self.interior_ids.append((name, interior_cell_ids(raw)))
        from cell_numbers import number_cells
        # the stable interior numbers the builder stamps into each room map (_aw_cell_int, tools/cell_numbers.py)
        self.interior_numbers = {r['cell'].casefold(): r['number'] for r in number_cells(self.interior_ids)}
        return self

    def _master(self, master, raw):
        pending_refs = []
        for tag, flags, payload in records(raw):
            if tag == 'SCPT':
                parts = list(subrecords(payload))
                fields = dict(parts)
                head = fields.get('SCHD', b'')
                ident = _text(head[:32])
                counts = struct.unpack_from('<5I', head, 32) if len(head) >= 52 else (0, 0, 0, 0, 0)
                names = [n for n in fields.get('SCVR', b'').split(b'\0') if n]
                text = (fields.get('SCTX') or b'').decode('cp1252', 'replace')
                if _deleted(flags, parts):
                    self.scripts.pop(ident.casefold(), None)
                    continue
                s = Script(ident, master, text, len(fields.get('SCTX') or b''), len(fields.get('SCDT') or b''),
                           counts, [n.decode('cp1252', 'replace') for n in names])
                self.scripts[ident.casefold()] = s
                self.scripts_by_master[master].append(s)
            elif tag == 'GLOB':
                parts = list(subrecords(payload)); fields = dict(parts)
                name = _text(fields.get('NAME', b''))
                if _deleted(flags, parts):
                    self.globals.pop(name.casefold(), None); continue
                kind = _text(fields.get('FNAM', b'f'))[:1] or 'f'
                value = struct.unpack('<f', fields['FLTV'])[0] if len(fields.get('FLTV', b'')) == 4 else 0.0
                self.globals[name.casefold()] = (kind if kind in 'slf' else 'f', value, name)
            elif tag == 'SOUN':
                parts = list(subrecords(payload)); fields = dict(parts)
                ident = _text(fields.get('NAME', b''))
                if _deleted(flags, parts):
                    self.sounds.pop(ident.casefold(), None); continue
                data = fields.get('DATA', b'\0\0\0')
                self.sounds[ident.casefold()] = {'id': ident, 'file': _text(fields.get('FNAM', b'')),
                                                 'volume': data[0], 'min': data[1] if len(data) > 1 else 0,
                                                 'max': data[2] if len(data) > 2 else 0, 'master': master}
            elif tag == 'GMST':
                fields = dict(subrecords(payload))
                name = _text(fields.get('NAME', b''))
                if len(fields.get('FLTV', b'')) == 4:
                    self.gmst[name.casefold()] = struct.unpack('<f', fields['FLTV'])[0]
            elif tag == 'SSCR':
                fields = dict(subrecords(payload))
                ident = _text(fields.get('NAME', b'')).casefold()
                if ident and ident not in self.start_scripts:
                    self.start_scripts.append(ident)
            elif tag in SCRIPTED:
                parts = list(subrecords(payload)); fields = dict(parts)
                ident = _text(fields.get('NAME', b''))
                if _deleted(flags, parts):
                    self.bases.pop(ident.casefold(), None); continue
                self.bases[ident.casefold()] = (tag, _text(fields.get('SCRI', b'')).casefold())
            elif tag == 'CELL':
                pending_refs.append(payload)
        for payload in pending_refs:
            self._cell(master, payload)

    def _cell(self, master, payload):
        parts = list(subrecords(payload))
        head = {}
        refs, ref, moved = [], None, False
        for tag, data in parts:
            if tag == 'MVRF':
                moved = True; ref = None; continue
            if tag == 'FRMR':
                if moved:
                    moved = False
                ref = {'number': struct.unpack('<I', data)[0]}
                refs.append(ref); continue
            if ref is None:
                head.setdefault(tag, data); continue
            if tag == 'NAME':
                ref['id'] = _text(data)
            elif tag == 'DATA' and len(data) == 24:
                ref['position'] = list(struct.unpack('<6f', data)[:3])
            elif tag == 'DELE':
                ref['deleted'] = True
        cell_flags, gx, gy = struct.unpack('<Iii', head['DATA']) if len(head.get('DATA', b'')) == 12 else (0, 0, 0)
        interior = bool(cell_flags & 1)
        cell_name = _text(head.get('NAME', b''))
        for r in refs:
            if r.get('deleted') or 'id' not in r:
                continue
            base = self.bases.get(r['id'].casefold())
            if master == 'Morrowind.esm':
                self.object_refs.setdefault(r['id'].casefold(), []).append(r['number'])
            if not base or not base[1]:
                continue
            self.reference_counts[master] += 1
            if master != 'Morrowind.esm':
                continue
            pos = r.get('position', [0.0, 0.0, 0.0])
            self.references.append({'reference': r['number'], 'id': r['id'], 'type': base[0], 'script': base[1],
                                    'interior': interior, 'cell': cell_name if interior else (gx, gy),
                                    'position': pos})
