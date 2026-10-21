#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The AmiWind icon on the game's boot volume, for someone who opens it from Workbench.

The game is a boot disk: S:startup-sequence runs the checks and the engine with a 300,000-byte stack. Seen from a
running Workbench the boot volume is just another drive, and a double-click on the engine binary would start it
without the boot check, without the CPU selector and with Workbench's default stack. So the binary keeps NO icon
(Workbench shows only files with icons, so it is not offered), and the builder can add one project icon instead
(--workbench-icon, default launch since v0.0.46; off = no icon):

  requester  the icon opens a requester (C:RequestChoice of the user's Workbench 3.1, run by C:IconX) that says
             AmiWind starts by booting from its disk, with an OK button. Nothing else runs.
  launch     the icon runs the boot steps from Workbench: the FPU loader when the build installed it, the CPU
             selector (pair builds) or the boot check, Stack 300000, the engine; paths use the boot volume's name
             instead of SYS:. Limits: Workbench's own SetPatch has already run, and the CPU selector looks for
             SYS:AmiWind060 (Workbench's disk), so a 68060 gets the 68040 engine from Workbench.

The icon's file is named "AmiWind v<VERSION>" so Workbench shows that under the picture; the name (with ".info")
must fit the FFS limit of 30 characters. Picture: resources/workbench/AmiWind-icon.png (normal) and
AmiWind-icon-selected.png, written with tools/amiga_icon.py.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import amiga_icon  # noqa: E402
import fpu_support  # noqa: E402

MODES = ('off', 'requester', 'launch')
BOOT_VOLUME = 'AMIWIND'                # the boot partition's volume name (tools/layout_plan.py, DH0)
DEFAULT = 'launch'                     # on by default since v0.0.46 (FS-UAE evidence: docs/WORKBENCH_ICON.md)
NAME_LIMIT = 30                        # FFS file name, ".info" included
PICTURE = HERE.parent / 'resources/workbench/AmiWind-icon.png'
SELECTED = HERE.parent / 'resources/workbench/AmiWind-icon-selected.png'
ICON_STACK = 8192                      # IconX's own process; the game's stack is set by the script (Stack 300000)
GAME_STACK = 300000
REQUESTER_WINDOW = 'WINDOW=CON:0/12/640/60/AmiWind/AUTO/CLOSE'
LAUNCH_WINDOW = 'WINDOW=CON:0/12/640/200/AmiWind/CLOSE'
VERSION_FORM = re.compile(r'[0-9]+\.[0-9]+\.[0-9]+(-[a-z]+[0-9]*)?')
VOLUME_FORM = re.compile(r'[A-Za-z0-9_]{1,30}')
REQUESTER_LINES = (
    'AmiWind v{version} starts by booting',
    'the computer from this disk.',
    '',
    'Make it the boot drive, or hold both mouse',
    'buttons at power-on and pick {volume}',
    'in the Early Startup menu.',
)
LINE_LIMIT = 255                       # one line of an AmigaDOS script (the classic shell's line buffer)


def label(version):
    """The icon's file name, which Workbench shows under the picture."""
    if not VERSION_FORM.fullmatch(version):
        raise ValueError('version %r is not X.Y.Z[-suffixN]' % version)
    name = 'AmiWind v' + version
    if len(name + '.info') > NAME_LIMIT:
        raise ValueError('icon name %r is %d characters with ".info"; FFS allows %d'
                         % (name, len(name + '.info'), NAME_LIMIT))
    return name


def requester_script(version, volume=BOOT_VOLUME):
    body = '*N'.join(line.format(version=version, volume=volume) for line in REQUESTER_LINES)
    command = 'C:RequestChoice >NIL: "AmiWind v%s" "%s" "OK"' % (version, body)
    if len(command) > LINE_LIMIT:
        raise ValueError('requester line is %d characters (limit %d)' % (len(command), LINE_LIMIT))
    return ('; AmiWind v%s: opened from Workbench. The game starts by booting from this disk;\n'
            '; this only says so (builder option --workbench-icon requester).\n%s\n' % (version, command))


def launch_script(version, volume=BOOT_VOLUME, pair=False, fpu=False):
    """The startup sequence's steps with the boot volume's name instead of SYS: (fpu_support.startup_sequence)."""
    v = volume + ':'
    lines = ['; AmiWind v%s: start the game from Workbench (builder option --workbench-icon launch).' % version,
             '; The same steps as the disk\'s S:startup-sequence, with %s instead of SYS:.' % v,
             'FailAt 10']
    if fpu:
        lines.append(v + fpu_support.LOADER)
    start = fpu_support.engine_start(pair, check=v + 'AmiWindCheck')
    check = start['check'].replace('SYS:', v)
    lines.append(check)
    lines += [line.replace('SYS:', v) for line in start['rest']]
    return '\n'.join(lines) + '\n'


def icon_bytes(mode):
    tool_types = [REQUESTER_WINDOW if mode == 'requester' else LAUNCH_WINDOW]
    return amiga_icon.disk_object('project', amiga_icon.load_png(PICTURE), amiga_icon.load_png(SELECTED),
                                  default_tool='C:IconX', tool_types=tool_types, stack=ICON_STACK)


def install(boot, mode, version, volume=BOOT_VOLUME, pair=False, fpu=False):
    """Write the script and its icon into the boot folder; returns the receipt (None for off)."""
    if mode not in MODES:
        raise ValueError('--workbench-icon must be one of %s' % ', '.join(MODES))
    if mode == 'off':
        return None
    if not VOLUME_FORM.fullmatch(volume):
        raise ValueError('boot volume name %r' % volume)
    boot = Path(boot)
    name = label(version)
    script = requester_script(version, volume) if mode == 'requester' else launch_script(version, volume, pair, fpu)
    (boot / name).write_text(script, encoding='latin-1', newline='\n')
    icon = icon_bytes(mode)
    (boot / (name + '.info')).write_bytes(icon)
    return {'mode': mode, 'name': name, 'volume': volume,
            'script_sha256': hashlib.sha256(script.encode('latin-1')).hexdigest(),
            'icon_sha256': hashlib.sha256(icon).hexdigest(), 'icon_bytes': len(icon)}


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='Write the Workbench icon files into a folder (test use)')
    ap.add_argument('--mode', choices=MODES, required=True)
    ap.add_argument('--version', required=True)
    ap.add_argument('--volume', default=BOOT_VOLUME)
    ap.add_argument('--pair', action='store_true')
    ap.add_argument('--fpu', action='store_true')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    print(json.dumps(install(a.out, a.mode, a.version, a.volume, a.pair, a.fpu), indent=2))
