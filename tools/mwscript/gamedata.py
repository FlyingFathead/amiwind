# SPDX-License-Identifier: GPL-3.0-only
"""What the script compiler reads from the game data: scripts, globals, sounds, start scripts, the records that
carry a script and the placed references of those records.

Masters load in order (Morrowind, Tribunal, Bloodmoon); a later master's record with the same id replaces the
earlier one, as in the game. Placed references are read from Morrowind.esm (Vvardenfell, the world the image has);
the add-ons' own placements are keyed by their load-order index (addon_key, since v0.0.63) and kept apart
(addon_references): an image binds them only for the add-on worlds it carries (compiler.bindings ADDONS).
"""
import hashlib
import re
import struct
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from mwad.esm import records, subrecords, string  # noqa: E402
from mwad.dialogue import conditions as dialogue_conditions  # noqa: E402

MASTERS = ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')
# MWSCRIPT-ADDON-ATTACH-62 (v0.0.63): an add-on placement's reference key = its file's place in MASTERS x this + its
# number: 2^22 keeps three masters' keys below 2^24, exact in the engine's float aw_ref (the masters' numbers are far
# below 2^22); Morrowind.esm's keys are its numbers, unchanged. The world builder stamps the same key when it converts
# Mournhold or Solstheim.
ADDON_KEY_STRIDE = 1 << 22
# The global script the game always runs (OpenMW 0.51 apps/openmw/mwscript/globalscripts.cpp GlobalScripts::addStartup
# adds "main" before the masters' start scripts). A new game sets CharGenState to 1 (OpenMW mwworld/worldimp.cpp
# startNewGame); Main's block under that test starts the new game's run-once scripts (Startup, whose ->Disable lines
# take the Dreamers, the falling mage and the quest characters out of the world, and VampireCheck).
MAIN_SCRIPT = 'main'
_TARGET = r'(?:"([^"]+)"|([^\s"]+))'
_START = re.compile(r'^startscript[\s,]+' + _TARGET + r'$', re.I)
_DISABLE = re.compile(r'^' + _TARGET + r'\s*->\s*disable$', re.I)
_NEW_GAME_TEST = re.compile(r'^if\s*\(?\s*chargenstate\s*==\s*1\s*\)?$', re.I)


def _statements(text):
    """The script's statements: comments cut, blanks dropped, spaces folded."""
    out = []
    for line in (text or '').splitlines():
        line = re.sub(r'\s+', ' ', line.split(';', 1)[0]).strip()
        if line:
            out.append(line)
    return out


def _target(match):
    return (match.group(1) or match.group(2)).strip()


def new_game_scripts(text):
    """The folded names Main starts inside its `if ( CharGenState == 1 )` block (any depth inside it), in order:
    the scripts a new game starts once. [] when Main has no such block."""
    names, depth, inside = [], 0, None
    for line in _statements(text):
        low = line.casefold()
        if re.match(r'^if\b', low):
            depth += 1
            if inside is None and _NEW_GAME_TEST.match(line):
                inside = depth
            continue
        if re.match(r'^endif\b', low):
            if inside is not None and depth == inside:
                inside = None
            depth = max(0, depth - 1)
            continue
        match = _START.match(line)
        if inside is not None and match and _target(match).casefold() not in names:
            names.append(_target(match).casefold())
    return names


_WEATHER = re.compile(r'^changeweather[\s,]+' + _TARGET + r'[\s,]+(\d+)$', re.I)


def new_game_weather(text):
    """[(folded region, weather)] of a script's ChangeWeather lines with a constant weather, in order (v0.0.63,
    OPENING-WEATHER-NOT-CLOUDY-63: CharGen's "ChangeWeather Bitter Coast Region 1", which AmiWind's own opening carries)."""
    out = []
    for line in _statements(text):
        m = _WEATHER.match(line)
        if m:
            out.append((_target(m).casefold(), int(m.group(3))))
    return out


def unconditional_disables(text):
    """The folded ids of a script's `ID->Disable` lines outside every if block, in order (what a run-once script such
    as Startup always disables)."""
    out, depth = [], 0
    for line in _statements(text):
        low = line.casefold()
        if re.match(r'^if\b', low):
            depth += 1
        elif re.match(r'^endif\b', low):
            depth = max(0, depth - 1)
        elif depth == 0:
            match = _DISABLE.match(line)
            if match and _target(match).casefold() not in out:
                out.append(_target(match).casefold())
    return out
# Record types that may name a script (SCRI) and be placed in a cell.
SCRIPTED = ('ACTI', 'ALCH', 'APPA', 'ARMO', 'BOOK', 'CLOT', 'CONT', 'CREA', 'DOOR', 'INGR', 'LIGH', 'LOCK', 'MISC',
            'NPC_', 'PROB', 'REPA', 'WEAP', 'STAT')
