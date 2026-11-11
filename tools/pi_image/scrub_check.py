#!/usr/bin/env python3
"""The scrub check of the clean Pi image: refuses an image that carries anything credential-shaped or private.

    python3 tools/pi_image/scrub_check.py IMAGE.img --downloads DIR --hdf-sha256 SHA [--extra-words FILE]

It reads the image itself (partition table, the boot drive and the AMIWIND drive with tools/pi_image/fatfs.py, the
root file system with `debugfs -R rdump`), compares every file with the plain Raspberry Pi OS image the build started
from (tools/pi_image/inputs.json) and fails on:
- any change that is not on tools/pi_image/expected_changes.json (added, changed or removed, by path pattern);
- key material anywhere: authorized_keys, known_hosts, id_rsa/id_ed25519/..., SSH host keys, private key blocks;
- a password: any /etc/shadow entry that is not locked ('*', '!' or '!...');
- network secrets: wifi passwords, NetworkManager connection files, the boot drive's first-start files (ssh,
  userconf, wpa_supplicant.conf, firstrun.sh) and changed cloud-init seed files;
- token shapes (GitHub, GitLab, Slack, AWS, chat bot tokens, bearer headers) and the private words of --extra-words
  and Windows paths, in every added or changed file;
- SSH switched on, a sudoers entry, a home folder, a Kickstart-sized file or kick.rom, anything else on AMIWIND than
  the AmiWind image (by SHA-256) and README-FIRST.txt.
Files equal to a checked input package (by SHA-256) and the AmiWind image are not scanned again. Exit 0 = PASS.
"""
import argparse
import concurrent.futures
import fnmatch
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fatfs  # noqa: E402

SECTOR = 512
KEY_NAMES = re.compile(r'^(authorized_keys2?|known_hosts(\.old)?|id_(rsa|dsa|ecdsa|ed25519)(_sk)?(\.pub)?|ssh_host_\w+_key(\.pub)?)$')
BOOT_FORBIDDEN = {'ssh', 'ssh.txt', 'userconf', 'userconf.txt', 'wpa_supplicant.conf', 'firstrun.sh', 'custom.toml'}
BOOT_SEEDS = {'user-data', 'network-config', 'meta-data'}
CONTENT = [
    (re.compile(rb'-----BEGIN [A-Z0-9 ]*PRIVATE KEY( BLOCK)?-----'), 'a private key block'),
    (re.compile(rb'\bghp_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{30,}'), 'a GitHub token'),
    (re.compile(rb'\bglpat-[A-Za-z0-9_-]{20,}'), 'a GitLab token'),
    (re.compile(rb'\bxox[abposr]-[A-Za-z0-9-]{10,}'), 'a Slack token'),
    (re.compile(rb'\bAKIA[0-9A-Z]{16}\b'), 'an AWS key'),
    (re.compile(rb'\b\d{8,10}:AA[A-Za-z0-9_-]{33}\b'), 'a chat bot token'),
    (re.compile(rb'(?i)authorization:\s*bearer\s+[A-Za-z0-9._-]{12,}'), 'a bearer header'),
    (re.compile(rb'(?im)^\s*(psk|password|wep_key\d)\s*=\s*\S'), 'a network password'),
]
CONTENT.append((re.compile(rb'(?<![A-Za-z0-9])[A-Za-z]:[\\/][A-Za-z0-9_.-]'), 'a Windows path'))
BUILTIN_WORDS = []   # the build machine's own names come from --extra-words (a private file)
LOCKED = re.compile(r'^(\*|!.*)$')
SCAN_LIMIT = 256 << 20


