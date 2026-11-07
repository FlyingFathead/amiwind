# SPDX-License-Identifier: GPL-3.0-only
"""The AWMS1 file (id1/mwscript.awm): every compiled script and the tables they index. Big-endian.

  header   "AWMS" u16 version (1) u16 sections u32 file bytes u32 resident bytes
  directory, one row per section: tag[4] u32 offset u32 rows u32 bytes
  CONF  8 bytes: u32 activation range (game units) u16 opcodes per frame u16 opcodes per script run
  The sections up to CODE are what the engine keeps in memory (the "resident bytes" from the start of the file);
  BIND and STRS stay on disk: the bindings are read at each map change, a string only when one is logged.
  GLOB  8 bytes a global:   u8 type (0 short, 1 long, 2 float) u8 0 u16 name u32 initial value (raw cell)
  JRNL  2 bytes a topic:    u16 name
  SNDS  18 bytes a sound:   u8 pool name[8] u16 length (1/100 s) u8 volume u8 flags (1 mapped, 2 a dungeon ambience:
                            AMBIENCE_SOUNDS)
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
  NEWG  2 bytes a script a new game starts once (Main's CharGenState block: Startup, VampireCheck; v0.0.62,
        NPC-STORY-DISABLED-AT-START-42): u16 script; resident, optional (an older file: none)
  HELD  20 bytes an actor standing on an object a script disables (events.py; v0.0.62, SCRIPTED-EVENT-FALLING-MAGE-61),
        sorted by actor: u32 the actor's reference u32 the object's reference f32 x y z (the actor's placed position,
        game units); resident, optional (an older file: none)
  STRS  u32 offset per string, then the NUL-ended strings (cp1252)
  OACT, ACTB, AINV, AITM, ASPT, ASPL, ASPC, ASPE, AEFF, AMGE, AENC, APCS: the actor table (actors.py;
        docs/ACTOR_STATE.md)
  PCEL  the cells each GetPCCell name matches (resident; pccell_section below)
  PMOV  20 bytes a move of the player (PositionCell; resident; written in write() below)
  VISI  12 bytes an actor a PositionCell may bring into a room (resident; written in write() below)
  PLAC  12 bytes an object a Place call names (PlaceAtPC, PlaceAtMe, PlaceItem, PlaceItemCell; resident; write() below)
  TOPC  2 bytes a dialogue topic (DIAL type 0), sorted by folded id: u16 name (on disk; AddTopic hands the row)
  DRSC  12 bytes a dialogue result script, sorted: u32 FNV-1a of its text, u16 length, u16 speaker script, u16 its
        compiled script (_dlg_N), u16 flags (1 did not compile); on disk

A pool name is the 8 bytes of a converted file's name in the media catalogue: sound/pool/a<16 hex>.wav.
"""
import struct

from .opcodes import NAME, LAYOUT

MAGIC = b'AWMS'
VERSION = 1
TYPES = {'s': 0, 'l': 1, 'f': 2}
ORDER = ('CONF', 'GLOB', 'JRNL', 'SNDS', 'VOIC', 'MUSI', 'OBJS', 'SCRP', 'STRT', 'NEWG', 'HELD', 'OACT', 'PCEL', 'PMOV', 'SPFX', 'VISI', 'PLAC', 'CODE', 'BIND', 'STRS',
         'ACTB', 'AINV', 'AITM', 'ASPT', 'ASPL', 'TOPC', 'ASPC', 'ASPE', 'AEFF', 'AMGE', 'DRSC', 'AENC', 'APCS')
# The actor sections (actors.py, docs/ACTOR_STATE.md): OACT is resident (a script's target -> its actor row); the
# others stay on disk and are read a row at a time by the engine's actor state (aw_actorstate.c).
ACTOR_SECTIONS = ('OACT', 'ACTB', 'AINV', 'AITM', 'ASPT', 'ASPL', 'ASPC', 'ASPE', 'AEFF', 'AMGE', 'AENC', 'APCS')
DEFAULT_CONF = {'range_units': 12288, 'ops_per_frame': 4000, 'ops_per_run': 2000}
RESIDENT = ORDER[:ORDER.index('BIND')]
# The engine's limits (the interpreter's MAX_SCRIPTS and MAX_GLOBALS; tests/test_mwscript.py keeps them equal): a file over them is refused there and every
# script stays off (MWSCRIPT-REFUSED-SCRIPT-COUNT-58), so the builder refuses it here first.
ENGINE_MAX_SCRIPTS = 16384
ENGINE_MAX_GLOBALS = 512
# SNDS flags. 2: a dungeon ambience (TOMB-MUSIC-OVER-AMBIENT-60, decided for the project 5 November 2026): while a
# script loops one of these SOUN records (PlayLoopSound3D(VP) of the original's sound markers: sound_haunted and
# sound_spirit_whisper in the ancestral tombs, sound_cave_drip and sound_cave_wind in the caves) the engine rests the
# exploration music (aw_music.c AW_MusicAmbience); battle music still plays. Folded SOUN ids.
SOUND_MAPPED = 1
SOUND_AMBIENCE = 2
AMBIENCE_SOUNDS = frozenset(('haunted', 'spirit ambient voices', 'cave drip', 'cave wind'))


