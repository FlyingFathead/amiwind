# SPDX-License-Identifier: GPL-3.0-only
"""Typed stack bytecode from the parser's tree (opcodes.py), and the program's shared tables.

What the compiler does beyond a plain translation (docs/MWSCRIPT_BYTECODE.md "What the compiler squeezes"):
  - every value is typed at build time: whole-number and fraction opcodes, conversions only where the types meet;
  - constants are folded ("set x to 2 * 30" stores 60) and branches on a constant are dropped;
  - the smallest push for each constant (1, 3 or 5 bytes);
  - names become indexes: globals, journal topics, sounds, voices, music tracks, objects, scripts, strings;
  - each script is marked VOLATILE when it reads something outside the game state (time, distance, chance, a
    sound still playing, an engine query): only those must run every frame; the others run again only when the
    state they read has changed (engine/aga/src/aw_mwvm.c).
"""
import struct

from .opcodes import CODE, CMP_I, CMP_F, ARITH_I, ARITH_F, NONE, QUERIES, WHOLE_STATS, VERBS, CMP_CODES, SPELL_VERBS

# The squeeze switch: False builds the program without the compare-and-branch opcodes (the A/B reference run; the
# builder always squeezes).
SQUEEZE = True
from .functions import lookup, ACTOR_CALLS

SCRIPT_VOLATILE = 1      # reads time, distance, chance, sound state or an engine query
SCRIPT_NOTYET = 2        # holds at least one NOTYET call
SCRIPT_START = 4         # a start script (runs from the beginning of the game)
SCRIPT_BROKEN = 8        # did not compile (an error in the original data); its code is END
SCRIPT_GLOBAL = 16       # started by StartScript somewhere (runs as a global script)
SCRIPT_HANDWRITTEN = 32  # the engine carries this behaviour by hand today (config/mwscript.json): not run
SCRIPT_INERT = 64        # nothing it can do today is seen outside its own values (no sound, global, journal, other
                         # object, script start or stop; only NOTYET calls): not attached until that changes
SCRIPT_ONACTIVATE = 128  # reads OnActivate: the player's use of its object goes to the script (the original's rule)
SCRIPT_ACTOR = 256       # reads the actor record (stats, items, spells, deaths): not VOLATILE; it wakes when the
                         # state generation moves, which a script's change or the engine's (a hit, a death) does
EFFECT_OPS = {'SETG', 'SETGS', 'SETM', 'SETMS', 'SETJ', 'JOURNAL', 'PLAYSOUND', 'PLAYSOUNDVP', 'PLAYSOUND3D',
              'PLAYSOUND3DVP', 'PLAYLOOP3D', 'PLAYLOOP3DVP', 'STOPSOUND', 'SAY', 'STREAMMUSIC', 'STARTSCRIPT',
              'STOPSCRIPT', 'ENABLE', 'DISABLE', 'LOCK', 'UNLOCK', 'ACTIVATE', 'COMBAT', 'AIWANDER', 'PLAYERMOVE'}
# ACTOR, ITEM and SPELL are effects only when they change something (their verb): see effect_op()


def effect_op(name, args):
    """Whether one decoded opcode is seen outside the script's own values (the INERT rule)."""
    if name in EFFECT_OPS:
        return True
    if name == 'ACTOR':
        return args[0] in (VERBS['set'], VERBS['mod'], VERBS['modcurrent'])
    if name == 'ITEM':
        return args[0] != 0
    if name == 'SPELL':
        return args[0] in (SPELL_VERBS['add'], SPELL_VERBS['remove'])
    return False

# The opcodes whose answer changes without the state generation moving (a script that holds one runs every frame).
# Not among them: CELLCHANGED (true only when the script is woken anyway) and SOUNDPLAYING (the script's own
# sounds: it acted when it started one, and the host wakes it when one ends).
VOLATILE_OPS = {'SECONDS', 'RANDOM', 'MENUMODE', 'SAYDONE', 'DISTANCE', 'QUERY',
                'SCRIPTRUNNING', 'GETDISABLED', 'GETLOCKED', 'ONACTIVATE', 'GETPOS'}


class CompileError(ValueError):
    pass


class Table:
    """An interned list: key -> index, with the stored row for each index."""

    def __init__(self, limit=0xFFFE):
        self.index, self.rows, self.limit = {}, [], limit

    def get(self, key, row=None):
        if key in self.index:
            return self.index[key]
        if len(self.rows) >= self.limit:
            raise CompileError('table full')
        self.index[key] = len(self.rows)
        self.rows.append(row if row is not None else key)
        return self.index[key]

    def __len__(self):
        return len(self.rows)


