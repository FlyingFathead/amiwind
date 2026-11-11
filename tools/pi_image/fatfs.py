"""Small FAT16/FAT32 helpers for the clean Pi image (standard library only).

- FatVolume: read a FAT16/FAT32 volume inside an image file (at a byte offset): list every file with its bytes, and
  rewrite an existing root-directory file in place when the new content fits in the clusters it already has.
- write_fat32: write a fresh FAT32 volume (label, files in the root directory, long names) at an offset of an open
  file, with each file in one contiguous run of clusters.
"""
import os
import struct

SECTOR = 512
DOS_TIME = 0                      # 00:00:00
DOS_DATE = ((2026 - 1980) << 9) | (1 << 5) | 1   # 2026-01-01: a fixed stamp, so the volume is reproducible


class FatVolume:
    def __init__(self, path, offset):
        self.path, self.offset = path, offset
        with open(path, 'rb') as f:
            f.seek(offset)
            bs = f.read(SECTOR)
        if bs[510:512] != b'\x55\xaa':
            raise ValueError('no FAT boot sector at offset %d' % offset)
        self.bps, self.spc = struct.unpack_from('<H', bs, 11)[0], bs[13]
        self.rsvd, self.nfats = struct.unpack_from('<H', bs, 14)[0], bs[16]
        self.root_ents = struct.unpack_from('<H', bs, 17)[0]
        tot16, fat16 = struct.unpack_from('<H', bs, 19)[0], struct.unpack_from('<H', bs, 22)[0]
        tot32, fat32 = struct.unpack_from('<I', bs, 32)[0], struct.unpack_from('<I', bs, 36)[0]
        self.total = tot16 or tot32
        self.fatsz = fat16 or fat32
        self.root_secs = (self.root_ents * 32 + self.bps - 1) // self.bps
        self.data_sec = self.rsvd + self.nfats * self.fatsz + self.root_secs
        clusters = (self.total - self.data_sec) // self.spc
        self.kind = 32 if clusters >= 65525 else 16
        if clusters < 4085:
            raise ValueError('FAT12 is not handled')
        self.root_clus = struct.unpack_from('<I', bs, 44)[0] if self.kind == 32 else 0
        self.csize = self.bps * self.spc
        with open(path, 'rb') as f:
            f.seek(offset + self.rsvd * self.bps)
            self.fat = f.read(self.fatsz * self.bps)

    def _next(self, c):
        if self.kind == 32:
            return struct.unpack_from('<I', self.fat, c * 4)[0] & 0x0FFFFFFF
        return struct.unpack_from('<H', self.fat, c * 2)[0]

    def _eoc(self, c):
        return c >= (0x0FFFFFF8 if self.kind == 32 else 0xFFF8) or c < 2

    def chain(self, c):
        out = []
        while not self._eoc(c):
            if c in out or len(out) > 1 << 22:
                raise ValueError('FAT chain loop at cluster %d' % c)
            out.append(c)
            c = self._next(c)
        return out

    def _cpos(self, c):
        return self.offset + (self.data_sec + (c - 2) * self.spc) * self.bps

    def _read_chain(self, f, c, size=None):
        buf = bytearray()
        for cl in self.chain(c):
            f.seek(self._cpos(cl))
            buf += f.read(self.csize)
            if size is not None and len(buf) >= size:
                break
        return bytes(buf if size is None else buf[:size])

    def _dir_raw(self, f, clus):
        if clus == 0:
            f.seek(self.offset + (self.rsvd + self.nfats * self.fatsz) * self.bps)
            return f.read(self.root_secs * self.bps), None
        return self._read_chain(f, clus), clus

    def _entries(self, raw):
        lfn = []
        for i in range(0, len(raw), 32):
            e = raw[i:i + 32]
            if e[0] == 0:
                break
            if e[0] == 0xE5:
                lfn = []
                continue
            if e[11] == 0x0F:
                part = e[1:11] + e[14:26] + e[28:32]
                lfn.insert(0, part.decode('utf-16-le', 'replace').split('\x00')[0].rstrip('￿'))
                continue
            short = e[0:8].decode('latin-1').rstrip() + ('.' + e[8:11].decode('latin-1').rstrip() if e[8:11].strip() else '')
            name = ''.join(lfn) or short
            lfn = []
            attr = e[11]
            clus = (struct.unpack_from('<H', e, 20)[0] << 16) | struct.unpack_from('<H', e, 26)[0]
            size = struct.unpack_from('<I', e, 28)[0]
            yield i, name, attr, clus, size

    def walk(self):
        """Yield (path, is_dir, size, first cluster) for every file and folder, the volume label left out."""
        with open(self.path, 'rb') as f:
            todo = [('', self.root_clus)]
            while todo:
                base, clus = todo.pop()
                raw, _ = self._dir_raw(f, clus)
                for _, name, attr, c, size in self._entries(raw):
                    if attr & 0x08 or name in ('.', '..'):
                        continue
                    p = base + '/' + name
                    if attr & 0x10:
                        yield p, True, 0, c
                        todo.append((p, c))
                    else:
                        yield p, False, size, c

    def read(self, first_cluster, size):
        with open(self.path, 'rb') as f:
            return self._read_chain(f, first_cluster, size) if size else b''

    def label(self):
        with open(self.path, 'rb') as f:
            raw, _ = self._dir_raw(f, self.root_clus)
        for i in range(0, len(raw), 32):
            e = raw[i:i + 32]
            if e[0] == 0:
                break
            if e[0] != 0xE5 and e[11] == 0x08:
                return e[0:11].decode('latin-1').rstrip()
        return ''

    def rewrite_root_file(self, name, data):
        """Replace the bytes of a root-directory file in place; the new content must fit in its clusters."""
        with open(self.path, 'r+b') as f:
            raw, clus = self._dir_raw(f, self.root_clus)
            for i, n, attr, c, size in self._entries(raw):
                if n.lower() != name.lower() or attr & 0x18:
                    continue
                cl = self.chain(c)
                if len(data) > len(cl) * self.csize:
                    raise ValueError('%s: %d bytes do not fit in its %d clusters' % (name, len(data), len(cl)))
                for k, cc in enumerate(cl):
                    f.seek(self._cpos(cc))
                    piece = data[k * self.csize:(k + 1) * self.csize]
                    f.write(piece + b'\x00' * (self.csize - len(piece)))
                if clus is None:
                    pos = self.offset + (self.rsvd + self.nfats * self.fatsz) * self.bps + i
                else:
                    pos = self._cpos(self.chain(clus)[i // self.csize]) + i % self.csize
                f.seek(pos + 28)
                f.write(struct.pack('<I', len(data)))
                return
        raise FileNotFoundError(name)


def _short_name(i, name):
    stem, _, ext = name.rpartition('.')
    stem = ''.join(ch for ch in (stem or name).upper() if ch.isalnum())[:6] or 'FILE'
    ext = ''.join(ch for ch in ext.upper() if ch.isalnum())[:3]
    return ('%s~%d' % (stem, i + 1)).ljust(8)[:8].encode('ascii') + ext.ljust(3).encode('ascii')


def _lfn_entries(name, short):
    csum = 0
    for b in short:
        csum = (((csum & 1) << 7) + (csum >> 1) + b) & 0xFF
    units = name.encode('utf-16-le')
    units = [units[k:k + 2] for k in range(0, len(units), 2)] + [b'\x00\x00']
    while len(units) % 13:
        units.append(b'\xff\xff')
    parts = [units[k:k + 13] for k in range(0, len(units), 13)]
    out = []
    for n, part in enumerate(parts, 1):
        seq = n | (0x40 if n == len(parts) else 0)
        e = bytes([seq]) + b''.join(part[0:5]) + bytes([0x0F, 0, csum]) + b''.join(part[5:11]) + b'\x00\x00' + b''.join(part[11:13])
        out.append(e)
    return list(reversed(out))


def write_fat32(f, offset, sectors, label, files, hidden=0, cluster_bytes=32768, vol_id=0x414D5749, progress=None):
    """Write a FAT32 volume of `sectors` sectors at byte `offset` of the open file `f`.
    files: list of (name, size, source) where source is a path or bytes; all in the root directory."""
    spc = cluster_bytes // SECTOR
    rsvd, nfats = 32, 2
    fatsz = 1
    while True:
        clusters = (sectors - rsvd - nfats * fatsz) // spc
        need = ((clusters + 2) * 4 + SECTOR - 1) // SECTOR
        if need <= fatsz:
            break
        fatsz = need
    if clusters < 65525:
        raise ValueError('volume too small for FAT32 (%d clusters)' % clusters)
    data_sec = rsvd + nfats * fatsz
    fat = bytearray(fatsz * SECTOR)
    struct.pack_into('<III', fat, 0, 0x0FFFFFF8, 0x0FFFFFFF, 0x0FFFFFFF)   # media, end mark, root folder (cluster 2)
    nxt = 3
    root = bytearray(label.upper().ljust(11)[:11].encode('ascii') + bytes([0x08]) + b'\x00' * 20)
    placed = []
    for i, (name, size, src) in enumerate(files):
        n = max(1, (size + cluster_bytes - 1) // cluster_bytes) if size else 0
        first = nxt if n else 0
        for k in range(n):
            struct.pack_into('<I', fat, (nxt + k) * 4, (nxt + k + 1) if k < n - 1 else 0x0FFFFFFF)
        nxt += n
        short = _short_name(i, name)
        for e in _lfn_entries(name, short):
            root += e
        root += short + bytes([0x20, 0, 0]) + struct.pack('<HHHHHHHI', DOS_TIME, DOS_DATE, DOS_DATE, first >> 16,
                                                           DOS_TIME, DOS_DATE, first & 0xFFFF, size)
        placed.append((first, size, src))
    if nxt - 2 > clusters:
        raise ValueError('files need %d clusters, the volume has %d' % (nxt - 2, clusters))
    if len(root) > cluster_bytes:
        raise ValueError('root folder larger than one cluster')
    bs = bytearray(SECTOR)
    bs[0:3] = b'\xeb\x58\x90'
    bs[3:11] = b'AMIWIND '
    struct.pack_into('<HBHBHHBHHHII', bs, 11, SECTOR, spc, rsvd, nfats, 0, 0, 0xF8, 0, 63, 255, hidden, sectors)
    struct.pack_into('<IHHIHH', bs, 36, fatsz, 0, 0, 2, 1, 6)
    bs[64], bs[66] = 0x80, 0x29
    struct.pack_into('<I', bs, 67, vol_id)
    bs[71:82] = label.upper().ljust(11)[:11].encode('ascii')
    bs[82:90] = b'FAT32   '
    bs[510:512] = b'\x55\xaa'
    fsinfo = bytearray(SECTOR)
    struct.pack_into('<I', fsinfo, 0, 0x41615252)
    struct.pack_into('<III', fsinfo, 484, 0x61417272, clusters - (nxt - 2), nxt)
    fsinfo[510:512] = b'\x55\xaa'
    f.seek(offset)
    f.write(b'\x00' * (data_sec * SECTOR + cluster_bytes))   # boot area, FATs and the root folder cleared
    for at in (0, 6):
        f.seek(offset + at * SECTOR)
        f.write(bs)
        f.seek(offset + (at + 1) * SECTOR)
        f.write(fsinfo)
    for k in range(nfats):
        f.seek(offset + (rsvd + k * fatsz) * SECTOR)
        f.write(fat)
    f.seek(offset + data_sec * SECTOR)
    f.write(bytes(root))
    for first, size, src in placed:
        if not size:
            continue
        f.seek(offset + (data_sec + (first - 2) * spc) * SECTOR)
        if isinstance(src, (bytes, bytearray)):
            f.write(src)
        else:
            done = 0
            with open(src, 'rb') as s:
                while True:
                    b = s.read(64 << 20)
                    if not b:
                        break
                    f.write(b)
                    done += len(b)
                    if progress:
                        progress(done, size)
    end = offset + sectors * SECTOR
    f.seek(end - 1)
    f.write(b'\x00')
    return {'clusters': clusters, 'fat_sectors': fatsz, 'used_clusters': nxt - 2}
