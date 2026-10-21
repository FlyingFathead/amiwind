#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Store repeated content of the boot payload once, as the last step before the disk layout.

Two methods, each off by default until a playtest image shows the game unchanged (build.py --file-aliases,
--shared-skins; docs/PAYLOAD_SHARING.md):

file aliases (IMAGE-DUPLICATE-FILES-46): byte-identical files (SHA-256 of the content) of the kinds the engine
    opens through its file search (models, sounds, sprites, animation layouts and item tags: COM_FindFile) are
    stored once. The other names go into id1/file-aliases.txt; when the
    engine finds no file of a name it looks the name up there and opens the stored copy (aw_file_alias.c). Amiga
    FFS has no links, so a name table is the only way to give one stored file several names.

shared skins (IMAGE-ACTOR-SKIN-REPEATS-46): a single-skin actor model (progs/a_*.mdl) whose skin pixels another
    model repeats stores them once in progs/skins/<16 hex>.awk; the model keeps its header and says where its
    skin is (skin type "AWSK", the 16 hex digits of the pixels' SHA-256, the pixel count) in place of the
    pixels. The engine's alias loaders read the pixels from that file into the same place (model.c), so the
    decoded model is byte-identical and the game holds no more memory than before. expand_shared_skin is the
    reference of what the engine rebuilds.

Usage (read only, a dry measurement over a staged payload; nothing is written):

    payload_share.py measure BOOT [--file-aliases] [--shared-skins] [--jobs N] [--json OUT]
"""
import argparse
import fnmatch
import hashlib
import json
from pathlib import Path
import struct
import sys

ALIAS_FILE = 'file-aliases.txt'                        # id1-relative
ALIAS_MAGIC = 'AWALIAS1'
# Kinds the engine opens through COM_FindFile. Not the soundtrack (.mws): aw_music.c opens its tracks by path.
ALIAS_KINDS = ('.mdl', '.wav', '.spr', '.anm', '.tag')
ALIAS_MIN_BYTES = 4096        # smaller repeats cost the game more table memory than they save on disk
ALIAS_NAME_LIMIT = 63         # MAX_QPATH 64 with its terminator

SKIN_DIR = 'progs/skins'
SKIN_EXT = '.awk'
SKIN_PATTERNS = ('progs/a_*.mdl',)
SKIN_TYPE = b'AWSK'           # skin type of a shared skin; read little-endian it is 0x4B535741
SKIN_SINGLE = 0
MDL_HEADER = 84
SKIN_REF = 4 + 16 + 4         # type, 16 hex digits, pixel count: in place of type + pixels
SKIN_FULL_LIMIT = 512 * 1024  # the engine's alias file staging limit (model.c AW_ALIAS_STAGING_LIMIT)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def _hashes(paths, jobs):
    try:
        from build_parallel import hash_files
        return hash_files(paths, jobs)
    except ImportError:                                  # standalone measurement
        return [sha256(Path(p).read_bytes()) for p in paths]


# ---- shared skins

def skin_of(raw):
    """(offset, pixel bytes) of a single-skin model's pixels, or None for anything else (groups, several skins,
    a shared skin already, another format)."""
    if len(raw) < MDL_HEADER + 4 or raw[:4] != b'IDPO' or struct.unpack_from('<i', raw, 4)[0] != 6:
        return None
    count, width, height = struct.unpack_from('<3i', raw, 48)
    if count != 1 or width < 1 or height < 1 or width & 3:
        return None
    if raw[MDL_HEADER:MDL_HEADER + 4] != struct.pack('<i', SKIN_SINGLE):
        return None
    pixels = width * height
    if MDL_HEADER + 4 + pixels > len(raw):
        return None
    return MDL_HEADER + 4, pixels


def skin_name(digest):
    return SKIN_DIR + '/' + digest[:16] + SKIN_EXT


def shared_model(raw, digest):
    """The stored form of RAW (a single-skin model) whose pixels live in skin_name(DIGEST)."""
    at, pixels = skin_of(raw)
    return raw[:MDL_HEADER] + SKIN_TYPE + digest[:16].encode('ascii') + struct.pack('<I', pixels) + raw[at + pixels:]


def is_shared(raw):
    return len(raw) >= MDL_HEADER + SKIN_REF and raw[:4] == b'IDPO' and raw[MDL_HEADER:MDL_HEADER + 4] == SKIN_TYPE


def expand_shared_skin(stored, read_skin):
    """The model the engine decodes from a stored shared-skin model: READ_SKIN(id1-relative name) gives the
    skin file's bytes. Raises ValueError like the engine refuses."""
    if not is_shared(stored):
        raise ValueError('Not a shared-skin model')
    ref = stored[MDL_HEADER + 4:MDL_HEADER + 20].decode('ascii')
    if any(c not in '0123456789abcdef' for c in ref):
        raise ValueError('Invalid shared skin name')
    pixels = struct.unpack_from('<I', stored, MDL_HEADER + 20)[0]
    width, height = struct.unpack_from('<2i', stored, 52)
    if pixels != width * height:
        raise ValueError('Shared skin size differs from the model header')
    skin = read_skin(SKIN_DIR + '/' + ref + SKIN_EXT)
    if len(skin) != pixels:
        raise ValueError('Shared skin file has the wrong size')
    return stored[:MDL_HEADER] + struct.pack('<i', SKIN_SINGLE) + skin + stored[MDL_HEADER + SKIN_REF:]