def check_limits(scripts, globals_):
    """Raise ValueError when the engine would refuse a file with this many scripts or globals."""
    if scripts > ENGINE_MAX_SCRIPTS:
        raise ValueError('%d scripts: the engine takes at most %d (the interpreter refuses more)' % (scripts, ENGINE_MAX_SCRIPTS))
    if globals_ > ENGINE_MAX_GLOBALS:
        raise ValueError('%d globals: the engine takes at most %d (the interpreter refuses more)' % (globals_, ENGINE_MAX_GLOBALS))


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


def pccell_section(table):
    """(bytes, rows) of PCEL: u32 offset (from the section's start) per row, then each row: u16 rooms, u16 outdoor
    cells (bit 15: the name also matches sDefaultCellname, an outdoor cell with no record; not used yet), u16 per
    room (its stable number), then s8 x, s8 y per outdoor cell; rows padded to 2 bytes."""
    rows = table.rows if table is not None else []
    head = bytearray()
    body = bytearray()
    for r in rows:
        head += struct.pack('>I', 4 * len(rows) + len(body))
        body += struct.pack('>HH', len(r['rooms']), len(r['outside']) | (0x8000 if r['wilderness'] else 0))
        body += b''.join(struct.pack('>H', n) for n in r['rooms'])
        body += b''.join(struct.pack('>bb', x, y) for x, y in r['outside'])
        if len(r['outside']) > 0x7FFF or len(r['rooms']) > 0xFFFF:
            raise ValueError('GetPCCell row too long: ' + r['name'])
    return bytes(head + body), len(rows)


