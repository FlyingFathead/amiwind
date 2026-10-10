#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Known inputs: identify the user's own input files by size, SHA-256 and version.

One mechanism for every input the user supplies: the Morrowind masters and
archives (Morrowind/Tribunal/Bloodmoon .esm and .bsa), the optional Amiga
support libraries (--amiga-libs) and the Kickstart ROM. config/known-inputs.json
lists builds that were seen and tested; it holds metadata only (name, size,
SHA-256, version, source label, notes), never file contents.

Every input gets one verdict:
  known    size and SHA-256 match a table entry (its source label is shown)
  unknown  a readable file of the right kind that is not in the table
           (patched, modded or another release): used, with a warning
  invalid  not a file of that kind, or its version is unreadable: never used
  unchecked  --check-hashes off: used without verification

The input lockfile (amiwind-inputs.lock in the build workspace, private) keeps
path, size, mtime, birth time, SHA-256 and verdict of every input, so large
input sets that did not change are not hashed again (--check-hashes).
See docs/KNOWN_INPUTS.md.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from mwad import esm  # noqa: E402  (the shared Morrowind data helpers)
from mwad.esm import FormatError, sha256_file  # noqa: E402,F401
from mwad.paths import child_ci  # noqa: E402

TABLE_PATH = ROOT / 'config/known-inputs.json'
TABLE_SCHEMA = 'amiwind-known-inputs-v1'
LOCK_SCHEMA = 'amiwind-inputs-lock-v1'
LOCK_NAME = 'amiwind-inputs.lock'
LOCK_ENV = 'AMIWIND_INPUTS_LOCK'
POLICIES = ('warn', 'fail', 'require-known')
HASH_MODES = ('core', 'full', 'auto', 'off')
KINDS = ('tes3-master', 'tes3-archive', 'amiga-library', 'kickstart-rom')
ENTRY_FIELDS = ('kind', 'name', 'bytes', 'sha256', 'version', 'source', 'tested', 'notes')
# The Morrowind files the builder identifies; only the base pair is required.
# One list of game files (mwad.esm): Morrowind is required, Tribunal and Bloodmoon are optional.
GAME_FILES = tuple(item for index, (master, archive) in enumerate(zip(esm.GAME_MASTERS, esm.GAME_ARCHIVES))
                   for item in ((master, 'tes3-master', index == 0), (archive, 'tes3-archive', index == 0)))
CORE_NAMES = frozenset(name.casefold() for name, _, _ in GAME_FILES)
NOUNS = {'tes3-master': 'a Morrowind master file (TES3)', 'tes3-archive': 'a Morrowind archive (BSA)',
         'amiga-library': 'an Amiga library', 'kickstart-rom': 'a Kickstart ROM'}


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


# ---------------------------------------------------------------- the table

def load_table(path=TABLE_PATH):
    """config/known-inputs.json, checked; adds its own SHA-256 as 'table_sha256'."""
    raw = Path(path).read_bytes()
    table = json.loads(raw.decode('utf-8'))
    problems = check_table(table)
    if problems:
        raise ValueError('Known inputs table ' + str(path) + ': ' + '; '.join(problems))
    table['table_sha256'] = hashlib.sha256(raw).hexdigest()
    return table


def check_table(table):
    """Schema problems of a known-inputs table, as text; empty when valid."""
    problems = []
    if table.get('schema') != TABLE_SCHEMA:
        problems.append('schema is not ' + TABLE_SCHEMA)
    if not isinstance(table.get('revision'), int) or table['revision'] < 1:
        problems.append('revision must be a positive integer')
    seen = set()
    for number, entry in enumerate(table.get('entries', [])):
        where = f'entry {number}'
        missing = [field for field in ENTRY_FIELDS if field not in entry]
        if missing:
            problems.append(where + ' lacks ' + ', '.join(missing))
            continue
        if entry['kind'] not in KINDS:
            problems.append(where + ' has unknown kind ' + str(entry['kind']))
        if not re.fullmatch(r'[0-9a-f]{64}', str(entry['sha256'])):
            problems.append(where + ' sha256 is not 64 lower-case hex digits')
        if not isinstance(entry['bytes'], int) or entry['bytes'] <= 0:
            problems.append(where + ' bytes must be a positive integer')
        if not isinstance(entry['tested'], bool):
            problems.append(where + ' tested must be true or false')
        for field in ('name', 'version', 'source'):
            if not isinstance(entry[field], str) or not entry[field].strip():
                problems.append(where + ' ' + field + ' must be non-empty text')
        key = (entry['kind'], str(entry['name']).casefold(), entry['sha256'])
        if key in seen:
            problems.append(where + ' repeats an earlier entry')
        seen.add(key)
    if not table.get('entries'):
        problems.append('no entries')
    sources = {entry.get('source') for entry in table.get('entries', [])}
    for number, edition in enumerate(table.get('editions', [])):
        where = f'edition {number}'
        if not all(isinstance(edition.get(f), str) and edition[f] for f in ('name', 'masters_source')):
            problems.append(where + ' needs name and masters_source')
        elif edition['masters_source'] not in sources:
            problems.append(where + ' masters_source matches no entry source')
        if edition.get('bookart_ttf') not in ('all', 'none'):
            problems.append(where + ' bookart_ttf must be all or none')
        if not isinstance(edition.get('reference'), bool):
            problems.append(where + ' reference must be true or false')
    return problems


