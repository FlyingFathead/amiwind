"""Shared release identity: VERSION (the game) and CHIM_VERSION (the CHIM engine and builder).

CHIM has its own version number, separate from the game's: semver, major = world
format change, minor = features, patch = fixes. Both files sit at the repository
root and are the only places either number is maintained."""
import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CREDITS = 'By FlyingFathead'
THANKS = 'Special thanks to: ChaosWhisperer'
PROJECT_URL = 'https://github.com/FlyingFathead/amiwind/'


def read_version(path):
    value = Path(path).read_text().strip()
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:-(?:dev|rc)[0-9]+)?', value):
        raise ValueError('VERSION must contain one number such as 0.0.17 or 0.0.17-dev1')
    return value


def read_chim_version(path):
    value = Path(path).read_text().strip()
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', value):
        raise ValueError('CHIM_VERSION must contain one version such as 0.1.0')
    return value


def chim_version(version_file):
    """The CHIM version from the CHIM_VERSION file beside VERSION (the repository root or the
    staged engine tree); None when there is none."""
    path = Path(version_file).parent / 'CHIM_VERSION'
    return read_chim_version(path) if path.is_file() else None


# Every private-test option a refusal check saw in this process, in order: the builder's release readiness
# block (tools/release_readiness.py) lists exactly what a release candidate or final would refuse.
private_test_options = []


def require_private_test_version(version, waivers):
    """Private-test waivers are for -devN builds only; rc and final images pass every gate.

    waivers: names of the waiver options in use (empty when none). VIVEC-ARENA-ACTORS-32.
    Each one is also recorded in private_test_options (release readiness).
    """
    for waiver in waivers or ():
        if waiver not in private_test_options:
            private_test_options.append(waiver)
    if waivers and not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+-dev[0-9]+', version):
        raise ValueError(f'Version {version} is a release candidate or final: private-test waivers '
                         f'({", ".join(waivers)}) are refused; the image must pass every gate')


def public_version(root=ROOT):
    return read_version(Path(root)/'VERSION')


def python_version(root=ROOT):
    return public_version(root).replace('-dev', '.dev').replace('-rc', 'rc')


# Fast RAM the whole game needs (RAM-REQUIREMENT-32MB-48, decided for the project 23 October 2026): the safe
# minimum. With every outdoor NPC and creature placed, 14 CHIM region frames need more model cache than 16 MiB
# gives; 16 MiB still starts (the built heap fits) and evicts and reloads models: slower, not a crash. More RAM
# than this is used automatically (aw_heapsize.c, chim_world.c). The boot check and the engine warn below it.
FAST_RAM_SAFE_MB = 32
FAST_RAM_SINCE = '0.0.48'
# Exec leaves a few bytes of a board out of MEMF_TOTAL; a board counts as its size within this much.
FAST_RAM_SLACK_KIB = 64
# The boot check's wait after the note (maintainer, 23 October 2026: "let it run then even with 16MB but at least
# so that the user/player is warned"): a countdown, ENTER skips, never a block.
FAST_RAM_WAIT_SECONDS = 10
# The trailing space clears the last dot when 10 s becomes 9 s (the row overwrites itself after a carriage return).
FAST_RAM_COUNTDOWN = 'Starting in %ld s... '
STARTUP_SCREEN_COLUMNS = 40  # the startup logo's notice rows (aw_movie.c draw_line: 8-pixel glyphs on 320)


def fast_ram_found_mb(kib):
    """<N> of the warning: the measured Fast RAM in whole MB, rounded down after the Exec slack (a 16 MiB
    board that reports 16320 KiB is 16, not 15). The boot check and the engine compute the same."""
    return (int(kib) + FAST_RAM_SLACK_KIB) // 1024


def fast_ram_short(kib):
    """True when the Fast RAM (MEMF_TOTAL in KiB) is under the safe minimum: the warning is shown."""
    return int(kib) < FAST_RAM_SAFE_MB * 1024 - FAST_RAM_SLACK_KIB


