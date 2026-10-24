# SPDX-License-Identifier: GPL-3.0-only
"""The AWMS1 file (id1/mwscript.awm): every compiled script and the tables they index. Big-endian.

  header   "AWMS" u16 version (1) u16 sections u32 file bytes u32 resident bytes
  directory, one row per section: tag[4] u32 offset u32 rows u32 bytes
  CONF  8 bytes: u32 activation range (game units) u16 opcodes per frame u16 opcodes per script run
  The sections up to CODE are what the engine keeps in memory (the "resident bytes" from the start of the file);
  BIND and STRS stay on disk: the bindings are read at each map change, a string only when one is logged.
  GLOB  8 bytes a global:   u8 type (0 short, 1 long, 2 float) u8 0 u16 name u32 initial value (raw cell)
  JRNL  2 bytes a topic:    u16 name
  SNDS  18 bytes a sound:   u8 pool name[8] u16 length (1/100 s) u8 volume u8 flags (1 mapped)
                            u16 near u16 far (hearing distances in game units, the SOUN record's min/max times the
                            game settings) u16 name
  VOIC  12 bytes a voice:   u8 pool name[8] u16 length (1/100 s) u16 path
  MUSI  4 bytes a track:    u8 track number (255 none) u8 flags (1 mapped) u16 path
  OBJS  12 bytes an object: u32 reference (0: not placed once) u16 id u16 script (0xFFFF none) u16 placed u16 flags
                            (1: the id names a script, its global instance)
  SCRP  16 bytes a script:  u16 name u8 locals u8 stack u16 flags u16 0 u32 code offset u32 code bytes
  CODE  the bytecode of every script, one after another
  BIND  24 bytes a placed scripted reference, ascending: u32 reference u16 script u16 flags
                            i16 cell x (or u16 the interior's stable number, the room map's _aw_cell_int)
                            i16 cell y i32 x y z (game units)
  STRT  2 bytes a start script: u16 script
  STRS  u32 offset per string, then the NUL-ended strings (cp1252)

A pool name is the 8 bytes of a converted file's name in the media catalogue: sound/pool/a<16 hex>.wav.
"""
import struct

from .opcodes import NAME, LAYOUT

MAGIC = b'AWMS'
VERSION = 1
TYPES = {'s': 0, 'l': 1, 'f': 2}
ORDER = ('CONF', 'GLOB', 'JRNL', 'SNDS', 'VOIC', 'MUSI', 'OBJS', 'SCRP', 'STRT', 'CODE', 'BIND', 'STRS')
DEFAULT_CONF = {'range_units': 12288, 'ops_per_frame': 4000, 'ops_per_run': 2000}
RESIDENT = ORDER[:ORDER.index('BIND')]


def _hash8(row):
    path = row.get('path_pool') or ''
    if not row.get('resolved') or not path:
        return b'\0' * 8
    name = path.rsplit('/', 1)[-1]
    if not (name.startswith('a') and name.endswith('.wav') and len(name) == 21):
        raise ValueError('Not a media pool name: ' + path)
    return bytes.fromhex(name[1:17])


def _centis(row):
    return max(0, min(0xFFFF, int(round(row.get('seconds', 0) * 100))))