# The placements events.py reads: the actors and the objects an actor can stand on.
PLACEMENT_TYPES = ('NPC_', 'CREA', 'ACTI', 'STAT', 'CONT', 'DOOR')
# The records that hold items (NPCO): their items' scripts run while the holder's area is loaded (bindings, BIND_HELD)
HOLDERS = ('CONT', 'NPC_', 'CREA')
# Records kept whole for the actor table (actors.py): the actors, what their stats come from, what they carry.
RECORD_TAGS = ('NPC_', 'CREA', 'RACE', 'CLAS', 'SKIL', 'WEAP', 'ARMO', 'CLOT', 'LEVI', 'SPEL', 'FACT', 'GMST',
               'ALCH', 'APPA', 'BOOK', 'INGR', 'LIGH', 'LOCK', 'MISC', 'PROB', 'REPA', 'MGEF', 'ENCH')


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
        self.new_game = []         # folded script ids Main starts when a new game begins (new_game_scripts)
        self.bases = {}            # folded record id -> (type, folded script id)
        self.references = []       # Morrowind.esm placed refs whose base has a script (its final one; load())
        self._placed_mw = []       # every Morrowind.esm placed ref with a record, bound after the last master
        self._placed_addon = []    # the add-ons' own placed refs with a record (MWSCRIPT-ADDON-ATTACH-62)
        self.addon_references = []  # those whose record has a script, keyed by load order (load(), addon_key)
        self.addon_refs_unkeyed = 0  # add-on placements whose file is not loaded or whose number is too large
        self.master_lists = {}     # master -> its own MAST list (the TES3 header)
        self.reference_counts = {m: 0 for m in MASTERS}     # placed scripted references per master
        self.object_refs = {}      # folded base id -> [reference numbers] (Morrowind.esm, every placed ref)
        # the cell each placed actor (an NPC_ or CREA reference of Morrowind.esm) stands in: reference number -> the
        # folded interior cell id, or None outdoors (PositionCell's visitors, codegen.Program.visitor)
        self.actor_cells = {}
        self.object_cells = {}     # any other placed object's interior cell: reference number -> folded cell id
        # Morrowind.esm placed actors and the objects they can stand on (events.py, SCRIPTED-EVENT-FALLING-MAGE-61):
        # reference number -> (base type, folded id, cell, x, y, z in game units)
        self.placements = {}
        self.cells = []            # interior cell names (folded) in first-seen order
        self.master_sha256 = {}
        self.gmst = {}             # folded float game settings
        self.interior_ids = []     # [(master, [interior cell ids])] (tools/cell_numbers.py)
        self.interior_numbers = {} # folded interior cell id -> its stable number (_aw_cell_int)
        self.exteriors = {}        # (x, y) -> (cell name, folded region id) of every exterior CELL record
        self.regions = {}          # folded REGN id -> its name
        self.topics = {}           # folded DIAL topic id (type 0) -> its name
        # the dialogue's result scripts (INFO BNAM) with the speaker each names (ONAM, folded; '' any speaker), in
        # first-seen order: compiled as scripts of their own (compiler.py, DIALOGUE-COMPLETE-58)
        self.results = {}
        self.default_cell_name = 'Wilderness'   # GMST sDefaultCellname: an exterior with no name and no region
        # the records the actor table reads (tools/mwscript/actors.py): {tag: {folded id: [(sub, data)]}}, the last
        # master wins; SKIL by its INDX number; a deleted record removes the earlier one
        self.records = {tag: {} for tag in RECORD_TAGS}
        self.levelled_lists = {}   # folded LEVC id -> [folded ids it names] (MWSCRIPT-UNPLACED-ATTACH-62)
        # MWSCRIPT-INVENTORY-HITONME-62: what each container, NPC and creature record holds (NPCO, the last master's
        # record wins): folded holder id -> [folded item ids] in record order; and the Morrowind.esm placed references
        # of those three types: [{'reference', 'id' (folded), 'type', 'interior', 'cell', 'position'}]
        self.holdings = {}
        self.holder_refs = []
        # MWSCRIPT-INERT-SEEN-62: the folded local names the dialogue's Local and NotLocal filters read (from the
        # speaker's script, at run time): a script setting one is not inert (compiler.dialogue_read_slots)
        self.dialogue_locals = set()
        # the folded REGN ids of Morrowind.esm: sorted, their places are the region catalogue's indexes the engine's
        # weather uses (tools/prepare_world_ui.py region_names / region_weather; ChangeWeather, ModRegion)
        self.base_regions = set()
        # TRAPS-WHEN-OPENED-63: the trap spells placed references name (TNAM), folded id -> id, first-seen order: the
        # actor table gives each an ASPT row, so the engine casts a trap with the spell code (actors.py)
        self.trap_spells = {}

    @property
    def levelled_actors(self):
        """The folded record ids any levelled creature list names (a list inside a list names no actor itself)."""
        return sorted({n for names in self.levelled_lists.values() for n in names})

    def sound_range(self, soun):
        """(min, max) hearing distance of a SOUN record in game units: its bytes times the game settings
        fAudioMinDistanceMult/fAudioMaxDistanceMult, the defaults when both are 0 (rule from OpenMW
        apps/openmw/mwsound/soundbuffer.cpp; the values are the game data's own GMSTs). The rule is hearing.py's."""
        from .hearing import sound_range
        return sound_range(self.gmst, soun)

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
        main = self.scripts.get(MAIN_SCRIPT)
        self.new_game = new_game_scripts(main.text) if main else []
        # the Morrowind.esm placements with their records' final scripts (MWSCRIPT-LATER-MASTER-SCRIPT-61)
        self.references = []
        for r in self._placed_mw:
            base = self.bases.get(r['id'].casefold())
            if base and base[1]:
                self.references.append(dict(r, type=base[0], script=base[1]))
        # MWSCRIPT-ADDON-ATTACH-62: the add-ons' own placements, keyed by their load-order index, with their records'
        # final scripts; bound only for the add-on worlds an image carries (compiler.bindings ADDONS)
        self.addon_references = []
        for r in self._placed_addon:
            base = self.bases.get(r['id'].casefold())
            if base and base[1]:
                self.addon_references.append(dict(r, type=base[0], script=base[1]))
        return self

    def addon_key(self, master, number):
        """The reference key of an add-on's placement NUMBER (its FRMR): the owning file is the add-on itself (top byte
        0) or its k-th master (top byte k); the key is that file's place in MASTERS times ADDON_KEY_STRIDE plus the
        low bits, so Morrowind.esm's references keep their numbers and every key stays exact in the engine's float
        aw_ref field (below 2^24). None when that file is not loaded or the number is too large for the stride."""
        top, low = number >> 24, number & 0xFFFFFF
        if top == 0:
            owner = master
        else:
            masts = self.master_lists.get(master, [])
            if top > len(masts):
                return None
            owner = next((m for m in MASTERS if m.casefold() == masts[top - 1].casefold()), None)
        if owner is None or low >= ADDON_KEY_STRIDE:
            return None
        return MASTERS.index(owner) * ADDON_KEY_STRIDE + low

    def _master(self, master, raw):
        pending_refs = []
        for tag, flags, payload in records(raw):
            if tag == 'TES3':
                # MWSCRIPT-ADDON-ATTACH-62: the file's own master list (MAST, in order): a reference number's top
                # byte k > 0 names its k-th master (OpenMW components/esm3/loadcell.cpp adjustRefNum)
                self.master_lists[master] = [_text(d) for t, d in subrecords(payload) if t == 'MAST']
                continue
            if tag in RECORD_TAGS:
                parts = list(subrecords(payload))
                if tag in ('SKIL', 'MGEF'):              # keyed by INDX: these have no NAME
                    index = dict(parts).get('INDX', b'')
                    if len(index) == 4:
                        self.records[tag][struct.unpack('<i', index)[0]] = parts
                else:
                    ident = _text(dict(parts).get('NAME', b'')).casefold()
                    if _deleted(flags, parts):
                        self.records[tag].pop(ident, None)
                    elif ident:
                        self.records[tag][ident] = parts
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
                elif name.casefold() == 'sdefaultcellname' and fields.get('STRV'):
                    self.default_cell_name = _text(fields['STRV'])
            elif tag == 'REGN':
                fields = dict(subrecords(payload))
                ident = _text(fields.get('NAME', b'')).casefold()
                if ident:
                    self.regions[ident] = _text(fields.get('FNAM', b'')) or ident
                    if master == MASTERS[0] and 'DELE' not in fields:
                        self.base_regions.add(ident)
            elif tag == 'DIAL':
                # the dialogue topics (DATA type 0) AddTopic names and the dialogue window lists (v0.0.57)
                parts = list(subrecords(payload)); fields = dict(parts)
                ident = _text(fields.get('NAME', b''))
                kind = fields.get('DATA', b'\0')[:1]
                if ident and kind == b'\0':
                    if _deleted(flags, parts):
                        self.topics.pop(ident.casefold(), None)
                    else:
                        self.topics[ident.casefold()] = ident
            elif tag == 'INFO':
                parts = list(subrecords(payload)); fields = dict(parts)
                text = _text(fields.get('BNAM') or b'')    # as the dialogue table keeps it (mwad text)
                if text.strip() and not _deleted(flags, parts):
                    self.results.setdefault((_text(fields.get('ONAM', b'')).casefold(), text), None)
                if not _deleted(flags, parts):
                    for function, variable, _, _ in dialogue_conditions(parts):
                        if function in ('Local', 'NotLocal') and variable:
                            self.dialogue_locals.add(variable)
            elif tag == 'SSCR':
                fields = dict(subrecords(payload))
                ident = _text(fields.get('NAME', b'')).casefold()
                if ident and ident not in self.start_scripts:
                    self.start_scripts.append(ident)
            elif tag == 'LEVC':
                # MWSCRIPT-UNPLACED-ATTACH-62: the actors each levelled creature list can give (the last master's
                # record of a list wins; awms.levelled_actor_rows)
                parts = list(subrecords(payload)); fields = dict(parts)
                ident = _text(fields.get('NAME', b'')).casefold()
                if _deleted(flags, parts):
                    self.levelled_lists.pop(ident, None); continue
                self.levelled_lists[ident] = sorted({_text(d).casefold() for t, d in parts if t == 'CNAM'})
            elif tag in SCRIPTED:
                parts = list(subrecords(payload)); fields = dict(parts)
                ident = _text(fields.get('NAME', b''))
                if _deleted(flags, parts):
                    self.bases.pop(ident.casefold(), None); self.holdings.pop(ident.casefold(), None); continue
                self.bases[ident.casefold()] = (tag, _text(fields.get('SCRI', b'')).casefold())
                if tag in HOLDERS:
                    self.holdings[ident.casefold()] = [_text(d[4:36]).casefold() for t, d in parts
                                                       if t == 'NPCO' and len(d) >= 36]
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
            elif tag == 'TNAM':
                ref['trap'] = _text(data)
        for r in refs:
            if r.get('trap') and not r.get('deleted'):
                self.trap_spells.setdefault(r['trap'].casefold(), r['trap'])
        cell_flags, gx, gy = struct.unpack('<Iii', head['DATA']) if len(head.get('DATA', b'')) == 12 else (0, 0, 0)
        interior = bool(cell_flags & 1)
        cell_name = _text(head.get('NAME', b''))
        if not interior:
            # the name GetPCCell compares (the last master's record of the grid cell wins)
            old = self.exteriors.get((gx, gy), ('', ''))
            self.exteriors[(gx, gy)] = (cell_name or old[0], _text(head.get('RGNN', b'')).casefold() or old[1])
        for r in refs:
            if r.get('deleted') or 'id' not in r:
                continue
            base = self.bases.get(r['id'].casefold())
            if master == 'Morrowind.esm':
                self.object_refs.setdefault(r['id'].casefold(), []).append(r['number'])
                if base and base[0] in HOLDERS:
                    self.holder_refs.append({'reference': r['number'], 'id': r['id'].casefold(), 'type': base[0],
                                             'interior': interior, 'cell': cell_name if interior else (gx, gy),
                                             'position': r.get('position', [0.0, 0.0, 0.0])})
                if base and base[0] in ('NPC_', 'CREA'):
                    self.actor_cells[r['number']] = cell_name.casefold() if interior else None
                elif base and interior:
                    # v0.0.62 (MWSCRIPT-GAP-FUNCTIONS-62): any other object's room, for a placing call's template
                    self.object_cells[r['number']] = cell_name.casefold()
                if base and base[0] in PLACEMENT_TYPES:
                    x, y, z = r.get('position', [0.0, 0.0, 0.0])
                    self.placements[r['number']] = (base[0], r['id'].casefold(),
                                                    cell_name.casefold() if interior else (gx, gy), x, y, z)
            if master == 'Morrowind.esm' and base:
                # MWSCRIPT-LATER-MASTER-SCRIPT-61 (v0.0.63): every placed reference with a record is kept here and
                # bound after the last master is read (load), with its record's FINAL script: a later master may give
                # the record one (Tribunal's fab_attack_disable on Vvardenfell's blue candle bulbs)
                self._placed_mw.append({'reference': r['number'], 'id': r['id'], 'interior': interior,
                                        'cell': cell_name if interior else (gx, gy),
                                        'position': r.get('position', [0.0, 0.0, 0.0])})
            if master != 'Morrowind.esm' and base:
                key = self.addon_key(master, r['number'])
                if key is None:
                    self.addon_refs_unkeyed += 1
                elif key >= ADDON_KEY_STRIDE:   # the add-on's own placement (a Morrowind.esm one is bound above)
                    self._placed_addon.append({'reference': key, 'id': r['id'], 'interior': interior,
                                               'cell': cell_name if interior else (gx, gy), 'master': master,
                                               'position': r.get('position', [0.0, 0.0, 0.0])})
            if not base or not base[1]:
                continue
            self.reference_counts[master] += 1