def fast_ram_note(found='%ld', enter=True):
    """The maintainer's warning text (23 October 2026), exactly; found = the measured MB (or the %ld the
    boot check and the engine fill in). The boot check then counts down FAST_RAM_WAIT_SECONDS (ENTER skips,
    never a block); the engine leaves the ENTER sentence out."""
    text = (f'NOTE: AmiWind has grown since v{FAST_RAM_SINCE}: {FAST_RAM_SAFE_MB} MB of Fast RAM is now the '
            f'minimum. Only {found} MB Fast RAM found, hence the game will start but may load more often.')
    return text + (' Press ENTER to continue anyway.' if enter else '')


def fast_ram_note_lines(width, enter=True):
    """The warning wrapped to rows of at most width columns, with %ld for the size counted at its widest
    (six digits); "Press ENTER to continue anyway." starts its own row."""
    import textwrap
    wide = 'x' * 6
    rows = textwrap.wrap(fast_ram_note(wide, enter=False), width, break_long_words=False)
    rows = [row.replace(wide, '%ld') for row in rows]
    if enter:
        rows.append('Press ENTER to continue anyway.')
    return rows


def fast_ram_row(found='%2ld'):
    """The boot checklist's Fast RAM row below the safe minimum (the [!] WARN in the column of the other rows)."""
    # %2ld prints two digits (the sizes under 32 MB), two columns fewer than its own text.
    pad = 49 + (len(found) - 2 if found.startswith('%') else 0)
    return f'Fast RAM:             {found} MB ({FAST_RAM_SAFE_MB} MB needed)'.ljust(pad) + '[!] WARN'


def heap_defaults(source=None):
    """The game heap (Quake's Hunk) in MiB: the engine's default AMIWIND_HEAP_MB and AMIWIND_HEAP_SAFE_MB,
    the largest size tested on the 16 MiB Fast RAM baseline (the least that starts), read from
    sys_amiga.c (the one source: the repository's engine/aga/src or a staged engine tree's src)."""
    if source is None:
        source = next((p for p in (ROOT/'engine/aga/src/sys_amiga.c', ROOT/'src/sys_amiga.c') if p.is_file()), None)
    text = Path(source).read_text(encoding='utf-8') if source else ''
    values = {}
    for name in ('AMIWIND_HEAP_MB', 'AMIWIND_HEAP_SAFE_MB'):
        match = re.search(r'^#define\s+%s\s+(\d+)\s*$' % name, text, re.M)
        if not match:
            raise ValueError(f'Could not find literal {name} in sys_amiga.c')
        values[name] = int(match.group(1))
    return values['AMIWIND_HEAP_MB'], values['AMIWIND_HEAP_SAFE_MB']


def heap_plan(heap_mb=None, source=None):
    """The game heap a build uses: exactly what was asked (--heap-mb N, like --jobs N), else the
    engine's default. Above the measured safe size the plan carries one warning; it is never refused.
    The boot check asks for the heap plus 3 MiB of free Fast RAM (14 MiB for the default 11) and the
    heap plus 16 bytes in one block."""
    default, safe = heap_defaults(source)
    mb = default if heap_mb is None else int(heap_mb)
    if not 1 <= mb <= 2047:
        # Not a size policy: the heap's byte count must fit the engine's signed 32-bit memsize.
        raise ValueError(f'--heap-mb takes a whole number of MiB from 1 to 2047, not {heap_mb}')
    free = mb + 3
    board = 16
    while board < free + 1:
        board *= 2
    warning = None
    if mb > safe:
        warning = (f'Game heap {mb} MiB is above the {safe} MiB tested on the 16 MiB Fast RAM baseline; '
                   f'built as asked (the boot check and the engine say so at start)')
    return {'heap_mb': mb, 'heap_default_mb': default, 'heap_safe_mb': safe, 'fast_free_mb': free,
            'fast_board_mb': board, 'heap_warning': warning}