def write(program, compiled, binds, conf=None):
    """The file's bytes, and a size table {section: bytes}. CONF: config/mwscript.json's activation and budget."""
    p = program
    check_limits(len(compiled), len(p.globals))
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
    folded = {i: k for k, i in p.sounds.index.items()}
    for i, r in enumerate(p.sounds.rows):
        lo, hi = p.data.sound_range({'min': r.get('min', 0), 'max': r.get('max', 0)})
        flags = (SOUND_MAPPED if r.get('resolved') else 0) | (SOUND_AMBIENCE if ' '.join(folded.get(i, '').split()) in AMBIENCE_SOUNDS else 0)
        snds += _hash8(r) + struct.pack('>HBBHHH', _centis(r), r.get('volume', 255) & 255,
                                        flags, min(lo, 0xFFFF), min(hi, 0xFFFF),
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
    newg = b''.join(struct.pack('>H', p.scripts.index[s]) for s in getattr(p.data, 'new_game', [])
                    if s in p.scripts.index)
    held_rows = getattr(p, 'held', None) or []
    held = b''.join(struct.pack('>IIfff', r['actor'], r['support'], *r['position'])
                    for r in sorted(held_rows, key=lambda r: r['actor']))
    pcel = pccell_section(getattr(p, 'pccells', None))
    # PMOV, 20 bytes a move of the player (PositionCell, v0.0.54): u8 kind (1 outdoors, 2 into a room) u8 0 u16 the
    # room map's name (string index, 0xFFFF outdoors) f32 x y z (outdoors the original's units; a room its map's own
    # units, as a door's arrival) f32 yaw (degrees)
    moves = getattr(p, 'moves', None)
    pmov = (b''.join(struct.pack('>BBHffff', r['kind'], 0, r['map'], *r['at'], r['yaw']) for r in moves.rows)
            if moves is not None else b'', len(moves) if moves is not None else 0)
    # SPFX (v0.0.57, SPELL-EFFECTS-57): 4 bytes a spell a Cast names (u16 first effect, u8 effects, u8 0), then 8
    # bytes an effect (u8 kind 0 drain 1 damage 2 restore 3 fortify, u8 stat, u16 seconds, u16 low, u16 high); resident
    spfx_rows = getattr(p, 'spfx', None)
    head, body, first = bytearray(), bytearray(), 0
    for r in (spfx_rows.rows if spfx_rows is not None else []):
        head += struct.pack('>HBB', first, len(r['effects']), 0)
        for e in r['effects']:
            body += struct.pack('>BBHHH', *e)
        first += len(r['effects'])
    spfx = (bytes(head + body), len(spfx_rows) if spfx_rows is not None else 0)
    # VISI (v0.0.62, MWSCRIPT-POSITIONCELL-ACTORS-62): 12 bytes an actor a PositionCell may bring into a room, sorted
    # by (room, reference): u32 the room's stable number, u32 the actor's reference, u16 its home room map's name
    # (string index; 0xFFFF outdoors or a room this build lacks), u16 0; resident
    visitors = getattr(p, 'visitors', None) or {}
    visi = (b''.join(struct.pack('>IIHH', room, ref, home, 0) for (room, ref), home in sorted(visitors.items())),
            len(visitors))
    # PLAC (v0.0.62, MWSCRIPT-PLACE-OBJECTS-62): 12 bytes an object the scripts' Place calls name, in the order of
    # codegen.Program.place_rows (sorted by folded id): u16 id, u16 the template's home room map (0xFFFF none), u32 the
    # template reference (0 none), u16 the record's script (0xFFFF none), u8 kind (0 an actor, 1 an item, 2 other),
    # u8 flags (1 the engine can make it); resident
    places = p.place_rows() if hasattr(p, 'place_rows') else []
    plac = (b''.join(struct.pack('>HHIHBB', r['id'], r['home'], r['template'], r['script'], r['kind'],
                                 1 if r['carried'] else 0) for r in places), len(places))
    # TOPC, 2 bytes a dialogue topic (v0.0.57): u16 name, sorted by folded id (AddTopic hands the row number); on disk
    rows = getattr(p, 'topic_rows', None)
    topics = sorted(rows(), key=rows().get) if rows else []
    names = getattr(p.data, 'topics', {})
    topc = (b''.join(struct.pack('>H', p.string(names[k])) for k in topics), len(topics))
    # DRSC (v0.0.58, DIALOGUE-COMPLETE-58): the dialogue's result scripts, 12 bytes a row sorted by (hash, length,
    # speaker script): u32 FNV-1a of the result text, u16 its length, u16 the speaker's script (0xFFFF none), u16 the
    # compiled _dlg_N script, u16 flags (1: did not compile); on disk, read when an answer is shown
    drsc_rows = []
    for r in getattr(p, 'results', []):
        sp = p.scripts.index.get(r['speaker_script'], 0xFFFF) if r['speaker_script'] else 0xFFFF
        index = p.scripts.index[r['script']]
        broken = 1 if compiled[index].error is not None else 0
        drsc_rows.append((r['hash'], min(0xFFFF, r['length']), sp, index, broken))
    drsc_rows.sort()
    drsc = (b''.join(struct.pack('>IHHHH', *r) for r in drsc_rows), len(drsc_rows))
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
                'STRT': (strt, len(strt) // 2), 'NEWG': (newg, len(newg) // 2), 'HELD': (held, len(held_rows)), 'PCEL': pcel, 'PMOV': pmov, 'TOPC': topc, 'SPFX': spfx,
                'VISI': visi, 'PLAC': plac, 'DRSC': drsc}
    actors = getattr(p, 'actors', None)
    if actors is not None:
        sections.update(actors.sections(p.objects.rows))
        # the actor rows interned strings: STRS is written again with them
        blob, offsets = bytearray(), []
        for s in p.strings.rows:
            offsets.append(len(blob))
            blob += s.encode('cp1252', 'replace') + b'\0'
        sections['STRS'] = (b''.join(struct.pack('>I', o) for o in offsets) + bytes(blob), len(p.strings))
    else:
        sections.update({tag: (b'', 0) for tag in ACTOR_SECTIONS})
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
        if layout in ('N', 'F'):
            # F (NOTYET): u16 the function's number first, then as N (MESSAGEBOX)
            number = struct.unpack_from('>H', code, i)[0] if layout == 'F' else None
            i += 2 if layout == 'F' else 0
            name, flags, nstr = struct.unpack_from('>HBB', code, i)
            i += 4
            strs = list(struct.unpack_from('>%dH' % nstr, code, i))
            i += 2 * nstr
            args = ([number] if layout == 'F' else []) + [name, flags, nstr] + strs
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
            text = '#%d %s flags=%#x strings=%s' % (args[0], names[args[1]], args[2], [names[s] for s in args[4:]])
        if name in ('JMP', 'JZ', 'JNEB', 'JCMPB'):
            size = {'JMP': 3, 'JZ': 3, 'JNEB': 4, 'JCMPB': 5}[name]
            text += ' -> %d' % (at + size + args[-1])
        lines.append('%5d %-13s %s' % (at, name, text))
    return '\n'.join(lines)
