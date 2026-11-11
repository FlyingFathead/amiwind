#!/usr/bin/env python3
"""Build the clean, ready-to-write Raspberry Pi 4B drive image of an AmiWind build (offline, no root tricks).

    python3 tools/pi_image/build_clean_image.py build --downloads DIR --hdf AmiWind.hdf --version V --out DIR
        [--work DIR] [--cache DIR] [--jobs 8] [--extra-words FILE]
    python3 tools/pi_image/build_clean_image.py inputs --downloads DIR      (rewrites tools/pi_image/inputs.json)

It runs in a Linux container with no network and needs only Python, xz and e2fsprogs (resize2fs, debugfs). No arm64
program runs here: the root file system is edited with debugfs on a file, the boot drive with a small FAT editor, and
Amiberry with its libraries is installed on the Pi itself at the first start, from packages saved inside the image
(tools/pi_image/clean/amiwind-firstboot). Every input is checked against tools/pi_image/inputs.json by SHA-256.

The image: Raspberry Pi OS Lite (64-bit) as published, its root file system grown for the libraries, plus a FAT32
drive labelled AMIWIND with the AmiWind image and README-FIRST.txt. No Kickstart, no keys, no password, no SSH, no
wifi, no user account until the first start makes `amiwind` (locked, no sudo). The finished image is checked by
tools/pi_image/scrub_check.py before it is zipped; a failed check leaves no ZIP.

The system half (boot drive + root file system) is cached under --cache by the SHA-256 of inputs.json and of this
folder's files, so a new AmiWind build only writes the AMIWIND drive and the ZIP.
"""
import argparse
import concurrent.futures
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fatfs  # noqa: E402
import scrub_check  # noqa: E402

SECTOR = 512
MIB = 1 << 20
ROOT_GROW_MIB = 1536          # room for the saved packages and their installed files
DATA_SLACK_MIB = 512          # room on AMIWIND for kick.rom and a second image copy step
IDE_CYLINDER = 516096
CMDLINE_ADD = ['quiet', 'loglevel=3', 'logo.nologo', 'vt.global_cursor_default=0', 'video=HDMI-A-1:720x576@50']
CONFIG_ADD = '\n[all]\n# AmiWind clean image: no splash, the hardware watchdog on (stock clock; README-FIRST.txt)\ndisable_splash=1\ndtparam=watchdog=on\n'
INSTALL = [  # (file in clean/, path in the image, mode)
    ('amiwind-firstboot', '/usr/local/sbin/amiwind-firstboot', 0o100755),
    ('amiwind-start', '/usr/local/bin/amiwind-start', 0o100755),
    ('amiwind.service', '/etc/systemd/system/amiwind.service', 0o100644),
    ('amiwind-firstboot.service', '/etc/systemd/system/amiwind-firstboot.service', 0o100644),
    ('10-watchdog.conf', '/etc/systemd/system.conf.d/10-watchdog.conf', 0o100644),
    ('autologin.conf', '/etc/systemd/system/getty@tty2.service.d/autologin.conf', 0o100644),
    ('README-FIRST.txt', '/usr/local/share/amiwind/README-FIRST.txt', 0o100644),
    ('../amiwind.uae', '/usr/local/share/amiwind/amiwind.uae', 0o100644),
    ('empty', '/etc/cloud/cloud-init.disabled', 0o100644),
]
DIRS = ['/usr/local/share/amiwind', '/etc/systemd/system.conf.d', '/etc/systemd/system/getty@tty2.service.d',
        '/var/cache/amiwind', '/var/cache/amiwind/debs', '/opt/amiwind', '/opt/amiwind/data', '/var/log/journal']
REMOVE = ['/etc/systemd/system/multi-user.target.wants/userconfig.service', '/etc/ssh/sshd_config.d/rename_user.conf']
LINKS = [('/etc/systemd/system/multi-user.target.wants/amiwind-firstboot.service',
          '/etc/systemd/system/amiwind-firstboot.service')]


def say(msg):
    print(msg, flush=True)


def sha256(path, chunk=8 * MIB):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            b = f.read(chunk)
            if not b:
                return h.hexdigest()
            h.update(b)


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        raise SystemExit('FAILED (%d): %s\n%s' % (r.returncode, ' '.join(map(str, cmd)), (r.stdout + r.stderr)[-2000:]))
    return r.stdout + r.stderr


def mbr_parts(path):
    with open(path, 'rb') as f:
        mbr = f.read(SECTOR)
    if mbr[510:512] != b'\x55\xaa':
        raise SystemExit('no MBR in %s' % path)
    out = []
    for i in range(4):
        e = mbr[446 + 16 * i:462 + 16 * i]
        if e[4]:
            out.append({'n': i + 1, 'type': e[4], 'start': struct.unpack_from('<I', e, 8)[0],
                        'sectors': struct.unpack_from('<I', e, 12)[0]})
    return out