BOOT_COLUMNS = 63  # the boot console is 64 columns; the last one would wrap (BOOT-CONSOLE-WIDTH-32)


def need_fast_lines(plan):
    """The boot check's two Fast RAM failure lines for the build's heap (the default's text unchanged;
    a shorter second line when a large heap would not fit one console row)."""
    free, mb = plan['fast_free_mb'], plan['heap_mb']
    second = f'      Need {free} MiB free; {mb} MiB + 16 bytes must be contiguous.'
    if len(second) > BOOT_COLUMNS:
        second = f'      Need {free} MiB free; {mb} MiB + 16 bytes in one block.'
    board = plan['fast_board_mb']
    if board < FAST_RAM_SAFE_MB:
        # The least that starts is smaller than the safe minimum: ask for the safe one (RAM-REQUIREMENT-32MB-48).
        return f'FAIL: select {FAST_RAM_SAFE_MB} MB Fast RAM ({board} MB is the least that starts).', second
    return f'FAIL: select {board} MB Fast RAM or more.', second


def heap_note(plan):
    """The boot check's heap line: empty within the measured safe size, else one warning row."""
    if plan['heap_mb'] <= plan['heap_safe_mb']:
        return ''
    return (f'Game heap:            {plan["heap_mb"]} MiB, above {plan["heap_safe_mb"]} MiB tested'.ljust(49)
            + ' [!] WARN')


def _write_if_changed(path, text):
    # Unchanged files keep their time stamps, so make rebuilds only what a new heap size changes.
    path = Path(path)
    data = text.encode('utf-8')
    if not path.is_file() or path.read_bytes() != data:
        path.write_bytes(data)


def generate_heap(out, heap_mb=None, source=None):
    """amiwind_heap.h (the engine's AMIWIND_HEAP_MB) and amiwind_heap.i (the boot check's Fast RAM
    figures and its heap line) for the build's heap size. Returns heap_plan's record."""
    plan = heap_plan(heap_mb, source)
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    mb = plan['heap_mb']
    screen = '\\n'.join(fast_ram_note_lines(STARTUP_SCREEN_COLUMNS, enter=False))
    _write_if_changed(out/'amiwind_heap.h', "/* Generated from the build's heap size (--heap-mb) and the safe Fast RAM\n"
        ' * minimum (tools/project_version.py, RAM-REQUIREMENT-32MB-48); do not edit. */\n'
        '#ifndef AMIWIND_HEAP_H\n#define AMIWIND_HEAP_H\n'
        f'#define AMIWIND_HEAP_MB {mb}\n'
        f'#define AW_FAST_RAM_SAFE_MB {FAST_RAM_SAFE_MB}\n'
        f'#define AW_FAST_RAM_SLACK_KIB {FAST_RAM_SLACK_KIB}\n'
        f'#define AW_FAST_RAM_NOTE "{fast_ram_note(enter=False)}"\n'
        f'#define AW_FAST_RAM_SCREEN "{screen}"\n#endif\n')
    note = heap_note(plan)
    note_rows = fast_ram_note_lines(BOOT_COLUMNS)
    _write_if_changed(out/'amiwind_heap.i', "; Generated from the build's heap size (--heap-mb) and the safe Fast RAM\n"
        '; minimum (tools/project_version.py, RAM-REQUIREMENT-32MB-48); do not edit.\n'
        f'AW_HEAP_BYTES equ {mb}*1048576\n'
        f'AW_FAST_FREE_BYTES equ {plan["fast_free_mb"]}*1048576\n'
        f'AW_FAST_SAFE_KIB equ {FAST_RAM_SAFE_MB * 1024 - FAST_RAM_SLACK_KIB}\n'
        f'AW_FAST_SLACK_KIB equ {FAST_RAM_SLACK_KIB}\n'
        f'AW_FAST_WAIT_SECONDS equ {FAST_RAM_WAIT_SECONDS}\n'
        f'need_fast:      dc.b "{need_fast_lines(plan)[0]}",10\n'
        f'                dc.b "{need_fast_lines(plan)[1]}",10,0\n'
        + (f'heap_note:      dc.b "{note}",10,0\n' if note else 'heap_note:      dc.b 0\n')
        + f'fast_warn_format: dc.b "{fast_ram_row()}",10,0\n'
        + f'fast_countdown_format: dc.b 13,"{FAST_RAM_COUNTDOWN}",0\n'
        + 'fast_note:      ' + '\n                '.join(f'dc.b "{row}",10' for row in note_rows) + ',0\n')
    return plan