def match(table, kind, name, size, digest):
    """The table entry with this kind, name (any case), size and SHA-256, or None.

    ROM images are matched by size and SHA-256 alone: their file names vary."""
    for entry in table['entries']:
        if (entry['kind'] == kind and (kind == 'kickstart-rom' or entry['name'].casefold() == name.casefold())
                and entry['bytes'] == size and entry['sha256'] == digest):
            return entry
    return None


def table_identity(table):
    return {'revision': table['revision'], 'sha256': table.get('table_sha256')}


# --------------------------------------------------- Amiga hunk executables

HUNK = {'unit': 0x3E7, 'name': 0x3E8, 'code': 0x3E9, 'data': 0x3EA, 'bss': 0x3EB,
        'reloc32': 0x3EC, 'symbol': 0x3F0, 'debug': 0x3F1, 'end': 0x3F2, 'header': 0x3F3,
        'overlay': 0x3F5, 'break': 0x3F6, 'drel32': 0x3F7, 'reloc32short': 0x3FC}
HUNKF_ADVISORY = 1 << 29
RTC_MATCHWORD = 0x4AFC
RTF_AUTOINIT = 0x80
NT_LIBRARY = 9
RESIDENT_SIZE = 26
LIB_VERSION, LIB_REVISION = 20, 22


class HunkError(ValueError):
    pass


def parse_hunks(data):
    """Load an AmigaDOS hunk executable: hunk contents and RELOC32 targets.

    Returns (hunks, relocs): hunks is a list of {'type', 'data'} (BSS has
    zero-filled data), relocs maps (hunk, offset) to the hunk whose base the
    loader adds to the longword at that offset. Follows the AmigaDOS load file
    format (dos/doshunks.h); anything else raises HunkError."""
    position = 0

    def long():
        nonlocal position
        if position + 4 > len(data):
            raise HunkError('file ends inside a hunk')
        value = struct.unpack_from('>I', data, position)[0]
        position += 4
        return value

    def words(count):
        nonlocal position
        if position + 2 * count > len(data):
            raise HunkError('file ends inside a hunk')
        values = struct.unpack_from('>%dH' % count, data, position)
        position += 2 * count
        return values

    if len(data) < 24 or long() != HUNK['header']:
        raise HunkError('no hunk header')
    while True:  # resident library names (never used by executables, but legal)
        count = long()
        if count == 0:
            break
        position += 4 * count
    table_size, first, last = long(), long(), long()
    if last < first or last - first + 1 != table_size - first or table_size > 4096:
        raise HunkError('bad hunk table')
    sizes = []
    for _ in range(last - first + 1):
        value = long()
        if value >> 30 == 3:
            long()  # extra memory attribute longword
        sizes.append((value & 0x3FFFFFFF) * 4)
    hunks, relocs, current = [], {}, None
    while position < len(data) and len(hunks) < len(sizes):
        raw_type = long()
        kind = raw_type & 0x3FFFFFFF
        if raw_type & HUNKF_ADVISORY and kind not in HUNK.values():
            skip = long()
            position += 4 * skip
            continue
        kind &= 0x1FFFFFFF
        if kind in (HUNK['code'], HUNK['data'], HUNK['bss']):
            if current is not None:
                raise HunkError('hunk without HUNK_END')
            count = long()
            if kind == HUNK['bss']:
                body = bytes(4 * count)
            else:
                body = data[position:position + 4 * count]
                if len(body) != 4 * count:
                    raise HunkError('file ends inside a hunk')
                position += 4 * count
            allocated = sizes[len(hunks)]
            current = {'type': kind, 'data': body + bytes(max(0, allocated - len(body)))}
        elif kind == HUNK['reloc32']:
            while True:
                count = long()
                if count == 0:
                    break
                target = long()
                for _ in range(count):
                    relocs[(len(hunks), long())] = target
        elif kind in (HUNK['reloc32short'], HUNK['drel32']):
            used = 0
            while True:
                (count,) = words(1)
                used += 1
                if count == 0:
                    break
                (target,) = words(1)
                offsets = words(count)
                used += 1 + count
                for offset in offsets:
                    relocs[(len(hunks), offset)] = target
            if used % 2:
                words(1)  # pad to a longword
        elif kind == HUNK['symbol']:
            while True:
                count = long()
                if count == 0:
                    break
                position += 4 * (count & 0xFFFFFF) + 4
        elif kind in (HUNK['debug'], HUNK['name']):
            skip = long()
            position += 4 * skip
        elif kind == HUNK['end']:
            if current is None:
                raise HunkError('HUNK_END without a hunk')
            hunks.append(current)
            current = None
        elif kind == HUNK['break']:
            break
        else:
            raise HunkError(f'unsupported hunk type ${kind:X}')
    if current is not None:  # a final hunk may end at the end of the file
        hunks.append(current)
    if len(hunks) != len(sizes):
        raise HunkError(f'{len(hunks)} hunks loaded, header lists {len(sizes)}')
    for (hunk, offset), target in relocs.items():
        if target >= len(hunks) or offset + 4 > len(hunks[hunk]['data']):
            raise HunkError('relocation outside the hunks')
    return hunks, relocs