class Program:
    """The tables every script shares, filled while scripts compile.

    data: GameData. media: an object with sound(id) / voice(path) / music(path) -> row dict or None (media.py);
    None makes rows from the game data alone (the measurement before a catalogue exists)."""

    def __init__(self, data, media=None, scripts=None):
        self.data = data
        self.media = media
        self.strings = Table()
        self.globals = Table()
        self.journal = Table()
        self.sounds = Table()
        self.voices = Table()
        self.music = Table()
        self.objects = Table()
        self.scripts = Table()
        self.pccells = Table()    # GetPCCell names: the cells each one matches (the PCEL section)
        self.moves = Table()      # the player's PositionCell moves, worked out at build time (the PMOV section)
        self.rooms = None         # {interior cell: room map and recentring} (rooms.room_table; compiler.py sets it)
        self.unresolved = []      # (script, kind, name, reason)
        for name, (kind, value, spelling) in data.globals.items():
            self.globals.get(name, {'name': spelling, 'type': kind, 'value': value})
        self.script_locals = {}   # folded script id -> {local: (type, slot)}
        for s in (data.scripts.values() if scripts is None else scripts):
            self.scripts.get(s.id.casefold(), {'name': s.id, 'script': s})
        # the actor table (actors.py): every NPC and creature record, the items and spells they and the scripts name
        from .actors import ActorTables
        self.actors = ActorTables(data, self.string)

    def string(self, text):
        return self.strings.get(text)

    def topic(self, name):
        key = name.casefold()
        return self.journal.get(key, {'name': name})

    def sound(self, name, script):
        key = name.casefold()
        if key in self.sounds.index:
            return self.sounds.index[key]
        row = self.media.sound(name) if self.media else None
        if row is None:
            soun = self.data.sounds.get(key)
            row = {'id': name, 'resolved': False, 'reason': 'no SOUN record' if soun is None else 'not mapped',
                   'volume': soun['volume'] if soun else 255, 'min': soun['min'] if soun else 0,
                   'max': soun['max'] if soun else 0}
        if not row.get('resolved'):
            self.unresolved.append((script, 'sound', name, row.get('reason')))
        row.setdefault('name_string', self.string(name))
        return self.sounds.get(key, row)

    def voice(self, path, script):
        key = path.replace('\\', '/').casefold()
        if key in self.voices.index:
            return self.voices.index[key]
        row = self.media.voice(path) if self.media else None
        if row is None:
            row = {'path': path, 'resolved': False, 'reason': 'not mapped'}
        if not row.get('resolved'):
            self.unresolved.append((script, 'voice', path, row.get('reason')))
        row.setdefault('name_string', self.string(path))
        return self.voices.get(key, row)

    def track(self, path, script):
        key = path.replace('\\', '/').casefold()
        if key in self.music.index:
            return self.music.index[key]
        row = self.media.music(path) if self.media else None
        if row is None:
            row = {'path': path, 'resolved': False, 'reason': 'not mapped', 'track': 255}
        if not row.get('resolved'):
            self.unresolved.append((script, 'music', path, row.get('reason')))
        row.setdefault('name_string', self.string(path))
        return self.music.get(key, row)

    def object(self, name):
        """Object table index of an object id or a script name ('player' is NONE)."""
        key = name.casefold()
        if key == 'player':
            return NONE
        if key in self.objects.index:
            return self.objects.index[key]
        refs = self.data.object_refs.get(key, [])
        base = self.data.bases.get(key)
        row = {'id': name, 'reference': refs[0] if len(refs) == 1 else 0, 'placed': len(refs),
               'script': None, 'kind': 'object'}
        if base and base[1] and base[1] in self.scripts.index:
            row['script'] = self.scripts.index[base[1]]
        elif key in self.scripts.index and not base:
            row.update(kind='script', script=self.scripts.index[key])
        row['id_string'] = self.string(name)
        return self.objects.get(key, row)

    def pccell(self, name):
        """PCEL row of a GetPCCell name: every cell whose name starts with it, without case (rule from OpenMW
        apps/openmw/mwscript/cellextensions.cpp OpGetPCCell): rooms by their stable number (_aw_cell_int), outdoor
        cells by grid, an outdoor cell named by its own name, else its region's name, else the game setting
        sDefaultCellname (OpenMW's world getCellName). Made once here, so the engine compares numbers, never text."""
        key = name.casefold()
        if key in self.pccells.index:
            return self.pccells.index[key]
        d = self.data
        rooms = sorted(n for cell, n in d.interior_numbers.items() if cell.startswith(key))
        outside = sorted(xy for xy, (cell, region) in d.exteriors.items()
                         if (cell or d.regions.get(region) or d.default_cell_name).casefold().startswith(key))
        if any(n > 0xFFFF for n in rooms) or any(not (-128 <= v <= 127) for xy in outside for v in xy):
            raise CompileError('GetPCCell %r: a cell outside the table\'s ranges' % name)
        wild = d.default_cell_name.casefold().startswith(key)
        return self.pccells.get(key, {'name': name, 'rooms': rooms, 'outside': outside, 'wilderness': wild})

    def player_move(self, args):
        """PMOV row of a PositionCell of the player, or None when it stays "not yet" (a number not constant, a room no
        repo list names). Rule from OpenMW apps/openmw/mwscript/transformationextensions.cpp OpPositionCell: a cell
        that is no interior moves the player outdoors to x, y (also an unknown name); the player's rotation is in
        degrees. Into a room: its map and the arrival as a door's (rooms.py)."""
        from .opcodes import PLAYERMOVE_KINDS
        numbers = [fold(a) for a in args if a[0] != 'str'][:4]
        cells = [a[1] for a in args if a[0] == 'str']
        if len(numbers) < 4 or not all(_const(n) for n in numbers) or not cells:
            return None
        x, y, z, rot = (float(n[1]) for n in numbers)
        key = cells[0].casefold()
        if key in self.data.interior_numbers:
            room = (self.rooms or {}).get(key)
            if room is None:
                return None
            from .rooms import arrival
            ax, ay, az, yaw = arrival((x, y, z), rot, room.get('offset'))
            row = {'kind': PLAYERMOVE_KINDS['room'], 'map': self.string(room['map']), 'at': (ax, ay, az), 'yaw': yaw}
        else:
            row = {'kind': PLAYERMOVE_KINDS['outdoors'], 'map': NONE, 'at': (x, y, z), 'yaw': rot}
        return self.moves.get((row['kind'], row['map'], row['at'], row['yaw']), row)

    def item(self, name):
        """AITM row of an item id a script names (the gold coins are one item)."""
        from .actors import item_id
        return self.actors.item(item_id(name))

    def spell(self, name):
        """ASPT row of a spell id a script names."""
        return self.actors.spell(name)

    def locals_of(self, name):
        """{local: (type, slot)} of the script an object id or script name runs, or None."""
        key = name.casefold()
        base = self.data.bases.get(key)
        script = base[1] if base and base[1] else (key if key in self.data.scripts else None)
        return self.script_locals.get(script) if script else None