def set_mbr_part(f, n, ptype, start, sectors):
    e = bytes([0, 0xFE, 0xFF, 0xFF, ptype, 0xFE, 0xFF, 0xFF]) + struct.pack('<II', start, sectors)
    f.seek(446 + 16 * (n - 1))
    f.write(e)


def copy_range(src, dst, start, length, progress=None):
    with open(src, 'rb') as s:
        s.seek(start)
        left, done = length, 0
        while left:
            b = s.read(min(left, 64 * MIB))
            if not b:
                raise SystemExit('short read from %s' % src)
            dst.write(b)
            left -= len(b)
            done += len(b)
            if progress:
                progress(done, length)


class Ticker:
    def __init__(self, what):
        self.what, self.t0, self.last = what, time.time(), 0

    def __call__(self, done, total):
        now = time.time()
        if now - self.last >= 5 or done == total:
            self.last = now
            rate = done / max(now - self.t0, 1e-6) / MIB
            say('  %s: %d / %d MiB, %.0f MiB/s' % (self.what, done // MIB, total // MIB, rate))


def load_inputs():
    return json.loads((HERE / 'inputs.json').read_text(encoding='utf-8'))


def check_inputs(downloads, jobs):
    spec = load_inputs()
    files = [spec['os']] + spec['packages']
    with concurrent.futures.ThreadPoolExecutor(jobs) as ex:
        got = list(ex.map(lambda e: (e, sha256(downloads / e['path']) if (downloads / e['path']).is_file() else None), files))
    bad = [(e['path'], g) for e, g in got if g != e['sha256']]
    if bad:
        raise SystemExit('input check FAILED: ' + '; '.join('%s: %s' % (p, g or 'missing') for p, g in bad[:10]))
    return spec


def cache_key():
    h = hashlib.sha256()
    for p in sorted([HERE / 'build_clean_image.py', HERE / 'fatfs.py', HERE / 'inputs.json', HERE / 'amiwind.uae']
                    + list((HERE / 'clean').iterdir())):
        h.update(p.name.encode() + b'\0' + p.read_bytes() + b'\0')
    return h.hexdigest()[:24]


def build_system(downloads, spec, cache_dir, work, jobs):
    """The boot drive and the edited root file system, as one file from sector 0 to the end of partition 2."""
    key = cache_key()
    base = cache_dir / key / 'system.img'
    meta_p = cache_dir / key / 'system.json'
    if base.is_file() and meta_p.is_file():
        meta = json.loads(meta_p.read_text())
        if sha256(base) == meta['sha256']:
            say('=== PHASE 2/5: system half REUSED (key %s, SHA-256 checked)' % key)
            return base, meta
        say('  cached system half %s fails its SHA-256: rebuilding it' % base)
    say('=== PHASE 2/5: system half, key %s' % key)
    work.mkdir(parents=True, exist_ok=True)
    osimg = work / 'os.img'
    with open(osimg, 'wb') as f:
        r = subprocess.run(['xz', '-dc', '-T%d' % jobs, str(downloads / spec['os']['path'])], stdout=f)
    if r.returncode:
        raise SystemExit('xz failed')
    parts = mbr_parts(osimg)
    p1, p2 = parts[0], parts[1]
    if p1['type'] != 0x0C or p2['type'] != 0x83 or len(parts) != 2:
        raise SystemExit('unexpected partition table %s' % parts)
    root = work / 'p2.ext4'
    with open(root, 'wb') as f:
        copy_range(osimg, f, p2['start'] * SECTOR, p2['sectors'] * SECTOR)
    new_sectors = p2['sectors'] + ROOT_GROW_MIB * MIB // SECTOR
    os.truncate(root, new_sectors * SECTOR)
    run(['resize2fs', '-f', str(root)])
    stage = work / 'stage'
    stage.mkdir(exist_ok=True)
    (stage / 'empty').write_bytes(b'')
    cmds = []
    for d in DIRS:
        if 'Inode:' in subprocess.run(['debugfs', '-R', 'stat %s' % d, str(root)], capture_output=True, text=True).stdout:
            continue
        cmds += ['mkdir %s' % d, 'sif %s mode 040755' % d, 'sif %s uid 0' % d, 'sif %s gid 0' % d]
    for p in REMOVE:
        cmds.append('rm %s' % p)
    for src, dst, mode in INSTALL:
        s = (stage / 'empty') if src == 'empty' else (HERE / 'clean' / src).resolve()
        folder, name = dst.rsplit('/', 1)
        cmds += ['cd %s' % folder, 'write %s %s' % (s, name), 'sif %s mode 0%o' % (dst, mode),
                 'sif %s uid 0' % dst, 'sif %s gid 0' % dst]
    cmds.append('cd /var/cache/amiwind/debs')
    for e in spec['packages']:
        name = e['path'].rsplit('/', 1)[1]
        dst = '/var/cache/amiwind/debs/' + name
        cmds += ['write %s %s' % (downloads / e['path'], name), 'sif %s mode 0100644' % dst, 'sif %s uid 0' % dst,
                 'sif %s gid 0' % dst]
    for link, target in LINKS:
        cmds.append('symlink %s %s' % (link, target))
    (work / 'debugfs.cmds').write_text('\n'.join(cmds) + '\n', encoding='utf-8', newline='\n')
    out = run(['debugfs', '-w', '-f', str(work / 'debugfs.cmds'), str(root)])
    errors = [l for l in out.splitlines() if any(k in l for k in ('rror', 'not found', 'File exists', 'Could not', 'No free'))]
    if errors:
        raise SystemExit('debugfs reported problems:\n' + '\n'.join(errors[:20]))
    if shutil.which('e2fsck'):
        r = subprocess.run(['e2fsck', '-fn', str(root)], capture_output=True, text=True)
        if r.returncode not in (0,):
            raise SystemExit('e2fsck -fn after the edit: exit %d\n%s' % (r.returncode, (r.stdout + r.stderr)[-1500:]))
    base.parent.mkdir(parents=True, exist_ok=True)
    tmp = base.with_suffix('.part')
    with open(tmp, 'wb') as f:
        copy_range(osimg, f, 0, p2['start'] * SECTOR)
        copy_range(root, f, 0, new_sectors * SECTOR, Ticker('root file system'))
        set_mbr_part(f, 2, 0x83, p2['start'], new_sectors)
    vol = fatfs.FatVolume(tmp, p1['start'] * SECTOR)
    files = {p.lower(): (c, s) for p, d, s, c in vol.walk() if not d}
    c, s = files['/cmdline.txt']
    toks = vol.read(c, s).decode().split()
    toks = [t for t in toks if 'resize' not in t and not t.startswith('init=') and not t.startswith('systemd.run')]
    toks += [t for t in CMDLINE_ADD if t not in toks]
    vol.rewrite_root_file('cmdline.txt', (' '.join(toks) + '\n').encode())
    c, s = files['/config.txt']
    cfg = vol.read(c, s).decode()
    if 'AmiWind clean image' not in cfg:
        vol.rewrite_root_file('config.txt', (cfg.rstrip('\n') + '\n' + CONFIG_ADD).encode())
    os.replace(tmp, base)
    meta = {'key': key, 'p1': p1, 'p2': dict(p2, sectors=new_sectors), 'sha256': sha256(base),
            'os_sha256': spec['os']['sha256'], 'cmdline': ' '.join(toks)}
    meta_p.write_text(json.dumps(meta, indent=1), encoding='utf-8', newline='\n')
    for p in (osimg, root):
        p.unlink()
    shutil.rmtree(stage)
    say('  system half: %s (%d MiB)' % (base, base.stat().st_size // MIB))
    return base, meta


def build(a):
    t0 = time.time()
    downloads, out = Path(a.downloads), Path(a.out)
    work = Path(a.work or out / 'work')
    cache_dir = Path(a.cache or work / 'cache')
    hdf = Path(a.hdf)
    say('=== PHASE 1/5: checks (inputs by SHA-256, the AmiWind image)')
    if not hdf.is_file() or hdf.stat().st_size % IDE_CYLINDER:
        raise SystemExit('--hdf %s: missing or not whole IDE cylinders (%d bytes)' % (hdf, IDE_CYLINDER))
    for tool in ('xz', 'resize2fs', 'debugfs'):
        if not shutil.which(tool):
            raise SystemExit('missing tool: %s' % tool)
    hdf_sha = sha256(hdf)
    if a.hdf_sha256 and a.hdf_sha256 != hdf_sha:
        raise SystemExit('--hdf SHA-256 %s, expected %s' % (hdf_sha, a.hdf_sha256))
    spec = check_inputs(downloads, a.jobs)
    say('  %d inputs OK; AmiWind image %s SHA-256 %s' % (1 + len(spec['packages']), hdf.name, hdf_sha))
    base, meta = build_system(downloads, spec, cache_dir, work, a.jobs)
    say('=== PHASE 3/5: the AMIWIND drive and the whole image')
    out.mkdir(parents=True, exist_ok=True)
    name = 'AmiWind-v%s-Pi4B.img' % a.version
    img = work / name
    readme = (HERE / 'clean' / 'README-FIRST.txt').read_bytes()
    p2end = meta['p2']['start'] + meta['p2']['sectors']
    p3start = (p2end + 2047) // 2048 * 2048
    p3mib = (hdf.stat().st_size + len(readme)) // MIB + DATA_SLACK_MIB
    p3sectors = p3mib * MIB // SECTOR
    with open(img, 'wb') as f:
        copy_range(base, f, 0, base.stat().st_size, Ticker('system half'))
        f.write(b'\x00' * ((p3start - p2end) * SECTOR))
        info = fatfs.write_fat32(f, p3start * SECTOR, p3sectors, 'AMIWIND',
                                 [('AmiWind-v%s.hdf' % a.version, hdf.stat().st_size, str(hdf)),
                                  ('README-FIRST.txt', len(readme), readme)],
                                 hidden=p3start, progress=Ticker('AMIWIND drive'))
        set_mbr_part(f, 3, 0x0C, p3start, p3sectors)
    say('  image %s: %d MiB (AMIWIND %d MiB, %d clusters)' % (name, img.stat().st_size // MIB, p3mib, info['clusters']))
    say('=== PHASE 4/5: scrub check')
    receipt = scrub_check.check_image(img, base_meta=meta, spec=spec, downloads=downloads, hdf_sha=hdf_sha,
                                      version=a.version, extra_words=a.extra_words, work=work / 'scrub', jobs=a.jobs)
    receipt.update({'version': a.version, 'image': name, 'image_bytes': img.stat().st_size, 'hdf_sha256': hdf_sha,
                    'system_key': meta['key'], 'os_sha256': meta['os_sha256'], 'cmdline': meta['cmdline'],
                    'boot_check': 'pending'})
    rpath = out / 'PI-IMAGE-RECEIPT.json'
    if receipt['result'] != 'PASS':
        rpath.write_text(json.dumps(receipt, indent=1), encoding='utf-8', newline='\n')
        img.unlink()
        raise SystemExit('scrub check FAILED: %s (receipt %s; no ZIP written)' % ('; '.join(receipt['failures'][:10]), rpath))
    say('  scrub PASS: %d changes against the plain OS, all on the allowlist' % len(receipt['changes']))
    say('=== PHASE 5/5: ZIP')
    zpath = out / ('AmiWind-v%s-pi4b-image.zip' % a.version)
    tmpz = zpath.with_suffix('.zip.part')
    receipt['image_sha256'] = sha256(img)
    with zipfile.ZipFile(tmpz, 'w', zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as z:
        z.writestr('README-FIRST.txt', readme)
        z.write(img, name)
    os.replace(tmpz, zpath)
    zsha = sha256(zpath)
    (out / (zpath.name + '.sha256')).write_text('%s  %s\n' % (zsha, zpath.name), encoding='utf-8', newline='\n')
    receipt.update({'zip': zpath.name, 'zip_bytes': zpath.stat().st_size, 'zip_sha256': zsha,
                    'seconds': round(time.time() - t0)})
    rpath.write_text(json.dumps(receipt, indent=1), encoding='utf-8', newline='\n')
    img.unlink()
    say('done: %s (%d MiB), SHA-256 %s, %d s; receipt %s' % (zpath, zpath.stat().st_size // MIB, zsha,
                                                             receipt['seconds'], rpath))


def write_inputs(a):
    d = Path(a.downloads)
    osx = sorted(d.glob('*raspios-trixie-arm64-lite.img.xz'))[-1]
    pk = [d / 'amiberry' / 'amiberry_8.5.0+trixie_arm64.deb'] + sorted((d / 'debs').glob('*.deb')) + sorted((d / 'debs-egl').glob('*.deb'))
    spec = {'note': 'Inputs of the clean Pi image, each checked by SHA-256 (tools/pi_image/build_clean_image.py).',
            'os': {'path': osx.name, 'sha256': sha256(osx), 'source': 'https://downloads.raspberrypi.com/raspios_lite_arm64/images/'},
            'packages': [{'path': str(p.relative_to(d)).replace('\\', '/'), 'sha256': sha256(p)} for p in pk]}
    (HERE / 'inputs.json').write_text(json.dumps(spec, indent=1) + '\n', encoding='utf-8', newline='\n')
    say('inputs.json: OS + %d packages' % len(pk))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = p.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('build')
    b.add_argument('--downloads', required=True)
    b.add_argument('--hdf', required=True)
    b.add_argument('--hdf-sha256')
    b.add_argument('--version', required=True)
    b.add_argument('--out', required=True)
    b.add_argument('--work')
    b.add_argument('--cache')
    b.add_argument('--jobs', type=int, default=8)
    b.add_argument('--extra-words', help='file of private words the image must not contain (one per line)')
    i = sub.add_parser('inputs')
    i.add_argument('--downloads', required=True)
    a = p.parse_args(argv)
    build(a) if a.cmd == 'build' else write_inputs(a)


if __name__ == '__main__':
    main()