def _pointer(hunks, relocs, hunk, offset):
    """The (hunk, offset) a relocated longword points to, or None (absolute)."""
    if offset + 4 > len(hunks[hunk]['data']):
        return None
    target = relocs.get((hunk, offset))
    if target is None:
        return None
    return target, struct.unpack_from('>I', hunks[hunk]['data'], offset)[0]


def _string(hunks, where, limit=200):
    if where is None:
        return None
    hunk, offset = where
    body = hunks[hunk]['data']
    if offset >= len(body):
        return None
    end = body.find(b'\0', offset, offset + limit)
    text = body[offset:end if end >= 0 else offset + limit]
    return text.decode('latin-1').rstrip('\r\n')


def find_resident(hunks, relocs):
    """Every Resident (RomTag) structure: RTC_MATCHWORD followed by a relocated
    rt_MatchTag that points back to the match word itself (exec/resident.h)."""
    found = []
    for number, hunk in enumerate(hunks):
        body = hunk['data']
        for offset in range(0, len(body) - RESIDENT_SIZE + 1, 2):
            if struct.unpack_from('>H', body, offset)[0] != RTC_MATCHWORD:
                continue
            if _pointer(hunks, relocs, number, offset + 2) != (number, offset):
                continue
            flags, version, node_type, priority = struct.unpack_from('>BBBb', body, offset + 10)
            found.append({'hunk': number, 'offset': offset, 'flags': flags, 'version': version,
                          'type': node_type, 'priority': priority,
                          'name': _string(hunks, _pointer(hunks, relocs, number, offset + 14)),
                          'id_string': _string(hunks, _pointer(hunks, relocs, number, offset + 18)),
                          'init': _pointer(hunks, relocs, number, offset + 22)})
    return found


def init_struct_fields(hunks, relocs, where):
    """Word writes of an exec InitStruct() data table: {library offset: value}.

    Command byte ddssnnnn: dd 00 copy / 01 repeat (no offset), 10 byte offset,
    11 24-bit offset; ss 00 long, 01 word, 10 byte; nnnn+1 items. Word and
    long data are word aligned; each command ends word aligned (exec InitStruct)."""
    hunk, position = where
    body = hunks[hunk]['data']
    fields, target = {}, 0
    for _ in range(256):
        if position >= len(body):
            break
        command = body[position]
        position += 1
        if command == 0:
            return fields
        count = (command & 15) + 1
        mode, size = command >> 6, (command >> 4) & 3
        if mode == 2:
            target = body[position]
            position += 1
        elif mode == 3:
            target = int.from_bytes(body[position:position + 3], 'big')
            position += 3
        if size == 3:
            raise HunkError('bad InitStruct size')
        width = (4, 2, 1)[size]
        if width > 1 and position % 2:
            position += 1
        items = 1 if mode == 1 else count
        values = [int.from_bytes(body[position + i * width:position + (i + 1) * width], 'big') for i in range(items)]
        position += items * width
        for i in range(count):
            value = values[0 if mode == 1 else i]
            if width == 2:
                fields[target] = value
            target += width
        if position % 2:
            position += 1
    return fields


VER_PATTERN = re.compile(rb'\$VER:\s*([^\0\r\n]{1,200})')