class Emitter:
    def __init__(self):
        self.code = bytearray()
        self.ops = []          # (offset, name) for the statistics
        self.depth = 0
        self.max_depth = 0

    def op(self, name, *operands, layout=None, pops=0, pushes=0):
        from .opcodes import LAYOUT
        code = CODE[name]
        self.ops.append((len(self.code), name))
        self.code.append(code)
        fmt = layout if layout is not None else LAYOUT[code]
        for letter, value in zip(fmt, operands):
            self.code += struct.pack({'b': '>b', 'B': '>B', 'h': '>h', 'H': '>H', 'i': '>i', 'f': '>f'}[letter],
                                     value)
        self.depth += pushes - pops
        self.max_depth = max(self.max_depth, self.depth)
        return len(self.code)

    def jump(self, name):
        """A jump with its offset to patch; returns the patch position."""
        pops = 1 if name == 'JZ' else 0
        self.op(name, 0, pops=pops)
        return len(self.code) - 2

    def patch(self, at, target=None):
        target = len(self.code) if target is None else target
        delta = target - (at + 2)
        if not -32768 <= delta <= 32767:
            raise CompileError('jump too far')
        self.code[at:at + 2] = struct.pack('>h', delta)


def _const(node):
    return node[0] in ('int', 'float')


def fold(node):
    """Constant folding on the tree (whole numbers stay whole, as the game computes them)."""
    kind = node[0]
    if kind == 'bin':
        a, b = fold(node[2]), fold(node[3])
        if _const(a) and _const(b):
            x, y = a[1], b[1]
            whole = a[0] == 'int' and b[0] == 'int'
            op = node[1]
            if op == '/' and y == 0:
                return ('bin', op, a, b)
            if op == '+':
                v = x + y
            elif op == '-':
                v = x - y
            elif op == '*':
                v = x * y
            else:
                v = int(x / y) if whole else x / y
            if whole and -2 ** 31 <= v < 2 ** 31:
                return ('int', v)
            if not whole:
                return ('float', float(struct.unpack('>f', struct.pack('>f', v))[0]))
        return ('bin', node[1], a, b)
    if kind == 'neg':
        a = fold(node[1])
        return (a[0], -a[1]) if _const(a) else ('neg', a)
    if kind == 'cmp':
        a, b = fold(node[2]), fold(node[3])
        if _const(a) and _const(b):
            x, y = a[1], b[1]
            v = {'==': x == y, '!=': x != y, '<': x < y, '<=': x <= y, '>': x > y, '>=': x >= y}[node[1]]
            return ('int', int(v))
        return ('cmp', node[1], a, b)
    return node


