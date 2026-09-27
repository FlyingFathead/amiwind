"""Shared release identity. pyproject.toml is the authoritative version."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CREDITS = 'By FlyingFathead +- ChaosWhisperer'
PROJECT_URL = 'https://github.com/FlyingFathead/amiwind/'


def python_version(root=ROOT):
    matches = re.findall(r'^version = "([0-9]+\.[0-9]+\.[0-9]+(?:\.dev[0-9]+)?)"$',
                         (Path(root) / 'pyproject.toml').read_text(), re.M)
    if len(matches) != 1:
        raise ValueError('Expected one project version in pyproject.toml')
    return matches[0]


def public_version(root=ROOT):
    return python_version(root).replace('.dev', '-dev')


def check_native_versions(root=ROOT):
    root = Path(root)
    expected = public_version(root)
    for name in ('src/aw_hud.c', 'src/aw_scene.c', 'src/sys_amiga.c', 'boot/bootcheck.asm'):
        path = root / 'engine/aga' / name
        found = re.findall(r'AmiWind v([0-9]+\.[0-9]+\.[0-9]+(?:-dev[0-9]+)?)',
                           path.read_text(), re.I)
        if not found or any(v != expected for v in found):
            raise ValueError(f'Native version mismatch in {path}: expected {expected}, found {found}')
    return expected


VERSION = public_version()