def plan_skins(id1, patterns=SKIN_PATTERNS):
    """{pixel SHA-256: [id1-relative model paths]} of skins two or more matching models repeat (sorted)."""
    id1 = Path(id1)
    users = {}
    for path in sorted(id1.rglob('*.mdl')):
        rel = path.relative_to(id1).as_posix()
        if not any(fnmatch.fnmatchcase(rel, p) for p in patterns):
            continue
        raw = path.read_bytes()
        found = skin_of(raw)
        if not found or len(raw) > SKIN_FULL_LIMIT:
            continue
        at, pixels = found
        users.setdefault(sha256(raw[at:at + pixels]), []).append(rel)
    groups = {d: paths for d, paths in users.items() if len(paths) > 1}
    prefixes = {}
    for digest in groups:
        if prefixes.setdefault(digest[:16], digest) != digest:
            raise ValueError('Two shared skins with the same 16-digit name: ' + digest[:16])
    return dict(sorted(groups.items()))


def apply_skins(id1, groups, write=True):
    """Store each skin of GROUPS once and rewrite its models (WRITE=False: count only). Returns the record."""
    id1 = Path(id1)
    before = after = 0
    for digest, paths in groups.items():
        skin_bytes = None
        for rel in paths:
            raw = (id1 / rel).read_bytes()
            at, pixels = skin_of(raw)
            pixels_raw = raw[at:at + pixels]
            if sha256(pixels_raw) != digest:
                raise ValueError('Skin of %s changed while sharing' % rel)
            stored = shared_model(raw, digest)
            if expand_shared_skin(stored, lambda name: pixels_raw) != raw:
                raise ValueError('Shared-skin form of %s does not rebuild the model' % rel)
            before += len(raw)
            after += len(stored)
            skin_bytes = pixels_raw
            if write:
                (id1 / rel).write_bytes(stored)
        after += len(skin_bytes)
        if write:
            target = id1 / skin_name(digest)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(skin_bytes)
    return {'skins': len(groups), 'models': sum(len(p) for p in groups.values()),
            'bytes_before': before, 'bytes_after': after, 'bytes_saved': before - after,
            'files_added': len(groups)}


# ---- file aliases

def table_name(name):
    """True for a name the engine's alias table can carry: printable ASCII, no TAB, at most 63 bytes."""
    return 0 < len(name) <= ALIAS_NAME_LIMIT and all(32 <= ord(c) < 127 for c in name)


def fold_key(name):
    """The engine's alias order (common.c COM_AliasCompare): bytes with a-z read as A-Z."""
    return bytes(c - 32 if 97 <= c <= 122 else c for c in name.encode('ascii'))


def plan_aliases(id1, kinds=ALIAS_KINDS, min_bytes=ALIAS_MIN_BYTES, jobs=None):
    """[(stored id1-relative path, [alias paths], bytes)] of byte-identical files: the stored copy is the
    first name in the engine's order; names the table cannot carry stay files of their own."""
    id1 = Path(id1)
    paths = [p for p in sorted(id1.rglob('*')) if p.is_file() and p.suffix.lower() in kinds
             and p.stat().st_size >= min_bytes and p.relative_to(id1).as_posix() != ALIAS_FILE]
    by_hash = {}
    for path, digest in zip(paths, _hashes(paths, jobs)):
        by_hash.setdefault(digest, []).append(path.relative_to(id1).as_posix())
    groups = []
    for digest, names in sorted(by_hash.items()):
        names = sorted((n for n in names if table_name(n)), key=lambda n: (fold_key(n), n))
        if len(names) < 2:
            continue
        groups.append((names[0], names[1:], (id1 / names[0]).stat().st_size))
    groups.sort(key=lambda g: fold_key(g[0]))
    return groups


