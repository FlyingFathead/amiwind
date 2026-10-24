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

from .opcodes import CODE, CMP_I, CMP_F, ARITH_I, ARITH_F, NONE, QUERIES
from .functions import lookup

SCRIPT_VOLATILE = 1      # reads time, distance, chance, sound state or an engine query
SCRIPT_NOTYET = 2        # holds at least one NOTYET call
SCRIPT_START = 4         # a start script (runs from the beginning of the game)
SCRIPT_BROKEN = 8        # did not compile (an error in the original data); its code is END
SCRIPT_GLOBAL = 16       # started by StartScript somewhere (runs as a global script)
SCRIPT_HANDWRITTEN = 32  # the engine carries this behaviour by hand today (config/mwscript.json): not run
SCRIPT_INERT = 64        # nothing it can do today is seen outside its own values (no sound, global, journal, other
                         # object, script start or stop; only NOTYET calls): not attached until that changes
EFFECT_OPS = {'SETG', 'SETGS', 'SETM', 'SETMS', 'SETJ', 'JOURNAL', 'PLAYSOUND', 'PLAYSOUNDVP', 'PLAYSOUND3D',
              'PLAYSOUND3DVP', 'PLAYLOOP3D', 'PLAYLOOP3DVP', 'STOPSOUND', 'SAY', 'STREAMMUSIC', 'STARTSCRIPT',
              'STOPSCRIPT'}

VOLATILE_OPS = {'SECONDS', 'RANDOM', 'MENUMODE', 'CELLCHANGED', 'SOUNDPLAYING', 'SAYDONE', 'DISTANCE', 'QUERY',
                'SCRIPTRUNNING'}


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
        self.unresolved = []      # (script, kind, name, reason)
        for name, (kind, value, spelling) in data.globals.items():
            self.globals.get(name, {'name': spelling, 'type': kind, 'value': value})
        self.script_locals = {}   # folded script id -> {local: (type, slot)}
        for s in (data.scripts.values() if scripts is None else scripts):
            self.scripts.get(s.id.casefold(), {'name': s.id, 'script': s})

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
        if ref is not None and fn.run:
            self.e.op('REF', self.p.object(ref))
        if not fn.run:
            return self.notyet(fn, ref, args, value)
        n = fn.name
        s = lambda i: args[i][1] if i < len(args) and args[i][0] == 'str' else ''   # noqa: E731
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
            self.e.op('CELLCHANGED', pushes=1); self.flags |= SCRIPT_VOLATILE
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
        flags = numeric | (0x80 if returns else 0) | (0x40 if fn.ret == 'f' else 0) | (0x20 if ref is not None else 0)
        layout = 'HBB' + 'H' * len(strings)
        self.e.op('NOTYET', self.p.string(fn.name), flags, len(strings), *strings, layout=layout,
                  pops=numeric, pushes=1 if returns else 0)
        if returns:
            # NOTYET reads 0 every time (a constant until the engine carries the function out, when it gets its own
            # opcode and the script is compiled again): it does not make the script VOLATILE
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
                self.condition(c)
                skip = self.e.jump('JZ')
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
            self.condition(c)
            out = self.e.jump('JZ')
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

    def compile(self):
        self.block(self.tree[2])
        self.e.op('END')
        return bytes(self.e.code)
