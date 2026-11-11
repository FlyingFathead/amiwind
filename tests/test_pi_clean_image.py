"""The clean Raspberry Pi 4B image: the FAT helpers and the scrub check's verdicts (synthetic, seconds)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools' / 'pi_image'))
import fatfs  # noqa: E402
import scrub_check  # noqa: E402

SHA_HDF = 'a' * 64
ALLOW = json.loads((ROOT / 'tools/pi_image/expected_changes.json').read_text())
SHADOW = b'root:*:20732:0:99999:7:::\npi:!:20732:0:99999:7:::\n'


def test_inputs_manifest_complete():
    spec = json.loads((ROOT / 'tools/pi_image/inputs.json').read_text())
    assert len(spec['os']['sha256']) == 64
    names = [p['path'] for p in spec['packages']]
    assert any(n.startswith('amiberry/amiberry_') for n in names)
    for n in ('debs-egl/libegl1_', 'debs-egl/libegl-mesa0_', 'debs-egl/libgles2_'):
        assert any(x.startswith(n) for x in names), n
    assert all(len(p['sha256']) == 64 for p in spec['packages'])


def test_fat32_roundtrip():
    tmp = tempfile.TemporaryDirectory()
    img = Path(tmp.name) / 'd.img'
    with open(img, 'wb') as f:
        info = fatfs.write_fat32(f, 4096, 70000, 'AMIWIND', [('AmiWind-v0.0.1.hdf', 3000, b'x' * 3000),
                                                             ('README-FIRST.txt', 5, b'hello')], cluster_bytes=512)
    assert info['clusters'] >= 65525
    vol = fatfs.FatVolume(img, 4096)
    assert vol.kind == 32 and vol.label() == 'AMIWIND'
    files = {p: (c, s) for p, d, s, c in vol.walk() if not d}
    assert set(files) == {'/AmiWind-v0.0.1.hdf', '/README-FIRST.txt'}
    assert vol.read(*files['/AmiWind-v0.0.1.hdf']) == b'x' * 3000
    vol.rewrite_root_file('README-FIRST.txt', b'hello again')
    vol = fatfs.FatVolume(img, 4096)
    c, _ = files['/README-FIRST.txt']
    assert [vol.read(c, s) for p, d, s, cc in vol.walk() if p == '/README-FIRST.txt'] == [b'hello again']
    tmp.cleanup()


def _run(new_extra=None, boot_new=None, data=None, contents=None, shadow=SHADOW, removed=()):
    base = {'/etc': ('dir', '', 0o40755, 0, 0), '/etc/shadow': ('file', 's0', 0o100640, 0, 10),
            '/etc/ssh/sshd_config.d/rename_user.conf': ('file', 'r', 0o100644, 0, 4)}
    new = {k: v for k, v in base.items() if k not in ('/etc/ssh/sshd_config.d/rename_user.conf',) + tuple(removed)}
    new['/usr/local/sbin/amiwind-firstboot'] = ('file', 'f1', 0o100755, 0, 20)
    new.update(new_extra or {})
    files = dict({'/usr/local/sbin/amiwind-firstboot': b'#!/bin/sh\ndpkg -i\n', '/etc/shadow': shadow}, **(contents or {}))
    boot_base = {'/cmdline.txt': 'c0', '/config.txt': 'k0'}
    data = data if data is not None else {'/AmiWind-v0.0.1.hdf': (3000, SHA_HDF), '/README-FIRST.txt': (5, 'r1')}

    def read(part, path):
        return files.get(path, b'')
    return scrub_check.evaluate(base, new, boot_base, boot_new or {'/cmdline.txt': 'c1', '/config.txt': 'k0'}, data, read,
                                ALLOW, SHA_HDF, set(), scrub_check.BUILTIN_WORDS + ['secretname'], '0.0.1')


def test_clean_passes():
    fails, changes = _run()
    assert fails == [], fails
    assert {c['path'] for c in changes} >= {'/usr/local/sbin/amiwind-firstboot', '/cmdline.txt',
                                             '/etc/ssh/sshd_config.d/rename_user.conf'}


def test_refuses_keys_passwords_tokens_and_strays():
    cases = [
        dict(new_extra={'/home/amiwind/.ssh/authorized_keys': ('file', 'k', 0o100600, 1001, 90)}),
        dict(shadow=SHADOW + b'amiwind:$6$abc$def:20732:0:99999:7:::\n'),
        dict(contents={'/usr/local/sbin/amiwind-firstboot': b'-----BEGIN OPENSSH PRIVATE KEY-----\n'}),
        dict(contents={'/usr/local/sbin/amiwind-firstboot': b'token=ghp_' + b'A' * 36}),
        dict(contents={'/usr/local/sbin/amiwind-firstboot': b'cp D:\\work\\x .'}),
        dict(contents={'/usr/local/sbin/amiwind-firstboot': b'# SecretName'}),
        dict(new_extra={'/etc/systemd/system/multi-user.target.wants/ssh.service': ('link', '/x', 0o120777, 0, 0)}),
        dict(new_extra={'/etc/NetworkManager/system-connections/home.nmconnection': ('file', 'n', 0o100600, 0, 50)}),
        dict(new_extra={'/root/stray.txt': ('file', 's', 0o100644, 0, 5)}),
        dict(boot_new={'/cmdline.txt': 'c0', '/config.txt': 'k0', '/ssh': 'e'}),
        dict(data={'/AmiWind-v0.0.1.hdf': (3000, SHA_HDF), '/kick.rom': (524288, 'k')}),
        dict(data={'/AmiWind-v0.0.1.hdf': (3000, 'b' * 64)}),
        dict(removed=('/etc/shadow',)),
    ]
    for i, kw in enumerate(cases):
        fails, _ = _run(**kw)
        assert fails, 'case %d passed: %s' % (i, kw)


class PiCleanImage(unittest.TestCase):
    def test_inputs(self):
        test_inputs_manifest_complete()

    def test_fat32(self):
        test_fat32_roundtrip()

    def test_clean(self):
        test_clean_passes()

    def test_refusals(self):
        test_refuses_keys_passwords_tokens_and_strays()