def alias_table(groups):
    """The text of id1/file-aliases.txt (common.c COM_InitFileAliases): 'AWALIAS1 <stored> <aliases>', one
    stored name per line, then '<alias>TAB<stored index>' per alias in the engine's order (ASCII, LF)."""
    aliases = sorted(((name, index) for index, (_, names, _) in enumerate(groups) for name in names),
                     key=lambda row: fold_key(row[0]))
    keys = [fold_key(name) for name, _ in aliases]
    if len(set(keys)) != len(keys):
        raise ValueError('Two alias names differ only in case')
    lines = ['%s %d %d' % (ALIAS_MAGIC, len(groups), len(aliases))]
    lines += [target for target, _, _ in groups]
    lines += ['%s\t%d' % row for row in aliases]
    return ('\n'.join(lines) + '\n').encode('ascii')


def read_alias_table(raw):
    """{alias name (case-folded): stored name}: the host reference of what the engine reads (same checks)."""
    lines = raw.decode('ascii').split('\n')
    head = lines[0].split(' ')
    if len(head) != 3 or head[0] != ALIAS_MAGIC or lines[-1] != '':
        raise ValueError('Invalid alias table')
    count, aliases = int(head[1]), int(head[2])
    if len(lines) != 2 + count + aliases:
        raise ValueError('Alias table length differs from its header')
    stored = lines[1:1 + count]
    out, previous = {}, None
    for line in lines[1 + count:-1]:
        name, tab, index = line.partition('\t')
        if not tab or not table_name(name) or not index.isdigit() or int(index) >= count:
            raise ValueError('Invalid alias table entry: ' + line)
        if previous is not None and fold_key(previous) >= fold_key(name):
            raise ValueError('Alias table out of order at ' + name)
        out[name.casefold()] = stored[int(index)]
        previous = name
    return out


def apply_aliases(id1, groups, write=True):
    """Remove every alias file of GROUPS and write the table (WRITE=False: count only). Returns the record."""
    id1 = Path(id1)
    table = alias_table(groups) if groups else b''
    removed = sum(len(a) for _, a, _ in groups)
    saved = sum(len(a) * size for _, a, size in groups)
    if write and groups:
        if (id1 / ALIAS_FILE).exists():
            raise ValueError('The payload already has ' + ALIAS_FILE)
        for _, aliases, _ in groups:
            for name in aliases:
                (id1 / name).unlink()
        (id1 / ALIAS_FILE).write_bytes(table)
    memory = len(table) + 8 * removed + 4 * len(groups)   # common.c: the text, 8 B per alias, 4 B per stored name
    return {'groups': len(groups), 'files_removed': removed, 'bytes_saved': saved - len(table),
            'table_bytes': len(table), 'engine_memory_bytes': memory if groups else 0,
            'by_kind': _by_kind(groups)}


def _by_kind(groups):
    out = {}
    for _, aliases, size in groups:
        for name in aliases:
            row = out.setdefault(name.rsplit('/', 1)[0] + '/*' + Path(name).suffix.lower(), {'files': 0, 'bytes': 0})
            row['files'] += 1
            row['bytes'] += size
    return dict(sorted(out.items(), key=lambda kv: -kv[1]['bytes']))


# ---- both, in the image step