def amiga_library_info(data, name=None):
    """Identity of an Amiga shared library file, read from its hunks.

    version: rt_Version of the library's Resident (RomTag) structure.
    revision: lib_Revision from the RTF_AUTOINIT data table when it sets one,
    otherwise the 'V.R' after the name in the RomTag id string or the $VER
    string, when its V equals rt_Version. 'valid' needs a resident NT_LIBRARY
    whose name matches the file name (exec opens libraries by that name)."""
    info = {'valid': False, 'reason': None, 'version': None, 'resident_version': None,
            'revision': None, 'revision_source': None, 'resident_name': None,
            'id_string': None, 'ver_string': None}
    found = VER_PATTERN.search(data)
    if found:
        info['ver_string'] = found.group(1).decode('latin-1').strip()
    try:
        hunks, relocs = parse_hunks(data)
    except HunkError as exc:
        info['reason'] = str(exc)
        return info
    libraries = [tag for tag in find_resident(hunks, relocs) if tag['type'] == NT_LIBRARY]
    if not libraries:
        info['reason'] = 'no resident library (RomTag) structure'
        return info
    tag = libraries[0]
    if name is not None:
        named = [t for t in libraries if (t['name'] or '').casefold() == name.casefold()]
        if not named:
            info.update(resident_name=tag['name'], id_string=tag['id_string'], resident_version=tag['version'])
            info['reason'] = f'resident name {tag["name"]!r} is not {name}'
            return info
        tag = named[0]
    info.update(resident_name=tag['name'], id_string=tag['id_string'], resident_version=tag['version'])
    version = tag['version']
    if tag['flags'] & RTF_AUTOINIT and tag['init'] is not None:
        hunk, offset = tag['init']
        data_table = _pointer(hunks, relocs, hunk, offset + 8)
        if data_table is not None:
            try:
                fields = init_struct_fields(hunks, relocs, data_table)
            except HunkError:
                fields = {}
            if LIB_REVISION in fields:
                info['revision'], info['revision_source'] = fields[LIB_REVISION], 'library data table'
    for source, text in (('RomTag id string', tag['id_string']), ('$VER string', info['ver_string'])):
        if info['revision'] is None and text:
            for major, minor in re.findall(r'(?<![\d.])(\d+)\.(\d+)(?![\d.])', text):
                if int(major) == version:
                    info['revision'], info['revision_source'] = int(minor), source
                    break
    info['version'] = f'{version}.{info["revision"]}' if info['revision'] is not None else str(version)
    info['valid'] = True
    return info


# ------------------------------------------------- Morrowind and Kickstart

def tes3_master_info(path):
    """TES3 header (HEDR) of a master: format version, file type, author,
    description, record count and masters. Reads the first record only."""
    info = {'valid': False, 'reason': None, 'version': None}
    with open(path, 'rb') as stream:
        header = stream.read(16)
        if len(header) != 16 or header[:4] != b'TES3':
            info['reason'] = 'no TES3 header record'
            return info
        length = struct.unpack_from('<I', header, 4)[0]
        if length > 1024 * 1024:
            info['reason'] = 'TES3 header record too large'
            return info
        body = stream.read(length)
    if len(body) != length:
        info['reason'] = 'file ends inside the TES3 header record'
        return info
    masters, hedr = [], None
    # The shared subrecord walk raises FormatError on a truncated header or an overrunning subrecord.
    for tag, value in esm.subrecords(body):
        if tag == 'HEDR' and len(value) == 300:
            hedr = value
        elif tag == 'MAST':
            masters.append(esm.string(value, 'TES3 MAST', errors='replace'))
    if hedr is None:
        info['reason'] = 'no 300-byte HEDR in the TES3 header'
        return info
    version, file_type = struct.unpack_from('<fI', hedr, 0)
    text = lambda raw: ' '.join(esm.string(raw, errors='replace').split())
    info.update(valid=True, version=f'{version:.2f}', file_type=file_type,
                author=text(hedr[8:40]), description=text(hedr[40:296]),
                records=struct.unpack_from('<I', hedr, 296)[0], masters=masters)
    return info


def tes3_archive_info(path):
    """Morrowind BSA header: version $100, hash table offset and file count."""
    info = {'valid': False, 'reason': None, 'version': None}
    size = Path(path).stat().st_size
    with open(path, 'rb') as stream:
        header = stream.read(12)
    if len(header) != 12:
        info['reason'] = 'shorter than a BSA header'
        return info
    version, hash_offset, files = struct.unpack('<III', header)
    if version != 0x100:
        info['reason'] = 'not a Morrowind BSA (version is not $100)'
        return info
    if 12 + hash_offset + 8 * files > size or files > 1_000_000:
        info['reason'] = 'BSA tables exceed the file'
        return info
    info.update(valid=True, format='TES3 BSA ($100)', files=files)
    return info