class ScriptCompiler:
    def __init__(self, program, ident, tree, local_types, warnings):
        self.p = program
        self.ident = ident
        self.tree = tree
        self.locals = local_types          # {name: (type letter, slot)}
        self.e = Emitter()
        self.warnings = warnings
        self.flags = 0
        self.calls = []                    # function names compiled (with repeats)
        self.notyet_names = []             # the calls compiled to NOTYET (with repeats)
        self.loops = 0

    # --- expressions: emit and return 'i' or 'f' ---
    def push_const(self, node):
        if node[0] == 'int':
            v = node[1]
            if -128 <= v <= 127:
                self.e.op('PUSHB', v, pushes=1)
            elif -32768 <= v <= 32767:
                self.e.op('PUSHW', v, pushes=1)
            else:
                self.e.op('PUSHL', max(-2 ** 31, min(2 ** 31 - 1, v)), pushes=1)
            return 'i'
        self.e.op('PUSHF', node[1], pushes=1)
        return 'f'

    def convert(self, have, want):
        if have == want:
            return
        if want == 'f':
            self.e.op('I2F')
        else:
            self.e.op('F2I')

    def expr(self, node):
        node = fold(node)
        kind = node[0]
        if kind in ('int', 'float'):
            return self.push_const(node)
        if kind == 'local':
            letter, slot = self.locals[node[1]]
            self.e.op('GETL', slot, pushes=1)
            return 'f' if letter == 'f' else 'i'
        if kind == 'global':
            index = self.p.globals.index[node[1]]
            self.e.op('GETG', index, pushes=1)
            return 'f' if self.p.globals.rows[index]['type'] == 'f' else 'i'
        if kind == 'member':
            target = self.member(node[1], node[2])
            if target is None:
                return self.push_const(('int', 0))
            obj, slot, letter = target
            self.e.op('GETM', obj, slot, pushes=1)
            return 'f' if letter == 'f' else 'i'
        if kind == 'neg':
            t = self.expr(node[1])
            self.e.op('NEGF' if t == 'f' else 'NEGI')
            return t
        if kind in ('bin', 'cmp'):
            # whole with whole stays whole; any fraction makes both sides fractions (the game's arithmetic)
            t = 'f' if 'f' in (self.typeof(node[2]), self.typeof(node[3])) else 'i'
            self.convert(self.expr(node[2]), t)
            self.convert(self.expr(node[3]), t)
            if kind == 'bin':
                self.e.op((ARITH_F if t == 'f' else ARITH_I)[node[1]], pops=2, pushes=1)
                return t
            self.e.op((CMP_F if t == 'f' else CMP_I)[node[1]], pops=2, pushes=1)
            return 'i'
        if kind == 'call':
            t = self.call(node, value=True)
            return t
        raise CompileError('unknown expression ' + kind)

    def typeof(self, node):
        """The type an expression has, without emitting it."""
        node = fold(node)
        kind = node[0]
        if kind == 'int':
            return 'i'
        if kind == 'float':
            return 'f'
        if kind == 'local':
            return 'f' if self.locals[node[1]][0] == 'f' else 'i'
        if kind == 'global':
            return 'f' if self.p.globals.rows[self.p.globals.index[node[1]]]['type'] == 'f' else 'i'
        if kind == 'member':
            table = self.p.locals_of(node[1])
            found = table.get(node[2].casefold()) if table else None
            return 'f' if found and found[0] == 'f' else 'i'
        if kind == 'neg':
            return self.typeof(node[1])
        if kind == 'bin':
            return 'f' if 'f' in (self.typeof(node[2]), self.typeof(node[3])) else 'i'
        if kind == 'cmp':
            return 'i'
        if kind == 'call':
            fn = lookup(node[2])
            if fn.name in ('getsoundplaying', 'saydone', 'getjournalindex', 'menumode', 'cellchanged',
                           'scriptrunning'):
                return 'i'
            if fn.name in ('getsecondspassed', 'random', 'getdistance', 'getsquareroot'):
                return 'f'
            return 'f' if fn.ret == 'f' else 'i'
        raise CompileError('unknown expression ' + kind)

    # --- calls ---
    def call(self, node, value):
        _, ref, name, args, extra = node
        fn = lookup(name)
        self.calls.append(fn.name)
        if fn.name == 'getitemcount' and ref is not None and ref.casefold() == 'player' and args \
                and args[0][0] == 'str':
            # the player's inventory counts are game state the engine keeps (aw_state.c AW_ITEM)
            self.e.op('QUERY', QUERIES['ITEM_COUNT'], self.p.string(args[0][1].casefold()), pushes=1)
            self.flags |= SCRIPT_VOLATILE
            return 'i'
        if fn.name == 'positioncell' and ref is not None and ref.casefold() == 'player':
            move = self.p.player_move(args)
            if move is not None:
                self.e.op('PLAYERMOVE', move)
                return None
        if not fn.run:
            return self.notyet(fn, ref, args, value)
        n = fn.name
        s = lambda i: args[i][1] if i < len(args) and args[i][0] == 'str' else ''   # noqa: E731
        # OpenMW: DontSaveObject does nothing, Xbox reads 0 (miscextensions.cpp): no code, a constant
        if n == 'dontsaveobject':
            return None
        if n == 'xbox':
            return self.push_const(('int', 0))
        if n == 'getpccell':
            # the player's cell: no reference (OpenMW reads the player's), a table row, not VOLATILE: the engine
            # moves the state generation when the player's cell changes (aw_mwhost.c)
            self.e.op('GETPCCELL', self.p.pccell(s(0)), pushes=1)
            return 'i'
        if ref is not None:
            self.e.op('REF', self.p.object(ref))
        if n == 'getpos':
            axis = s(0).casefold()[:1]
            if axis not in ('x', 'y', 'z'):
                self.warnings.append('GetPos with no axis %r: reads 0 (OpenMW)' % s(0))
                return self.push_const(('float', 0.0))
            self.e.op('GETPOS', 'xyz'.index(axis), pushes=1); self.flags |= SCRIPT_VOLATILE
            return 'f'
        if n in ('getcurrentaipackage', 'getaipackagedone'):
            # rules from OpenMW apps/openmw/mwscript/aiextensions.cpp OpGetCurrentAIPackage and OpGetAiPackageDone;
            # not VOLATILE: the ambient tables move the state generation when a package starts or ends
            self.e.op('AIPACKAGE', 0 if n == 'getcurrentaipackage' else 1, pushes=1)
            return 'i'
        if n in ('getcommondisease', 'getblightdisease'):
            self.e.op('SPELL', SPELL_VERBS['common_disease' if n == 'getcommondisease' else 'blight_disease'], 0,
                      pushes=1)
            self.flags |= SCRIPT_ACTOR
            return 'i'
        # audio: rules from OpenMW apps/openmw/mwscript/soundextensions.cpp (OpPlaySound, OpPlaySoundVP,
        # OpPlaySound3D, OpPlaySoundVP3D, OpStopSound, OpGetSoundPlaying, OpSay, OpSayDone, OpStreamMusic); a sound
        # names a SOUN record, Say a voice file, StreamMusic a music file: each resolved here to the media pool file
        # (media.py), so the engine reads indexes only
        if n in ('playsound', 'playsound3d', 'playloopsound3d', 'stopsound', 'getsoundplaying'):
            index = self.p.sound(s(0), self.ident)
            op = {'playsound': 'PLAYSOUND', 'playsound3d': 'PLAYSOUND3D', 'playloopsound3d': 'PLAYLOOP3D',
                  'stopsound': 'STOPSOUND', 'getsoundplaying': 'SOUNDPLAYING'}[n]
            self.e.op(op, index, pushes=1 if op == 'SOUNDPLAYING' else 0)
            return 'i' if op == 'SOUNDPLAYING' else None
        if n in ('playsoundvp', 'playsound3dvp', 'playloopsound3dvp'):
            index = self.p.sound(s(0), self.ident)
            for a in args[1:3]:
                self.convert(self.expr(a), 'f')
            self.e.op({'playsoundvp': 'PLAYSOUNDVP', 'playsound3dvp': 'PLAYSOUND3DVP',
                       'playloopsound3dvp': 'PLAYLOOP3DVP'}[n], index, pops=2)
            return None
        if n in ('say', 'say3d'):
            self.e.op('SAY', self.p.voice(s(0), self.ident), self.p.string(s(1)))
            return None
        if n == 'saydone':
            self.e.op('SAYDONE', pushes=1); self.flags |= SCRIPT_VOLATILE
            return 'i'
        if n == 'streammusic':
            self.e.op('STREAMMUSIC', self.p.track(s(0), self.ident))
            return None
        if n in ('journal', 'setjournalindex'):
            self.convert(self.expr(args[1]), 'i')
            self.e.op('JOURNAL' if n == 'journal' else 'SETJ', self.p.topic(s(0)), pops=1)
            return None
        if n == 'getjournalindex':
            self.e.op('GETJ', self.p.topic(s(0)), pushes=1)
            return 'i'
        if n == 'getsecondspassed':
            self.e.op('SECONDS', pushes=1); self.flags |= SCRIPT_VOLATILE
            return 'f'
        if n == 'random':
            self.convert(self.expr(args[0]), 'i')
            self.e.op('RANDOM', pops=1, pushes=1); self.flags |= SCRIPT_VOLATILE
            return 'f'
        if n == 'menumode':
            self.e.op('MENUMODE', pushes=1); self.flags |= SCRIPT_VOLATILE
            return 'i'
        if n == 'cellchanged':
            # not VOLATILE (v0.0.54): CellChanged reads 1 only on the run after the object was attached or came into
            # range, and the interpreter runs a quiet script on exactly those frames (aw_mwvm.c AWI_CELLCHANGED);
            # the sound markers ("if CellChanged ... GetSoundPlaying ... PlayLoopSound") were most of every frame's
            # work and now run once, and again when their sound ends (the host wakes them: aw_mwhost.c)
            self.e.op('CELLCHANGED', pushes=1)
            return 'i'
        if n in ('startscript', 'stopscript', 'scriptrunning'):
            key = s(0).casefold()
            if key not in self.p.scripts.index:
                self.warnings.append('%s of an unknown script %r: not compiled' % (n, s(0)))
                if n == 'scriptrunning':
                    return self.push_const(('int', 0))
                return None
            index = self.p.scripts.index[key]
            if n == 'startscript':
                self.p.scripts.rows[index]['started'] = True
            op = {'startscript': 'STARTSCRIPT', 'stopscript': 'STOPSCRIPT', 'scriptrunning': 'SCRIPTRUNNING'}[n]
            self.e.op(op, index, pushes=1 if op == 'SCRIPTRUNNING' else 0)
            if op == 'SCRIPTRUNNING':
                self.flags |= SCRIPT_VOLATILE
            return 'i' if op == 'SCRIPTRUNNING' else None
        if n == 'getdistance':
            self.e.op('DISTANCE', self.p.object(s(0)), pushes=1); self.flags |= SCRIPT_VOLATILE
            return 'f'
        if n == 'getsquareroot':
            self.convert(self.expr(args[0]), 'f')
            self.e.op('SQRT')
            return 'f'
        if n in ('enable', 'disable', 'unlock'):
            self.e.op(n.upper())
            return None
        if n in ('getdisabled', 'getlocked'):
            self.e.op(n.upper(), pushes=1); self.flags |= SCRIPT_VOLATILE
            return 'i'
        if n == 'onactivate':
            # the object's use goes to this script from now on (the original's rule); read every frame
            self.e.op('ONACTIVATE', pushes=1); self.flags |= SCRIPT_VOLATILE | SCRIPT_ONACTIVATE
            return 'i'
        if n == 'activate':
            self.e.op('ACTIVATE')
            return None
        if n == 'messagebox':
            # the text, its numbers (each pushed as a number with a fraction; %d formats the whole part), the buttons
            numbers = args[1:1 + extra['nargs']]
            for a in numbers:
                self.convert(self.expr(a), 'f')
            buttons = [self.p.string(b) for b in extra['buttons']]
            if len(numbers) > 0x1F or len(buttons) > 0xFF:
                raise CompileError('messagebox with too many numbers or buttons')
            self.e.op('MESSAGEBOX', self.p.string(extra['format']), len(numbers), len(buttons), *buttons,
                      layout='HBB' + 'H' * len(buttons), pops=len(numbers))
            return None
        if n == 'getbuttonpressed':
            self.e.op('GETBUTTONPRESSED', pushes=1); self.flags |= SCRIPT_VOLATILE
            return 'i'
        if n == 'lock':
            # Lock [level]: without a number the lock takes the level it had (-1 to the engine)
            numbers = [a for a in args if a[0] != 'str']
            if numbers:
                self.convert(self.expr(numbers[0]), 'i')
            else:
                self.push_const(('int', -1))
            self.e.op('LOCK', pops=1)
            return None
        # --- the actor record (engine/aga/src/aw_actorstate.h; docs/ACTOR_STATE.md) ---
        if n in ACTOR_CALLS:
            verb, stat = ACTOR_CALLS[n]
            whole = stat in WHOLE_STATS and verb != VERBS['ratio']
            if verb in (VERBS['set'], VERBS['mod'], VERBS['modcurrent']):
                self.convert(self.expr(args[0] if args else ('int', 0)), 'i' if whole else 'f')
                self.e.op('ACTOR', verb, stat, pops=1)
                return None
            self.e.op('ACTOR', verb, stat, pushes=1)
            self.flags |= SCRIPT_ACTOR
            return 'i' if whole else 'f'
        if n in ('additem', 'removeitem', 'getitemcount'):
            item = self.p.item(s(0))
            if n == 'getitemcount':
                self.e.op('ITEM', 0, item, pushes=1)
                self.flags |= SCRIPT_ACTOR
                return 'i'
            self.convert(self.expr(args[1] if len(args) > 1 else ('int', 1)), 'i')
            self.e.op('ITEM', 1 if n == 'additem' else 2, item, pops=1)
            return None
        if n in ('addspell', 'removespell', 'getspell'):
            spell = self.p.spell(s(0))
            if n == 'getspell':
                self.e.op('SPELL', 0, spell, pushes=1)
                self.flags |= SCRIPT_ACTOR
                return 'i'
            self.e.op('SPELL', 1 if n == 'addspell' else 2, spell)
            return None
        if n in ('startcombat', 'stopcombat'):
            self.e.op('COMBAT', 0 if n == 'startcombat' else 1, self.p.object(s(0)) if n == 'startcombat' else NONE)
            return None
        if n == 'aiwander':
            # range, duration, time and then up to 10 more, each a whole number (OpenMW OpAiWander truncates the
            # first three); the engine reads them as OpenMW does (aw_mwhost.c)
            numbers = [a for a in args if a[0] != 'str'][:13]
            while len(numbers) < 3:
                numbers.append(('int', 0))
            for a in numbers:
                self.convert(self.expr(a), 'i')
            self.e.op('AIWANDER', len(numbers) - 3, pops=len(numbers))
            return None
        if n == 'getdeadcount':
            row = self.p.actors.actor(s(0))
            self.e.op('DEADCOUNT', NONE if row is None else row, pushes=1)
            self.flags |= SCRIPT_ACTOR
            return 'i'
        raise CompileError('run function without code: ' + n)

    def notyet(self, fn, ref, args, value):
        """NOTYET: the numeric arguments pushed, the strings as indexes; logged once by the engine."""
        self.flags |= SCRIPT_NOTYET
        self.notyet_names.append(fn.name)
        numeric = 0
        strings = []
        if ref is not None:
            strings.append(self.p.string(ref))
        for a in args:
            if a[0] == 'str':
                strings.append(self.p.string(a[1]))
            else:
                self.expr(a)
                numeric += 1
        returns = fn.ret != '-'
        if numeric > 0x1F or len(strings) > 0xFF:
            raise CompileError('%s with too many arguments' % fn.name)
        flags = numeric | (0x80 if returns else 0) | (0x40 if fn.ret == 'f' else 0) | (0x20 if ref is not None else 0)
        layout = 'HHBB' + 'H' * len(strings)
        self.e.op('NOTYET', fn.number, self.p.string(fn.name), flags, len(strings), *strings, layout=layout,
                  pops=numeric, pushes=1 if returns else 0)
        if returns:
            # NOTYET reads 0 (a constant until the engine carries the function out, by its number through the host's
            # call() or with its own opcode): it does not make the script VOLATILE
            return 'f' if fn.ret == 'f' else 'i'
        return None

    def member(self, owner, var):
        table = self.p.locals_of(owner)
        if table is None or var.casefold() not in table:
            self.warnings.append('member %s.%s not found: reads 0, writes are dropped' % (owner, var))
            return None
        letter, slot = table[var.casefold()]
        return self.p.object(owner), slot, letter

    # --- statements ---
    def block(self, stmts):
        for st in stmts:
            self.statement(st)

    def statement(self, st):
        kind = st[0]
        if kind == 'set':
            _, line, target, value = st
            if target[0] == 'local':
                letter, slot = self.locals[target[1]]
                self.convert(self.expr(value), 'f' if letter == 'f' else 'i')
                self.e.op('SETLS' if letter == 's' else 'SETL', slot, pops=1)
            elif target[0] == 'global':
                index = self.p.globals.index[target[1]]
                letter = self.p.globals.rows[index]['type']
                self.convert(self.expr(value), 'f' if letter == 'f' else 'i')
                self.e.op('SETGS' if letter == 's' else 'SETG', index, pops=1)
            else:
                found = self.member(target[1], target[2])
                if found is None:
                    return
                obj, slot, letter = found
                self.convert(self.expr(value), 'f' if letter == 'f' else 'i')
                self.e.op('SETMS' if letter == 's' else 'SETM', obj, slot, pops=1)
            return
        if kind == 'do':
            t = self.call(st[2], value=False)
            if t is not None:
                self.e.op('POP', pops=1)
            return
        if kind == 'return':
            self.e.op('RET')
            return
        if kind == 'if':
            _, line, branches, otherwise = st
            live = []
            for cond, body in branches:
                c = fold(cond)
                if _const(c):
                    if c[1]:
                        live.append((None, body))   # always true: what follows is dead code
                        break
                    continue                        # always false: dropped
                live.append((c, body))
            tail = live and live[-1][0] is None
            ends = []
            for i, (c, body) in enumerate(live):
                if c is None:
                    self.block(body)
                    break
                skip = self.branch_false(c)
                self.block(body)
                # no jump over nothing: the last test with no else after it falls through
                if i < len(live) - 1 or (otherwise and not tail):
                    ends.append(self.e.jump('JMP'))
                self.e.patch(skip)
            if not tail:
                self.block(otherwise)
            for at in ends:
                self.e.patch(at)
            return
        if kind == 'while':
            _, line, cond, body = st
            c = fold(cond)
            if _const(c) and not c[1]:
                return
            top = len(self.e.code)
            out = self.branch_false(c)
            self.block(body)
            back = self.e.jump('JMP')
            self.e.patch(back, top)
            self.e.patch(out)
            self.loops += 1
            return
        raise CompileError('unknown statement ' + kind)

    def condition(self, node):
        t = self.expr(node)
        if t == 'f':
            self.e.op('PUSHB', 0, pushes=1); self.e.op('I2F'); self.e.op('NEF', pops=2, pushes=1)

    def branch_false(self, node):
        """The test of an if or while and its jump past the body; returns the jump's patch position. With SQUEEZE, a
        whole number tested against a constant of -128..127 is one opcode (JNEB for ==, else JCMPB) instead of
        PUSHB, the comparison and JZ (docs/MWSCRIPT_BYTECODE.md "What it squeezes")."""
        if SQUEEZE and node[0] == 'cmp' and node[3][0] == 'int' and -128 <= node[3][1] <= 127 \
                and self.typeof(node[2]) == 'i':
            self.expr(node[2])
            if node[1] == '==':
                self.e.op('JNEB', node[3][1], 0, pops=1)
            else:
                self.e.op('JCMPB', CMP_CODES[node[1]], node[3][1], 0, pops=1)
            return len(self.e.code) - 2
        self.condition(node)
        return self.e.jump('JZ')

    def compile(self):
        self.block(self.tree[2])
        self.e.op('END')
        return bytes(self.e.code)