def generate_native(version_file, out, heap_mb=None):
    value = read_version(version_file)
    chim = chim_version(version_file)
    # The boot check's short form "AmiWind vX / CHIM vY" (project decision, 2026-10-08).
    title = f'AmiWind v{value} / CHIM v{chim}' if chim else f'AmiWind v{value}'
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    (out/'amiwind_version.h').write_text('/* Generated from VERSION; do not edit. */\n'
        '#ifndef AMIWIND_VERSION_H\n#define AMIWIND_VERSION_H\n'
        f'#define AMIWIND_VERSION "{value}"\n'
        # The console's first version line (maintainer, 11 October 2026): the boot check's title.
        f'#define AMIWIND_TITLE "{title}"\n#endif\n')
    if chim:
        # CHIM's own version for the engine (engine/aga/src/chim/chim.h includes it).
        (out/'chim_version.h').write_text('/* Generated from CHIM_VERSION; do not edit. */\n'
            '#ifndef CHIM_VERSION_H\n#define CHIM_VERSION_H\n'
            f'#define CHIM_VERSION "{chim}"\n#endif\n')
    header = f'{title} hardware preflight'
    rule = '-' * len(header)  # every divider is exactly as long as the header line (generated, never hard-coded)
    (out/'amiwind_version.i').write_text('; Generated from VERSION and CHIM_VERSION; do not edit.\n'
        f'banner: dc.b "{rule}",10\n'
        f'        dc.b "{header}",10\n'
        f'        dc.b "{rule}",10,0\n'
        f'separator:      dc.b "{rule}",10,0\n'
        f'passed: dc.b "AmiWind v{value} preflight OK.",10,0\n'
        f'stopped: dc.b "AmiWind v{value} was not loaded. Change settings and reboot.",10,0\n'
        f'version_tag: dc.b "$VER: AmiWindCheck {value}",0\n')
    generate_heap(out, heap_mb)
    # The boot check's engine profile row: the c profile until tools/build_aga.py engine writes the
    # build's own (engine_profile.write_boot_include; the same text as engine_profile.boot_line).
    _write_if_changed(out/'amiwind_engine.i', DEFAULT_ENGINE_INCLUDE)
    return value


# engine_profile.write_boot_include for the c profile (tests/test_engine_profile.py keeps them equal)
DEFAULT_ENGINE_INCLUDE = ("; Generated from the engine profile (--engine-profile); do not edit.\n"
                          'engine_note:    dc.b "Engine profile:       c: C paths, -O1             [i] INFO",10,0\n')


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
    # CHIM's version comes from CHIM_VERSION through the generated chim_version.h, never a literal.
    for path in sorted((root/'engine/aga/src').rglob('*.[ch]')):
        if re.search(r'^\s*#\s*define\s+CHIM_VERSION\b', path.read_text(errors='replace'), re.M):
            raise ValueError(f'CHIM_VERSION must come from the generated chim_version.h '
                             f'(CHIM_VERSION file): {path}')
    return expected


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version-file', type=Path, default=ROOT/'VERSION')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--heap-mb', type=int, help="Game heap in MiB (default: the engine source's AMIWIND_HEAP_MB)")
    args = parser.parse_args()
    # No warning here: make runs this twice per build; the builder prints it once (build_aga.py engine),
    # and the boot check and the engine say it at start.
    generate_native(args.version_file, args.out, args.heap_mb)
else:
    VERSION = public_version()