def kickstart_info(path):
    """A Kickstart ROM image: 256 or 512 KiB with the $1111/$1114 start word
    (version.revision at offset 12), or an Amiga Forever encrypted image."""
    info = {'valid': False, 'reason': None, 'version': None}
    size = Path(path).stat().st_size
    with open(path, 'rb') as stream:
        head = stream.read(16)
    if head[:11] == b'AMIROMTYPE1' and size - 11 in (262144, 524288):
        info.update(valid=True, version='encrypted', encrypted=True)
    elif size in (262144, 524288) and head[:2] in (b'\x11\x11', b'\x11\x14'):
        version, revision = struct.unpack_from('>HH', head, 12)
        info.update(valid=True, version=f'{version}.{revision}', encrypted=False)
    else:
        info['reason'] = 'not a 256/512 KiB Kickstart image'
    return info


def identify(kind, path, name=None):
    if kind == 'amiga-library':
        return amiga_library_info(Path(path).read_bytes(), name)
    if kind == 'tes3-master':
        try:
            return tes3_master_info(path)
        except FormatError as exc:
            return {'valid': False, 'reason': str(exc), 'version': None}
    if kind == 'tes3-archive':
        return tes3_archive_info(path)
    if kind == 'kickstart-rom':
        return kickstart_info(path)
    raise ValueError('Unknown input kind: ' + str(kind))


# ---------------------------------------------------------------- verdicts

def classify(kind, name, path, digest, table, required=False, size=None, info=None):
    """The verdict record of one input file (see the module docstring)."""
    path = Path(path)
    size = path.stat().st_size if size is None else size
    info = identify(kind, path, name) if info is None else info
    record = {'kind': kind, 'name': name, 'path': str(path), 'bytes': size, 'sha256': digest,
              'version': info.get('version'), 'identity': info, 'required': required,
              'label': None, 'tested': None}
    if not info['valid']:
        record['verdict'] = 'invalid'
        if kind == 'amiga-library':
            text = 'invalid: not an Amiga library or version unreadable (not used)'
        else:
            text = f'invalid: not {NOUNS[kind]} (not used)'
        record['message'] = text + ': ' + str(info['reason'])
        return record
    if digest is None:
        record['verdict'] = 'unchecked'
        record['message'] = 'unchecked: --check-hashes off (used without verification)'
        return record
    entry = match(table, kind, name, size, digest)
    if entry is not None:
        record.update(verdict='known', label=entry['source'], tested=entry['tested'])
        record['message'] = 'known: ' + entry['source'] + (' (tested)' if entry['tested'] else ' (listed, not tested)')
        return record
    record['verdict'] = 'unknown'
    shown = (' v' + info['version']) if info.get('version') else ''
    if kind == 'amiga-library':
        record['message'] = f'unknown build of {name}{shown} (not tested; used)'
    else:
        record['message'] = f'unknown version of {name}{shown} (patched or modded? not tested; used)'
    return record


def line(record):
    """One report line: name, size, version, SHA-256 and the verdict."""
    digest = record['sha256'] or 'not hashed'
    version = (' v' + record['version']) if record.get('version') else ''
    return f"{record['name']}{version} ({record['bytes']:,} bytes) SHA-256 {digest}: {record['message']}"


def enforce(records, policy, what):
    """Apply a policy; returns warning lines, raises ValueError to stop the build.

    warn: unknown/unchecked files are used with a warning; an invalid file is
    not used (an invalid required file stops the build).
    fail: as warn, but any invalid file stops the build.
    require-known: anything but a known file stops the build."""
    if policy not in POLICIES:
        raise ValueError(f'Unknown {what} policy: {policy}')
    stop, warnings = [], []
    for record in records:
        verdict = record['verdict']
        if verdict == 'known':
            continue
        if (verdict == 'invalid' and (record.get('required') or policy != 'warn')) or \
                (verdict in ('unknown', 'unchecked') and policy == 'require-known'):
            stop.append(record)
        else:
            warnings.append(f'{what}: ' + line(record))
    if stop:
        raise ValueError(f'{what} policy {policy} stops the build:\n  - ' + '\n  - '.join(line(r) for r in stop)
                         + '\nSee docs/KNOWN_INPUTS.md (known versions and the --*-policy options).')
    return warnings


