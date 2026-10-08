#!/usr/bin/env python3
"""Create a public, asset-free RDB boot image after a native test compile."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mwad.paths import ensure_external
from build_aga import VERSION
from check_aga_binary import check_binary
from amiga_fs import check_image
from project_version import CREDITS, PROJECT_URL, THANKS
import fpu_support


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def build(args):
    out = ensure_external(args.out, "dry-run output")
    sdk = ensure_external(args.sdk, "Amiga SDK")
    engine = ensure_external(args.engine, "compiled engine")
    check_binary(engine.read_bytes())
    record = json.loads((engine.parents[2] / 'engine-build.json').read_text())
    checker = engine.parent / 'AmiWindCheck'
    if (record.get('version') != VERSION or record.get('binary_sha256') != digest(engine)
            or not checker.is_file() or record.get('bootcheck_sha256') != digest(checker)):
        raise ValueError('Engine/preflight checker does not match the current versioned build receipt')
    from build_host import executable_path
    vasm = executable_path(args.vasm or sdk / "bin/vasmm68k_mot")
    out.mkdir(parents=True, exist_ok=False)
    boot = out / "boot"
    (boot / "C").mkdir(parents=True)
    (boot / "S").mkdir()
    message = (f"AmiWind v{VERSION} - test build\n\n"
               f"{CREDITS}\n{PROJECT_URL}\n{THANKS}\n\n"
               "This is a test compile of AmiWind, built without game files.\n\n"
               "To play, obtain a copy of Morrowind and rebuild AmiWind\n"
               "using your installed game files.\n\n"
               "Engine compilation passed.\n"
               "No game assets or ROMs are included.\n"
               "This screen checks booting only; it is not a playable demo.\n\n"
               "You may now stop the emulator or reset your Amiga.\n")
    # Clear the inherited console, then show original text using the ROM font.
    raw = b'\x1b[0m\x1b[2J\x1b[H' + message.encode('ascii')
    lines = ["message:"] + ["        dc.b " + ','.join(map(str, raw[i:i+24])) for i in range(0, len(raw), 24)]
    lines.append("message_end:")
    (out / "dryrun-message.i").write_text('\n'.join(lines) + '\n', newline='\n')
    notice = boot / "C/AmiWindDryRun"
    subprocess.run([str(vasm), '-m68000', '-Fhunkexe', '-kick1hunks', '-nosym',
                    '-I', str(sdk / 'm68k-amigaos/ndk-include'), '-I', str(out),
                    '-o', str(notice), str(ROOT / 'engine/aga/boot/dryrun.asm')], check=True)
    check_binary(notice.read_bytes())
    shutil.copyfile(checker, boot / "C/AmiWindCheck")
    shutil.copyfile(engine, boot / "C/AmiWind")
    # Optional: the user's own FPU support library (--amiga-libs), as on a game image.
    loader = None
    if getattr(args, 'amiga_libs', None) is not None and fpu_support.find(args.amiga_libs):
        loader = engine.parent / fpu_support.LOADER
        if not loader.is_file() or record.get('fpu_loader_sha256') != digest(loader):
            raise ValueError('AmiWindFPU does not match the engine build receipt; rebuild the engine')
        check_binary(loader.read_bytes())
    fpu_receipt = fpu_support.stage(getattr(args, 'amiga_libs', None), boot, loader,
                                    loader_target='C/' + fpu_support.LOADER,
                                    policy=getattr(args, 'amiga_libs_policy', None) or 'warn')
    for line in fpu_support.summary_lines(fpu_receipt):
        print(line, flush=True)
    if fpu_receipt['status'] == 'installed':
        startup = fpu_support.startup_sequence(fpu_receipt, check='SYS:C/AmiWindCheck',
                                               loader='SYS:C/AmiWindFPU', rest=('SYS:C/AmiWindDryRun',))
    else:
        startup = 'FailAt 10\nSYS:C/AmiWindCheck\nSYS:C/AmiWindDryRun\n'
    (boot / 'S/startup-sequence').write_text(startup, newline='\n')
    (boot / 'README.txt').write_text(message, newline='\n')
    shutil.copyfile(ROOT / 'engine/aga/COPYING', boot / 'COPYING')
    # Use Python module entry points so wrappers cannot select another Python.
    xdf = [sys.executable, '-m', 'amitools.tools.xdftool']
    rdb = [sys.executable, '-m', 'amitools.tools.rdbtool']
    part = out / 'partition.hdf'
    image = out / f'AmiWind-v{VERSION}-dry-run.hdf'
    command = xdf + [str(part), 'create', 'size=8Mi', '+', 'format', 'AMIWINDTEST', 'ffs', '+', 'boot', 'install']
    for name in ('C', 'S', 'LIBS'):
        if (boot / name).is_dir():
            command += ['+', 'makedir', name]
    payload = sorted(p for p in boot.rglob('*') if p.is_file())
    for path in payload:
        command += ['+', 'write', str(path), path.relative_to(boot).as_posix()]
    subprocess.run(command, check=True)
    check_image(part, normalize=True)
    subprocess.run(rdb + [str(image), 'create', 'chs=257,1,64', '+', 'init', '+', 'addimg', str(part), 'name=DH0', 'bootable=1', 'pri=0'], check=True)
    check_image(image, partition='DH0')
    check = out / 'readback.tmp'
    for path in payload:
        subprocess.run(xdf + [str(image), 'open', 'part=DH0', '+', 'read', path.relative_to(boot).as_posix(), str(check)], check=True)
        if digest(check) != digest(path):
            raise ValueError('Dry-run image readback mismatch: ' + str(path))
        check.unlink()
    part.unlink()
    (out / 'dry-run-build.json').write_text(json.dumps({
        'version': VERSION, 'kind': 'asset-free test compile', 'game_assets': False,
        'rom_included': False, 'hdf': image.name, 'hdf_sha256': digest(image),
        'payload': {p.relative_to(boot).as_posix(): digest(p) for p in payload},
        'fpu_support': fpu_receipt,
        'validation': 'Amiga Hunk headers, filesystem metadata and every payload readback; emulator boot is a separate check'
    }, indent=2) + '\n', newline='\n')
    from emulator_configs import write_configs, print_outputs
    configs = write_configs(image, getattr(args, 'kickstart_file', None))
    receipt = out / 'dry-run-build.json'
    record = json.loads(receipt.read_text(encoding='utf-8'))
    record['emulator_configs'] = configs
    receipt.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8',newline='\n')
    print_outputs(image)
    return image


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('sdk', 'engine', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--vasm', type=Path)
    p.add_argument('--kickstart-file', type=Path)
    p.add_argument('--amiga-libs', type=Path,
                   help='Optional folder with your own 68040.library/68060.library (docs/FPU_SUPPORT_LIBRARY.md)')
    p.add_argument('--amiga-libs-policy', choices=('warn', 'fail', 'require-known'), default='warn',
                   help='Known-inputs policy for --amiga-libs (docs/KNOWN_INPUTS.md)')
    try:
        build(p.parse_args())
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        p.exit(1, f'Error: {exc}\n')


if __name__ == '__main__':
    main()