def sha256(path, chunk=8 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            b = f.read(chunk)
            if not b:
                return h.hexdigest()
            h.update(b)


def parts_of(img):
    with open(img, 'rb') as f:
        mbr = f.read(SECTOR)
    out = []
    for i in range(4):
        e = mbr[446 + 16 * i:462 + 16 * i]
        if e[4]:
            out.append({'type': e[4], 'start': struct.unpack_from('<I', e, 8)[0], 'sectors': struct.unpack_from('<I', e, 12)[0]})
    return out


def tree_manifest(root, jobs):
    """{path: (kind, value, mode, uid)} of a dumped tree; value = SHA-256, link target or ''."""
    items, files = {}, []
    for d, dirs, names in os.walk(root):
        for n in dirs + names:
            p = os.path.join(d, n)
            rel = '/' + os.path.relpath(p, root).replace(os.sep, '/')
            st = os.lstat(p)
            if os.path.islink(p):
                items[rel] = ['link', os.readlink(p), st.st_mode, st.st_uid, 0]
            elif os.path.isdir(p):
                items[rel] = ['dir', '', st.st_mode, st.st_uid, 0]
            else:
                items[rel] = ['file', None, st.st_mode, st.st_uid, st.st_size]
                files.append((rel, p))
    with concurrent.futures.ThreadPoolExecutor(jobs) as ex:
        for rel, h in zip([r for r, _ in files], ex.map(lambda rp: sha256(rp[1]), files)):
            items[rel][1] = h
    return items


def dump_root(img, part, dest, work):
    """rdump the ext4 partition of `img` into dest (the partition is copied out first)."""
    work.mkdir(parents=True, exist_ok=True)
    p = work / 'root.ext4'
    with open(img, 'rb') as s, open(p, 'wb') as o:
        s.seek(part['start'] * SECTOR)
        left = part['sectors'] * SECTOR
        while left:
            b = s.read(min(left, 64 << 20))
            o.write(b)
            left -= len(b)
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    r = subprocess.run(['debugfs', '-R', 'rdump / %s' % dest, str(p)], capture_output=True, text=True)
    p.unlink()
    if r.returncode:
        raise SystemExit('debugfs rdump failed: %s' % r.stderr[-500:])


def fat_manifest(img, part):
    vol = fatfs.FatVolume(img, part['start'] * SECTOR)
    out = {}
    for path, is_dir, size, clus in vol.walk():
        out[path] = {'dir': is_dir, 'size': size, 'clus': clus}
    return vol, out


def base_manifests(osxz, cache, jobs):
    """Manifests of the plain OS image (root and boot), cached by the OS image's SHA-256."""
    key = sha256(osxz)
    cp = cache / ('base-manifest-%s.json' % key[:16])
    if cp.is_file():
        return json.loads(cp.read_text())
    cache.mkdir(parents=True, exist_ok=True)
    img = cache / 'base-os.img'
    with open(img, 'wb') as f:
        if subprocess.run(['xz', '-dc', '-T%d' % jobs, str(osxz)], stdout=f).returncode:
            raise SystemExit('xz failed on %s' % osxz)
    ps = parts_of(img)
    dump_root(img, ps[1], cache / 'base-tree', cache)
    root = tree_manifest(cache / 'base-tree', jobs)
    vol, boot = fat_manifest(img, ps[0])
    bootsha = {p: hashlib.sha256(vol.read(e['clus'], e['size'])).hexdigest() for p, e in boot.items() if not e['dir']}
    img.unlink()
    shutil.rmtree(cache / 'base-tree')
    m = {'root': root, 'boot': bootsha}
    cp.write_text(json.dumps(m), encoding='utf-8', newline='\n')
    return m


def evaluate(base, new, boot_base, boot_new, data_files, read, allow, hdf_sha, input_shas, words, version):
    """The checks themselves, on manifests; `read(part, path)` returns a file's bytes. Returns (failures, changes)."""
    fails, changes = [], []

    def allowed(kind, part, path):
        return any(fnmatch.fnmatchcase(path, pat) for pat in allow.get(part, {}).get(kind, []))

    for path, e in sorted(new.items()):
        b = base.get(path)
        if b is None:
            ch = 'added'
        elif b[0] != e[0] or b[1] != e[1] or (b[2] & 0o7777) != (e[2] & 0o7777) or b[3] != e[3]:
            ch = 'changed' if e[0] != 'dir' else None
        else:
            ch = None
        if ch:
            changes.append({'part': 'root', 'path': path, 'change': ch, 'kind': e[0], 'sha256': e[1] if e[0] == 'file' else e[1]})
            if not allowed(ch, 'root', path):
                fails.append('root: %s not on the allowlist: %s' % (ch, path))
    for path in sorted(set(base) - set(new)):
        changes.append({'part': 'root', 'path': path, 'change': 'removed'})
        if not allowed('removed', 'root', path):
            fails.append('root: removed, not on the allowlist: %s' % path)
    for path, h in sorted(boot_new.items()):
        if boot_base.get(path) != h:
            ch = 'added' if path not in boot_base else 'changed'
            changes.append({'part': 'boot', 'path': path, 'change': ch, 'sha256': h})
            if not allowed(ch, 'boot', path):
                fails.append('boot: %s not on the allowlist: %s' % (ch, path))
            if path.lstrip('/').lower() in BOOT_SEEDS:
                fails.append('boot: first-start seed file changed: %s' % path)
        if path.lstrip('/').lower() in BOOT_FORBIDDEN:
            fails.append('boot: first-start file present: %s' % path)
    for path in sorted(set(boot_base) - set(boot_new)):
        changes.append({'part': 'boot', 'path': path, 'change': 'removed'})
        fails.append('boot: removed: %s' % path)
    # whole-tree checks (the plain OS included)
    for path, e in new.items():
        name = path.rsplit('/', 1)[1]
        if KEY_NAMES.match(name):
            fails.append('key material by name: %s' % path)
        if path.startswith('/etc/NetworkManager/system-connections/') and e[0] != 'dir':
            fails.append('a network connection file: %s' % path)
        if path.startswith('/etc/sudoers.d/') and path not in base:
            fails.append('a sudoers entry: %s' % path)
        if path.startswith('/home/') and path not in base:
            fails.append('a home folder file: %s' % path)
        # only the folders systemd starts units from (deb-systemd-helper-enabled/ is a package record, not a switch)
        if path.startswith(('/etc/systemd/system/', '/usr/lib/systemd/system/', '/lib/systemd/system/')) \
                and '.target.wants/' in path and name in ('ssh.service', 'sshd.service', 'ssh.socket'):
            fails.append('SSH switched on: %s' % path)
        if e[0] == 'file' and path not in base and e[4] in (262144, 524288) or name.lower() in ('kick.rom', 'kick31.rom'):
            fails.append('a Kickstart-sized or Kickstart-named file: %s' % path)
    shadow = read('root', '/etc/shadow').decode('utf-8', 'replace')
    for line in shadow.splitlines():
        f = line.split(':')
        if len(f) > 1 and not LOCKED.match(f[1]):
            fails.append('/etc/shadow: user %s has a usable password' % f[0])
    if not any(l.startswith('root:') and LOCKED.match(l.split(':')[1]) for l in shadow.splitlines()):
        fails.append('/etc/shadow: root is not locked')
    # content scan of every added or changed file
    wl = [w.encode() for w in words if w]
    for c in changes:
        if c['change'] == 'removed' or c.get('kind') in ('dir', 'link'):
            continue
        if c.get('sha256') in input_shas or c.get('sha256') == hdf_sha:
            continue
        data = read(c['part'], c['path'])
        if data is None or len(data) > SCAN_LIMIT:
            fails.append('%s: %s too large to scan, not allowed' % (c['part'], c['path']))
            continue
        for rx, what in CONTENT:
            if rx.search(data):
                fails.append('%s: %s in %s' % (c['part'], what, c['path']))
        low = data.lower()
        for w in wl:
            if w.lower() in low:
                fails.append('%s: a private word in %s' % (c['part'], c['path']))
    # the AMIWIND drive
    for path, (size, sha) in sorted(data_files.items()):
        changes.append({'part': 'data', 'path': path, 'change': 'added', 'sha256': sha})
        if not allowed('files', 'data', path):
            fails.append('data: not allowed on AMIWIND: %s' % path)
        if path.lower().endswith('.hdf') and (sha != hdf_sha or path != '/AmiWind-v%s.hdf' % version):
            fails.append('data: %s is not the AmiWind image of this build' % path)
        if size in (262144, 524288):
            fails.append('data: Kickstart-sized file %s' % path)
    if not any(p.lower().endswith('.hdf') for p in data_files):
        fails.append('data: no AmiWind image on AMIWIND')
    return fails, changes


def check_image(img, base_meta=None, spec=None, downloads=None, hdf_sha='', version='', extra_words=None, work=None,
                jobs=8, cache=None):
    img = Path(img)
    work = Path(work or img.parent / 'scrub')
    spec = spec or json.loads((HERE / 'inputs.json').read_text())
    allow = json.loads((HERE / 'expected_changes.json').read_text())
    words = list(BUILTIN_WORDS)
    if extra_words:
        words += [l.strip() for l in Path(extra_words).read_text(encoding='utf-8').splitlines()
                  if l.strip() and not l.startswith('#')]
    ps = parts_of(img)
    if len(ps) != 3 or [p['type'] for p in ps] != [0x0C, 0x83, 0x0C]:
        return {'result': 'FAIL', 'failures': ['partition table: %s' % ps], 'changes': []}
    base = base_manifests(Path(downloads) / spec['os']['path'], Path(cache or work / 'cache'), jobs)
    tree = work / 'tree'
    dump_root(img, ps[1], tree, work)
    new = tree_manifest(tree, jobs)
    bvol, bmani = fat_manifest(img, ps[0])
    boot_new = {p: hashlib.sha256(bvol.read(e['clus'], e['size'])).hexdigest() for p, e in bmani.items() if not e['dir']}
    dvol, dmani = fat_manifest(img, ps[2])
    data_files = {}
    for p, e in dmani.items():
        if e['dir']:
            data_files[p] = (0, 'dir')
            continue
        h = hashlib.sha256()
        with open(img, 'rb') as f:
            left, chain = e['size'], dvol.chain(e['clus'])
            for c in chain:
                if left <= 0:
                    break
                f.seek(dvol._cpos(c))
                b = f.read(min(dvol.csize, left))
                h.update(b)
                left -= len(b)
        data_files[p] = (e['size'], h.hexdigest())

    def read(part, path):
        if part == 'root':
            p = tree / path.lstrip('/')
            return p.read_bytes() if p.is_file() and not p.is_symlink() else b''
        vol, mani = (bvol, bmani) if part == 'boot' else (dvol, dmani)
        e = mani.get(path)
        return vol.read(e['clus'], e['size']) if e and e['size'] <= SCAN_LIMIT else None

    input_shas = {e['sha256'] for e in spec['packages']}
    fails, changes = evaluate({k: tuple(v) for k, v in base['root'].items()}, {k: tuple(v) for k, v in new.items()},
                              base['boot'], boot_new, data_files, read, allow, hdf_sha, input_shas, words, version)
    if dvol.label() != 'AMIWIND':
        fails.append('data: the drive label is %r, not AMIWIND' % dvol.label())
    shutil.rmtree(tree)
    return {'result': 'FAIL' if fails else 'PASS', 'failures': fails, 'changes': changes,
            'checked_words': len(words), 'root_entries': len(new)}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('image')
    p.add_argument('--downloads', required=True)
    p.add_argument('--hdf-sha256', required=True)
    p.add_argument('--version', required=True)
    p.add_argument('--extra-words')
    p.add_argument('--work')
    p.add_argument('--jobs', type=int, default=8)
    a = p.parse_args(argv)
    r = check_image(a.image, downloads=a.downloads, hdf_sha=a.hdf_sha256, version=a.version, extra_words=a.extra_words,
                    work=a.work, jobs=a.jobs)
    print(json.dumps({k: v for k, v in r.items() if k != 'changes'}, indent=1))
    print('%s: %d changes' % (r['result'], len(r['changes'])))
    return 0 if r['result'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