def check_game_data(data, lock, policy='warn', table=None, input_report=None):
    """Verdicts of the Morrowind masters and archives in DATA (Data Files).

    Morrowind.esm/.bsa are required; the expansion files are identified when
    present. Returns {'policy', 'files', 'absent', 'warnings'}; raises
    ValueError when the policy stops the build."""
    table = table or lock.table
    data = Path(data)
    present = []
    absent = []
    for name, kind, required in GAME_FILES:
        # child_ci: one case-insensitive lookup; two names differing only by case are an error.
        path = child_ci(data, name, required=required)
        if path is None:
            absent.append(name)
            continue
        if not path.is_file():
            raise ValueError(f'Expected a regular file: {name} in {data}')
        present.append((name, kind, required, path))
    lock.prepare([path for _, _, _, path in present], core=True)
    records = []
    for name, kind, required, path in present:
        record = classify(kind, name, path, lock.sha256(path), table, required=required)
        lock.note_verdict(path, record, table)
        records.append(record)
    warnings = enforce(records, policy, 'Game data')
    report = {'policy': policy, 'files': records, 'absent': absent, 'warnings': warnings,
              'known_table': table_identity(table)}
    report['edition'] = identify_edition(report, input_report, table)
    return report


BOOKART_TTF = ('Magic Cards.ttf', 'GOTHIC.TTF', 'daedric_runes.ttf')


def identify_edition(report, input_report, table):
    """Name the edition from the masters' verdicts plus the BookArt TrueType
    fonts, and record which font source and loose overrides the build used.

    Both GOTY editions are supported: neither is a warning. The masters alone
    cannot tell GOG from Steam (they are identical); the fonts can
    (docs/MORROWIND_EDITIONS.md, BUILD-EDITION-DIFFERENCES-32)."""
    fonts = (input_report or {}).get('font_sources') or {}
    present = dict(fonts.get('preferred_ttf') or {})
    families = {key: item.get('selected') for key, item in (fonts.get('families') or {}).items()}
    overrides = (input_report or {}).get('loose_overrides')
    base = {r['name'].casefold(): r for r in report['files']}
    core = [base.get('morrowind.esm'), base.get('morrowind.bsa')]
    result = {'edition': None, 'reference': False, 'bookart_ttf': present, 'font_sources': families,
              'loose_overrides': overrides, 'expansions_absent': list(report.get('absent', []))}
    if not all(r and r['verdict'] == 'known' for r in core) or core[0]['label'] != core[1]['label']:
        result['edition'] = 'unknown edition (Morrowind.esm/.bsa not a known pair)'
        return result
    found = sum(1 for name in BOOKART_TTF if present.get(name))
    fonts_state = 'all' if found == len(BOOKART_TTF) else 'none' if found == 0 else 'some'
    for edition in table.get('editions', []):
        if edition['masters_source'] == core[0]['label'] and edition['bookart_ttf'] == fonts_state:
            result.update(edition=edition['name'], reference=edition['reference'])
            break
    else:
        missing = [name for name in BOOKART_TTF if not present.get(name)]
        result['edition'] = core[0]['label'] + (' (BookArt fonts incomplete: missing ' + ', '.join(missing) + ')'
                                                 if missing else '')
    return result


def report_lines(report, title='Game data'):
    if not report:
        return []
    lines = [f"{title} (policy {report['policy']}):"]
    edition = report.get('edition')
    if edition:
        lines.append('  Edition: ' + edition['edition'] + (' [reference]' if edition['reference'] else ''))
        if edition['font_sources']:
            lines.append('  Font sources: ' + ', '.join(f'{k} {v}' for k, v in sorted(edition['font_sources'].items())))
        overrides = edition.get('loose_overrides')
        if overrides is not None:
            by = ', '.join(f'{k} {v}' for k, v in overrides['by_folder'].items())
            lines.append(f"  Loose files shadowing Morrowind.bsa copies: {overrides['total']}" + (f' ({by})' if by else ''))
    lines.extend('  ' + line(record) for record in report['files'])
    if report.get('absent'):
        lines.append('  not present (optional): ' + ', '.join(report['absent']))
    return lines


# ---------------------------------------------------------------- the lock

def file_stamp(path):
    """Size, mtime (ns) and birth time (ns) where the platform really has one.

    Birth time: st_birthtime (Windows with Python 3.12+, macOS, BSD); on
    Windows before 3.12 st_ctime is the creation time. On Linux st_ctime is
    the inode change time, not creation, so it is never used; Python's os.stat
    does not read statx btime there, so Linux records null. Docker bind mounts
    may also hide it. A null birth time is ignored when comparing."""
    st = os.stat(path)
    birth = getattr(st, 'st_birthtime_ns', None)
    if birth is None and getattr(st, 'st_birthtime', None) is not None:
        birth = int(st.st_birthtime * 1_000_000_000)
    if birth is None and sys.platform == 'win32':
        birth = st.st_ctime_ns
    return {'bytes': st.st_size, 'mtime_ns': st.st_mtime_ns, 'birth_ns': birth}


