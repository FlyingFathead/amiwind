"""Shared release identity; VERSION is the only maintained version number."""
import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CREDITS = 'By FlyingFathead'
THANKS = 'Special thanks to: ChaosWhisperer'
PROJECT_URL = 'https://github.com/FlyingFathead/amiwind/'


def read_version(path):
    value = Path(path).read_text().strip()
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:-dev[0-9]+)?', value):
        raise ValueError('VERSION must contain one number such as 0.0.17 or 0.0.17-dev1')
    return value


def public_version(root=ROOT):
    return read_version(Path(root)/'VERSION')


def python_version(root=ROOT):
    return public_version(root).replace('-dev', '.dev')


def generate_native(version_file, out):
    value = read_version(version_file)
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    (out/'amiwind_version.h').write_text('/* Generated from VERSION; do not edit. */\n'
        '#ifndef AMIWIND_VERSION_H\n#define AMIWIND_VERSION_H\n'
        f'#define AMIWIND_VERSION "{value}"\n#endif\n')
    (out/'amiwind_version.i').write_text('; Generated from VERSION; do not edit.\n'
        f'banner: dc.b "----------------------------------------------",10\n'
        f'        dc.b "AmiWind v{value} hardware preflight",10\n'
        f'        dc.b "----------------------------------------------",10,0\n'
        f'passed: dc.b "AmiWind v{value} preflight OK.",10,0\n'
        f'stopped: dc.b "AmiWind v{value} was not loaded. Change settings and reboot.",10,0\n'
        f'version_tag: dc.b "$VER: AmiWindCheck {value}",0\n')
    return value


def check_native_versions(root=ROOT):
    root = Path(root)
    expected = public_version(root)
    for name in ('src/aw_hud.c', 'src/aw_scene.c', 'src/sys_amiga.c'):
        path = root/'engine/aga'/name
        text = path.read_text()
        if '#include "amiwind_version.h"' not in text or 'AMIWIND_VERSION' not in text or re.search(r'AmiWind v?[0-9]+\.[0-9]+\.[0-9]+', text, re.I):
            raise ValueError(f'Native version must come from the generated header: {path}')
    if 'include "amiwind_version.i"' not in (root/'engine/aga/boot/bootcheck.asm').read_text():
        raise ValueError('Boot version must come from the generated VERSION include')
    return expected


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version-file', type=Path, default=ROOT/'VERSION')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    generate_native(args.version_file, args.out)
else:
    VERSION = public_version()
