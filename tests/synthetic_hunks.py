"""Synthetic Amiga hunk files for tests: tiny fake libraries with a RomTag.

Built here byte by byte, like tests/fpu_test_library.asm builds a real one;
no vendor file is used or needed. The layout follows the AmigaDOS load file
format and exec/resident.h:

  hunk 0 (CODE)  moveq #-1,d0; rts | Resident | init table | InitStruct data
                 table | strings (unless strings_in_data)
  hunk 1 (DATA)  strings, when strings_in_data
"""
import struct

HUNK_HEADER, HUNK_CODE, HUNK_DATA, HUNK_RELOC32, HUNK_END = 0x3F3, 0x3E9, 0x3EA, 0x3EC, 0x3F2
HUNK_RELOC32SHORT, HUNK_SYMBOL, HUNK_DEBUG = 0x3FC, 0x3F0, 0x3F1


def _pad4(data):
    return data + bytes(-len(data) % 4)


def fake_library(name=b'68040.library', version=40, revision=2, id_string=None, ver_string=None,
                 data_table_revision=None, autoinit=True, node_type=9, short_relocs=False,
                 strings_in_data=False, self_pointer=True, extras=b''):
    """Bytes of a hunk executable holding one resident library.

    revision appears only where the caller puts it: in the id string (default
    '<name> <version>.<revision> (1.1.99)'), in ver_string ('$VER: ...') or in
    the RTF_AUTOINIT data table (data_table_revision, an exec INITWORD)."""
    if id_string is None:
        id_string = name + b' %d.%d (1.1.99)' % (version, revision)
    code = bytearray(b'\x70\xff\x4e\x75')            # moveq #-1,d0 ; rts
    tag = len(code)                                   # 4
    code += bytes(26)
    init = len(code)                                  # 30
    code += bytes(16)
    table = len(code)                                 # 46
    if data_table_revision is not None:
        code += bytes([0x90, 22]) + struct.pack('>H', data_table_revision)  # INITWORD LIB_REVISION
    code += b'\x00\x00'
    code += extras
    strings = bytearray()
    names = {}
    for key, text in (('name', name), ('id', id_string), ('ver', b'$VER: ' + ver_string if ver_string else None)):
        if text is None:
            continue
        names[key] = len(strings)
        strings += text + b'\0'
    string_hunk = 1 if strings_in_data else 0
    base = 0 if strings_in_data else len(code)
    if not strings_in_data:
        code += strings
    code = bytearray(_pad4(bytes(code)))
    relocs = {0: [], 1: []}

    def pointer(field, target_hunk, value):
        struct.pack_into('>I', code, field, value)
        relocs[target_hunk].append(field)

    struct.pack_into('>H', code, tag, 0x4AFC)
    if self_pointer:
        pointer(tag + 2, 0, tag)
    pointer(tag + 6, 0, init)
    struct.pack_into('>BBBb', code, tag + 10, 0x80 if autoinit else 0, version, node_type, 0)
    pointer(tag + 14, string_hunk, base + names['name'])
    pointer(tag + 18, string_hunk, base + names['id'])
    pointer(tag + 22, 0, init)
    struct.pack_into('>I', code, init, 34 + 4)
    pointer(init + 8, 0, table)
    hunks = [(HUNK_CODE, bytes(code))]
    if strings_in_data:
        hunks.append((HUNK_DATA, _pad4(bytes(strings))))
    out = bytearray(struct.pack('>IIIII', HUNK_HEADER, 0, len(hunks), 0, len(hunks) - 1))
    for _, body in hunks:
        out += struct.pack('>I', len(body) // 4)
    for number, (kind, body) in enumerate(hunks):
        out += struct.pack('>II', kind, len(body) // 4) + body
        if number == 0:
            groups = [(target, sorted(offsets)) for target, offsets in relocs.items() if offsets]
            if short_relocs:
                words = []
                for target, offsets in groups:
                    words += [len(offsets), target, *offsets]
                words.append(0)
                if len(words) % 2:
                    words.append(0)
                out += struct.pack('>I', HUNK_RELOC32SHORT) + struct.pack('>%dH' % len(words), *words)
            else:
                out += struct.pack('>I', HUNK_RELOC32)
                for target, offsets in groups:
                    out += struct.pack('>II', len(offsets), target) + b''.join(struct.pack('>I', o) for o in offsets)
                out += struct.pack('>I', 0)
            out += struct.pack('>IIII', HUNK_SYMBOL, 1, 0x41424344, 0) + struct.pack('>I', 0)  # one symbol, then end
            out += struct.pack('>II', HUNK_DEBUG, 1) + b'dbg!'
        out += struct.pack('>I', HUNK_END)
    return bytes(out)


def tes3_master(version=1.3, author=b'Synthetic Author', description=b'Synthetic test master', records=0,
                masters=()):
    """A TES3 file: header record only (HEDR, MAST/DATA pairs)."""
    hedr = struct.pack('<fI', version, 1) + author.ljust(32, b'\0') + description.ljust(256, b'\0') + \
        struct.pack('<I', records)
    body = b'HEDR' + struct.pack('<I', 300) + hedr
    for master in masters:
        name = master + b'\0'
        body += b'MAST' + struct.pack('<I', len(name)) + name + b'DATA' + struct.pack('<I', 8) + bytes(8)
    return b'TES3' + struct.pack('<III', len(body), 0, 0) + body


def tes3_archive(files=0):
    """A BSA with an empty directory of FILES entries."""
    directory = bytes(12 * files)
    return struct.pack('<III', 0x100, len(directory), files) + directory + bytes(8 * files)


def kickstart(version=40, revision=68, size=524288):
    """A Kickstart-shaped image: $1114 start word, version.revision at offset 12."""
    head = b'\x11\x14\x4e\xf9\x00\xf8\x00\xd2\x00\x00\xff\xff' + struct.pack('>HH', version, revision)
    return head + bytes(size - len(head))