def same_stamp(old, new):
    """Size and mtime equal, and birth time equal when both sides have one."""
    if old.get('bytes') != new['bytes'] or old.get('mtime_ns') != new['mtime_ns']:
        return False
    a, b = old.get('birth_ns'), new.get('birth_ns')
    return a is None or b is None or a == b


def lock_key(path):
    """Identity of an input in the lock: symlinks resolved, case-folded where the filesystem is."""
    return os.path.normcase(os.path.realpath(os.fspath(path)))


class InputLock:
    """amiwind-inputs.lock: the one place input hashes come from in a build.

    Modes (--check-hashes):
      core  the core inputs (Morrowind/Tribunal/Bloodmoon .esm/.bsa, Amiga
            libraries, Kickstart ROM) are hashed in full every build; other
            inputs (loose music, sound, fonts, video...) are trusted when size,
            mtime and birth time are unchanged, otherwise rehashed (default)
      full  every input is hashed (release builds)
      auto  every input is trusted when unchanged, otherwise rehashed
      off   nothing is hashed; inputs are 'unchecked' (loud warning)
    Stats and hashes run in a thread pool. path=None keeps the lock in memory."""

    def __init__(self, path, mode='core', table=None, workers=None, hasher=sha256_file):
        if mode not in HASH_MODES:
            raise ValueError('Unknown --check-hashes mode: ' + str(mode))
        self.path = Path(path) if path is not None else None
        self.mode = mode
        self.table = table if table is not None else load_table()
        self.workers = workers or min(8, os.cpu_count() or 1)
        self._hasher = hasher
        self._count = threading.Lock()
        self.hash_calls = 0
        self.entries = {}
        self.current = {}
        self.messages = []
        self.changed = []
        self.trusted = 0
        self.hashed = 0
        self.previous_table = None
        if self.path is not None and self.path.is_file():
            self._load()

    def _load(self):
        try:
            record = json.loads(self.path.read_text(encoding='utf-8'))
            if record.get('schema') != LOCK_SCHEMA or not isinstance(record.get('files'), dict):
                raise ValueError('unexpected schema')
            for key, entry in record['files'].items():
                if not isinstance(entry, dict) or not re.fullmatch(r'[0-9a-f]{64}', str(entry.get('sha256') or '')) \
                        or not isinstance(entry.get('bytes'), int) or not isinstance(entry.get('mtime_ns'), int):
                    raise ValueError('bad entry for ' + key)
            self.entries = record['files']
            self.previous_table = record.get('known_table')
        except (OSError, ValueError, UnicodeError) as exc:
            aside = self.path.with_name(self.path.name + '.unreadable-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'))
            try:
                self.path.replace(aside)
                where = 'moved aside to ' + aside.name
            except OSError:
                where = 'left in place'
            self.messages.append(f'Input lock {self.path} was unreadable ({exc}); {where}; '
                                 'every input is hashed again and a new lock is written')
            self.entries = {}
        if self.previous_table is not None and self.previous_table != table_identity(self.table):
            self.messages.append('Known inputs table changed since the lock was written: every verdict is re-evaluated')

    def _hash(self, path):
        with self._count:
            self.hash_calls += 1
        return self._hasher(path)

    @staticmethod
    def is_core(path):
        """Core inputs: the masters and archives, Amiga libraries, ROM images."""
        name = Path(path).name.casefold()
        return name in CORE_NAMES or name.endswith(('.library', '.rom'))

    def prepare(self, paths, core=False):
        """Stat PATHS in parallel; hash, in parallel, the ones this mode does not trust.

        core=True (or a core file name) means: in mode 'core' always hash."""
        todo, seen = [], set()
        for path in paths:
            key = lock_key(path)
            entry = self.current.get(key)
            core_here = core or self.is_core(path)
            if entry is not None and not (core_here and self.mode == 'core' and entry['checked'].startswith('trusted')):
                continue
            if key not in seen:
                seen.add(key)
                todo.append((key, Path(path), core_here))
        if not todo:
            return
        with ThreadPoolExecutor(self.workers) as pool:
            stamps = list(pool.map(lambda item: file_stamp(item[1]), todo))
        rehash = []
        for (key, path, core_here), stamp in zip(todo, stamps):
            old = self.entries.get(key)
            if key in self.current:  # trusted earlier as a non-core input
                self.trusted -= 1
                del self.current[key]
            trust = self.mode == 'auto' or (self.mode == 'core' and not core_here)
            if self.mode == 'off':
                self.current[key] = {**stamp, 'sha256': None, 'checked': 'off'}
            elif trust and old and same_stamp(old, stamp):
                self.current[key] = {**old, **stamp, 'checked': 'trusted: size and times unchanged'}
                self.trusted += 1
            else:
                if old and not same_stamp(old, stamp):
                    self.changed.append(key)
                rehash.append((key, path, stamp, old))
        with ThreadPoolExecutor(self.workers) as pool:
            digests = list(pool.map(lambda item: self._hash(item[1]), rehash))
        for (key, path, stamp, old), digest in zip(rehash, digests):
            self.hashed += 1
            self.current[key] = {**stamp, 'sha256': digest, 'checked': 'hashed', 'hashed_at': now()}
            if old and not same_stamp(old, stamp):
                state = 'content changed' if old.get('sha256') != digest else 'content unchanged'
                self.messages.append(f'Input changed since the last build (size/time differ): {key}; '
                                     f'rehashed and verified again ({state})')

    def sha256(self, path):
        """SHA-256 of an input (None with --check-hashes off)."""
        key = lock_key(path)
        if key not in self.current:
            self.prepare([path])
        return self.current[key]['sha256']

    def note_verdict(self, path, record, table=None):
        entry = self.current.setdefault(lock_key(path), {})
        entry.update(kind=record['kind'], verdict=record['verdict'], label=record['label'],
                     version=record.get('version'), known_table=table_identity(table or self.table))

    def summary(self):
        return {'mode': self.mode, 'lock': str(self.path) if self.path else None,
                'inputs': len(self.current), 'hashed': self.hashed, 'trusted': self.trusted,
                'changed': list(self.changed), 'messages': list(self.messages),
                'known_table': table_identity(self.table)}

    def summary_lines(self):
        return hash_lines(self.summary())

    def save(self):
        """Write the lock (LF, atomic); entries of other inputs are kept."""
        if self.path is None:
            return None
        files = {**self.entries, **{k: v for k, v in self.current.items() if v.get('sha256')}}
        record = {'schema': LOCK_SCHEMA, 'written_at': now(), 'check_hashes': self.mode,
                  'known_table': table_identity(self.table),
                  'note': 'Private: hashes of your own input files. Never share or ship this file.',
                  'files': dict(sorted(files.items()))}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(self.path.name + '.tmp')
        temporary.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8', newline='\n')
        temporary.replace(self.path)
        return self.path