def write(program, compiled, binds, conf=None):
    """The file's bytes, and a size table {section: bytes}. CONF: config/mwscript.json's activation and budget."""
    p = program
    conf = dict(DEFAULT_CONF, **(conf or {}))
    confb = struct.pack('>IHH', conf['range_units'], conf['ops_per_frame'], conf['ops_per_run'])
    for c in compiled:
        p.string(c.name)
    sections = {}
    # scripts and code first: they intern their names
    code = bytearray()
    scrp = bytearray()
    for row, c in zip(p.scripts.rows, compiled):
        scrp += struct.pack('>HBBHHII', p.string(row['name']), c.nlocals, min(255, c.max_depth), c.flags, 0,
                            len(code), len(c.code))
        code += c.code
    glob = bytearray()
    for row in p.globals.rows:
        kind = TYPES[row['type']]
        v = row['value']
        whole = 0 if v != v else int(max(-2 ** 31, min(2 ** 31 - 1, v)))   # the record stores a float: clamp, NaN 0
        if kind == 0:
            whole = (whole + 32768) % 65536 - 32768
        value = struct.pack('>f', v) if kind == 2 else struct.pack('>i', whole)
        glob += struct.pack('>BBH', kind, 0, p.string(row['name'])) + value
    jrnl = b''.join(struct.pack('>H', p.string(r['name'])) for r in p.journal.rows)
    snds = bytearray()
    for r in p.sounds.rows:
        lo, hi = p.data.sound_range({'min': r.get('min', 0), 'max': r.get('max', 0)})
        snds += _hash8(r) + struct.pack('>HBBHHH', _centis(r), r.get('volume', 255) & 255,
                                        1 if r.get('resolved') else 0, min(lo, 0xFFFF), min(hi, 0xFFFF),
                                        r['name_string'])
    snds = bytes(snds)
    voic = b''.join(_hash8(r) + struct.pack('>HH', _centis(r), r['name_string']) for r in p.voices.rows)
    musi = b''.join(struct.pack('>BBH', r.get('track', 255) if r.get('resolved') else 255,
                                1 if r.get('resolved') else 0, r['name_string']) for r in p.music.rows)
    objs = b''.join(struct.pack('>IHHHH', r['reference'], r['id_string'],
                                0xFFFF if r['script'] is None else r['script'], min(r['placed'], 0xFFFF),
                                1 if r['kind'] == 'script' else 0) for r in p.objects.rows)
    bind = bytearray()
    for b in binds:
        if isinstance(b['cell'], tuple):
            cx, cy = b['cell']
            cell = struct.pack('>hh', max(-32768, min(32767, cx)), max(-32768, min(32767, cy)))
        else:
            cell = struct.pack('>Hh', b['cell'], 0)
        bind += struct.pack('>IHH', b['reference'], b['script'], b['flags']) + cell + struct.pack('>iii', *b['position'])
    strt = b''.join(struct.pack('>H', p.scripts.index[s]) for s in p.data.start_scripts if s in p.scripts.index)
    blob = bytearray()
    offsets = []
    for s in p.strings.rows:
        offsets.append(len(blob))
        blob += s.encode('cp1252', 'replace') + b'\0'
    strs = b''.join(struct.pack('>I', o) for o in offsets) + bytes(blob)
    sections = {'CONF': (confb, 1), 'STRS': (strs, len(p.strings)), 'GLOB': (bytes(glob), len(p.globals)), 'JRNL': (jrnl, len(p.journal)),
                'SNDS': (snds, len(p.sounds)), 'VOIC': (voic, len(p.voices)), 'MUSI': (musi, len(p.music)),
                'OBJS': (objs, len(p.objects)), 'SCRP': (bytes(scrp), len(compiled)),
                'CODE': (bytes(code), len(compiled)), 'BIND': (bytes(bind), len(binds)),
                'STRT': (strt, len(strt) // 2)}
    head = 16 + 16 * len(ORDER)
    out = bytearray()
    directory = bytearray()
    at = head
    body = bytearray()
    resident = head
    for tag in ORDER:
        data, rows = sections[tag]
        pad = (-len(data)) % 4
        if tag == 'BIND':
            resident = at
        directory += tag.encode('ascii') + struct.pack('>III', at, rows, len(data))
        body += data + b'\0' * pad
        at += len(data) + pad
    out += MAGIC + struct.pack('>HHII', VERSION, len(ORDER), head + len(body), resident) + directory + body
    sizes = {tag: len(sections[tag][0]) for tag in ORDER}
    sizes['resident'] = resident
    return bytes(out), sizes


def read(raw):
    """{'version', tag: bytes, tag+'_rows': n} of an AWMS1 file; raises ValueError on a bad file."""
    if raw[:4] != MAGIC:
        raise ValueError('Not an AWMS file')
    version, count, size, resident = struct.unpack_from('>HHII', raw, 4)
    if version != VERSION or size != len(raw):
        raise ValueError('Unsupported AWMS file')
    out = {'version': version, 'resident': resident}
    for i in range(count):
        tag, offset, rows, length = struct.unpack_from('>4sIII', raw, 16 + 16 * i)
        tag = tag.decode('ascii')
        if offset + length > len(raw):
            raise ValueError('AWMS section past the end: ' + tag)
        out[tag] = raw[offset:offset + length]
        out[tag + '_rows'] = rows
    return out


def strings(f):
    n = f['STRS_rows']
    blob = f['STRS'][4 * n:]
    out = []
    for i in range(n):
        o = struct.unpack_from('>I', f['STRS'], 4 * i)[0]
        out.append(blob[o:blob.index(b'\0', o)].decode('cp1252'))
    return out


def scripts(f):
    rows = []
    for i in range(f['SCRP_rows']):
        name, nl, depth, flags, _, off, length = struct.unpack_from('>HBBHHII', f['SCRP'], 16 * i)
        rows.append({'name': name, 'locals': nl, 'stack': depth, 'flags': flags,
                     'code': f['CODE'][off:off + length]})
    return rows


def decode(code):
    """[(offset, opcode name, [operands])] of one script's bytecode; raises ValueError on bad code."""
    out, i = [], 0
    while i < len(code):
        op = code[i]
        if op not in NAME:
            raise ValueError('bad opcode 0x%02x at %d' % (op, i))
        start = i
        i += 1
        args = []
        layout = LAYOUT[op]
        if layout == 'N':
            name, flags, nstr = struct.unpack_from('>HBB', code, i)
            i += 4
            strs = list(struct.unpack_from('>%dH' % nstr, code, i))
            i += 2 * nstr
            args = [name, flags, nstr] + strs
        else:
            for letter in layout:
                fmt = {'b': '>b', 'B': '>B', 'h': '>h', 'H': '>H', 'i': '>i', 'f': '>f'}[letter]
                args.append(struct.unpack_from(fmt, code, i)[0])
                i += struct.calcsize(fmt)
        out.append((start, NAME[op], args))
        if i > len(code):
            raise ValueError('operand past the end')
    return out


def disassemble(code, names=None):
    lines = []
    for at, name, args in decode(code):
        text = ' '.join(str(a) for a in args)
        if name == 'NOTYET' and names:
            text = '%s flags=%#x strings=%s' % (names[args[0]], args[1], [names[s] for s in args[3:]])
        if name in ('JMP', 'JZ'):
            text += ' -> %d' % (at + 3 + args[0])
        lines.append('%5d %-13s %s' % (at, name, text))
    return '\n'.join(lines)