def share_payload(id1, *, file_aliases=False, shared_skins=False, jobs=None, write=True, log=print):
    """The image step's last payload pass (finalize_image, after every check that reads the payload by name or
    size): shared skins first (models that then become byte-identical are aliased too), then file aliases.
    Returns the record for build.json; 'bytes_removed' is what DH0 lost (the layout plan allows for it)."""
    record = {'file_aliases': bool(file_aliases), 'shared_skins': bool(shared_skins), 'bytes_removed': 0}
    if shared_skins:
        skins = apply_skins(id1, plan_skins(id1), write)
        record['skins'] = skins
        record['bytes_removed'] += skins['bytes_saved']
        log('Shared skins (--shared-skins on): %d skins stored once for %d models, %d bytes saved'
            % (skins['skins'], skins['models'], skins['bytes_saved']))
    if file_aliases:
        aliases = apply_aliases(id1, plan_aliases(id1, jobs=jobs), write)
        record['aliases'] = aliases
        record['bytes_removed'] += aliases['bytes_saved']
        log('File aliases (--file-aliases on): %d files stored once under %d names more, %d bytes saved, '
            'table %d bytes (game memory about %d bytes)' % (aliases['groups'], aliases['files_removed'],
                                                             aliases['bytes_saved'], aliases['table_bytes'],
                                                             aliases['engine_memory_bytes']))
    return record


def measure(boot, file_aliases, shared_skins, jobs=None):
    """Dry run over a staged payload BOOT (read only): what each method saves on its own and both together.
    Both together are measured on a scratch view: the skin pass's stored forms counted, then aliases over them
    (a model pair that becomes byte-identical only after sharing is counted as the alias pass would see it)."""
    id1 = Path(boot) / 'id1'
    out = {'boot': str(boot)}
    if shared_skins:
        groups = plan_skins(id1)
        out['shared_skins'] = apply_skins(id1, groups, write=False)
    if file_aliases:
        out['file_aliases'] = apply_aliases(id1, plan_aliases(id1, jobs=jobs), write=False)
    if file_aliases and shared_skins:
        out['both'] = _both(id1, jobs)
    return out


def _both(id1, jobs):
    """Aliases over the payload as it would be after the skin pass (in memory: stored forms hashed)."""
    groups = plan_skins(id1)
    stored = {}
    for digest, paths in groups.items():
        for rel in paths:
            stored[rel] = shared_model((id1 / rel).read_bytes(), digest)
    files = [p for p in sorted(id1.rglob('*')) if p.is_file()]
    rows = {}
    plain = [p for p in files if p.relative_to(id1).as_posix() not in stored]
    for path, digest in zip(plain, _hashes(plain, jobs)):
        rows[path.relative_to(id1).as_posix()] = (digest, path.stat().st_size)
    for rel, raw in stored.items():
        rows[rel] = (sha256(raw), len(raw))
    for digest, paths in groups.items():
        raw = (id1 / paths[0]).read_bytes()
        at, pixels = skin_of(raw)
        rows[skin_name(digest)] = (digest, pixels)
    by_hash = {}
    for rel, (digest, size) in rows.items():
        if Path(rel).suffix.lower() in ALIAS_KINDS and size >= ALIAS_MIN_BYTES:
            by_hash.setdefault(digest, []).append((rel, size))
    alias_groups = []
    for members in by_hash.values():
        names = sorted((n for n, _ in members if table_name(n)), key=lambda n: (fold_key(n), n))
        if len(names) > 1:
            alias_groups.append((names[0], names[1:], members[0][1]))
    alias_groups.sort(key=lambda g: fold_key(g[0]))
    table = len(alias_table(alias_groups)) if alias_groups else 0
    alias_saved = sum(len(a) * size for _, a, size in alias_groups)
    before = sum(p.stat().st_size for p in files)
    after = sum(size for _, size in rows.values()) - alias_saved + table
    return {'payload_before': before, 'payload_after': after, 'bytes_saved': before - after,
            'alias_files': sum(len(a) for _, a, _ in alias_groups), 'alias_table_bytes': table,
            'skins': len(groups), 'skin_files_added': len(groups)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='action', required=True)
    m = sub.add_parser('measure', help='Dry run over a staged payload folder (read only)')
    m.add_argument('boot', type=Path)
    m.add_argument('--file-aliases', action='store_true')
    m.add_argument('--shared-skins', action='store_true')
    m.add_argument('--jobs', type=int, default=None)
    m.add_argument('--json', type=Path)
    args = parser.parse_args(argv)
    if not (args.file_aliases or args.shared_skins):
        args.file_aliases = args.shared_skins = True
    result = measure(args.boot, args.file_aliases, args.shared_skins, args.jobs)
    text = json.dumps(result, indent=1)
    if args.json:
        args.json.write_text(text + '\n', encoding='utf-8', newline='\n')
    print(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