def hash_lines(summary):
    """Report lines of an input-lock summary (InputLock.summary())."""
    lines = [f"Input hashes (--check-hashes {summary['mode']}): {summary['inputs']} inputs, {summary['hashed']} hashed, "
             f"{summary['trusted']} trusted unchanged; known table revision {summary['known_table']['revision']}"]
    if summary['mode'] == 'off':
        lines.append('WARNING: --check-hashes off: input files were NOT verified; this build cannot be '
                     'compared with a known edition or a release')
    lines.extend('  ' + message for message in summary.get('messages', []))
    return lines


def summary_lines(block):
    """End-of-build lines of the receipt's known_inputs block."""
    if not block:
        return []
    lines = hash_lines(block['check_hashes']) if block.get('check_hashes') else []
    lines.extend(report_lines(block.get('game_data')))
    amiga = block.get('amiga_libs')
    if amiga:
        lines.append(f"Amiga libraries (policy {amiga['policy']}):")
        lines.extend('  ' + line(record) for record in amiga['files'])
    if block.get('kickstart'):
        lines.append('Kickstart ROM: ' + line(block['kickstart']))
    return lines


_SHARED = {}


def input_sha256(path):
    """SHA-256 of a user input file for cache keys in any build stage.

    The build exports its lock as AMIWIND_INPUTS_LOCK; when the lock holds this
    file with the same size and times, its hash is the answer (one source of
    truth, no second full hash). Otherwise the file is hashed."""
    lock_path = os.environ.get(LOCK_ENV)
    if lock_path:
        if lock_path not in _SHARED:
            try:
                record = json.loads(Path(lock_path).read_text(encoding='utf-8'))
                _SHARED[lock_path] = record.get('files', {}) if record.get('schema') == LOCK_SCHEMA else {}
            except (OSError, ValueError):
                _SHARED[lock_path] = {}
        entry = _SHARED[lock_path].get(lock_key(path))
        if entry and entry.get('sha256') and same_stamp(entry, file_stamp(path)):
            return entry['sha256']
    return sha256_file(path)
