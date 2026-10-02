#!/usr/bin/env python3
"""Provision Windows host tools; builds still run through tools/build.py."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile

import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from fetch_native import QCC_COMMIT, QCC_FILES, QCC_URL
from fetch_toolchain import SPEC as LINUX_SDK
from install_dependencies import PYTHON_PACKAGES
from mwad.paths import ensure_external


def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def run(command, **kwargs):
    print('& ' + ' '.join("'" + str(part).replace("'", "''") + "'" for part in command), flush=True)
    return subprocess.run(list(map(str, command)), check=True, **kwargs)


def cached_download(spec, cache, offline=False):
    path = cache / spec['filename']
    if not path.is_file():
        if offline:
            raise ValueError('Offline cache missing: ' + str(path))
        if not spec['url'].startswith('https://') or Path(spec['filename']).name != spec['filename']:
            raise ValueError('Invalid download specification')
        partial = path.with_name(path.name + '.partial')
        command = [str(Path(os.environ['SystemRoot']) / 'System32/curl.exe'), '--fail', '--location',
                   '--proto', '=https', '--proto-redir', '=https', '--connect-timeout', '20', '--max-time', '600',
                   '--max-filesize', str(spec.get('bytes', 4 * 1024 * 1024)), '--output', str(partial), spec['url']]
        run(command)
        verify_download(partial, spec)
        partial.rename(path)
    verify_download(path, spec)
    return path


def verify_download(path, spec):
    size = path.stat().st_size
    if 'bytes' in spec and size != spec['bytes']:
        raise ValueError('Download size mismatch: ' + str(path))
    if size > spec.get('bytes', 4 * 1024 * 1024):
        raise ValueError('Download size limit exceeded')
    if 'sha256' in spec and digest(path) != spec['sha256']:
        raise ValueError('Download SHA-256 mismatch: ' + str(path))


def zip_members(bundle, prefix):
    seen = set()
    for entry in bundle.infolist():
        original = entry.orig_filename
        parts = PurePosixPath(original).parts
        if (not parts or parts[0] != prefix or '..' in parts or '\\' in original or '\0' in original
                or any(':' in p or p.endswith(('.', ' ')) for p in parts)
                or stat.S_ISLNK(entry.external_attr >> 16)):
            raise ValueError('Unsafe ZIP entry: ' + entry.filename)
        relative = Path(*parts[1:])
        key = str(relative).casefold()
        if key in seen:
            raise ValueError('Duplicate ZIP path: ' + entry.filename)
        seen.add(key)
        yield entry, relative


def install_zip(archive, destination, prefix):
    with zipfile.ZipFile(archive) as bundle:
        members = list(zip_members(bundle, prefix))
        if destination.exists():
            # Adopt only an exact existing extraction; never overwrite user edits.
            for entry, relative in members:
                if not entry.is_dir():
                    target = destination / relative
                    if not target.is_file() or hashlib.sha256(bundle.read(entry)).hexdigest() != digest(target):
                        raise ValueError('Existing tool differs from pinned archive: ' + str(target))
            return
        with tempfile.TemporaryDirectory(prefix='amiwind-zip-', dir=destination.parent) as temp:
            staged = Path(temp) / 'ready'
            staged.mkdir()
            for entry, relative in members:
                target = staged / relative
                if entry.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with bundle.open(entry) as source, target.open('xb') as output:
                        shutil.copyfileobj(source, output)
            staged.rename(destination)


def extract_qcc(archive, destination):
    destination.mkdir(parents=True, exist_ok=True)
    seen = set()
    with tarfile.open(archive) as bundle:
        for entry in bundle:
            parts = PurePosixPath(entry.name).parts
            if len(parts) != 3 or parts[1] != 'qcc' or parts[2] not in QCC_FILES:
                continue
            name = parts[2]
            size, expected = QCC_FILES[name]
            if name in seen or not entry.isfile() or entry.size != size:
                raise ValueError('Invalid pinned QCC source entry')
            data = bundle.extractfile(entry).read(size + 1)
            if len(data) != size or hashlib.sha256(data).hexdigest() != expected:
                raise ValueError('Pinned QCC source mismatch: ' + name)
            target = destination / name
            if target.exists() and target.read_bytes() != data:
                raise ValueError('Existing QCC source differs; preserve and inspect: ' + str(target))
            if not target.exists():
                target.write_bytes(data)
            seen.add(name)
    if seen != QCC_FILES.keys():
        raise ValueError('Missing pinned QCC source files')


def provision_python(tools, spec, offline, env):
    venv = tools / 'venv'
    python = venv / 'Scripts/python.exe'
    if venv.exists() and not ((venv / 'pyvenv.cfg').is_file() and python.is_file()):
        raise ValueError('Incomplete Windows venv; inspect before retrying: ' + str(venv))
    if not venv.exists():
        run([sys.executable, '-m', 'venv', venv], env=env)
    cache = tools / 'downloads'
    constraints = cache / 'windows-python-constraints.txt'
    # Keep an existing compatible environment instead of downgrading it to defaults.
    probe = subprocess.run([str(python), '-c',
        'import importlib.metadata as m, json, sys; '
        'from pip._vendor.packaging.requirements import Requirement; '
        'rs=[Requirement(x) for x in sys.argv[1:]]; '
        'vs={r.name:m.version(r.name) for r in rs}; '
        'assert all(r.specifier.contains(vs[r.name]) for r in rs); '
        'print(json.dumps([r.name+"=="+vs[r.name] for r in rs]))', *PYTHON_PACKAGES],
        env=env, capture_output=True, text=True)
    selected = spec['python_constraints']
    if probe.returncode == 0:
        selected = json.loads(probe.stdout)
        print('Reusing Python packages that satisfy the shared requirements; versions are reported below.', flush=True)
    constraints.write_text('\n'.join(selected) + '\n', encoding='utf-8')
    wheels = cache / 'wheels'
    wheels.mkdir(exist_ok=True)
    receipt = cache / 'windows-wheel-cache.json'
    if offline:
        if not receipt.is_file():
            raise ValueError('Offline wheel cache needs an online setup receipt first')
        for name, expected in json.loads(receipt.read_text(encoding='utf-8')).items():
            if Path(name).name != name or not (wheels / name).is_file() or digest(wheels / name) != expected:
                raise ValueError('Offline wheel cache mismatch: ' + name)
    else:
        run([python, '-m', 'pip', 'wheel', '--disable-pip-version-check', '--wheel-dir', wheels,
             '--constraint', constraints, *PYTHON_PACKAGES], env=env)
        receipt.write_text(json.dumps({p.name: digest(p) for p in sorted(wheels.glob('*.whl'))}, indent=2) + '\n', encoding='utf-8')
    run([python, '-m', 'pip', 'install', '--disable-pip-version-check', '--no-index', '--find-links', wheels,
         '--constraint', constraints, *PYTHON_PACKAGES], env=env)
    run([python, '-m', 'pip', 'check'], env=env)
    return python


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tools-dir', type=Path, required=True)
    parser.add_argument('--offline', action='store_true')
    args = parser.parse_args(argv)
    try:
        if sys.platform != 'win32':
            raise ValueError('Windows setup only; Linux keeps its existing setup path')
        spec = json.loads((ROOT / 'config/windows-toolchain.json').read_text(encoding='utf-8'))
        if spec['sdk']['version'] != LINUX_SDK['release']:
            raise ValueError('Windows and Linux SDK pins differ; update and validate them together')
        tools = ensure_external(args.tools_dir, 'Windows tools directory')
        cache = tools / 'downloads'
        cache.mkdir(parents=True, exist_ok=True)
        msys = tools / 'msys64'
        bash = msys / 'usr/bin/bash.exe'
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', PYTHONUNBUFFERED='1')
        env['PATH'] = os.pathsep.join([str(tools / 'venv/Scripts'), str(tools / 'sdk/bin'), str(tools / 'ffmpeg/bin'), str(msys / 'usr/bin'), env.get('PATH', '')])
        env.pop('PYTHONHOME', None)
        env.pop('PYTHONPATH', None)
        for name, key in [('m68k-amigaos-gcc.exe', 'compiler_sha256'), ('vasmm68k_mot.exe', 'assembler_sha256')]:
            if digest(tools / 'sdk/bin' / name) != spec['sdk'][key]:
                print('WARNING: Existing ' + name + ' differs from the Windows reference binary. '
                      'Keeping it; compare its version and validate an actual compile.', flush=True)
        if not (tools / 'sdk/m68k-amigaos/ndk-include/exec/exec_lib.i').is_file():
            raise ValueError('SDK NDK assembly includes are missing')
        font = msys / 'ucrt64/share/fonts/TTF/DejaVuSansMono.ttf'
        missing = [p for p in (msys / 'usr/bin/make.exe', msys / 'usr/bin/gcc.exe', font) if not p.is_file()]
        if missing:
            if args.offline:
                raise ValueError('Offline MSYS2 prerequisites missing: ' + ', '.join(map(str, missing)))
            # A runtime update closes its shell; a fresh invocation completes it.
            run([bash, '-lc', 'pacman -Syu --noconfirm'], env=env)
            run([bash, '-lc', 'pacman -Syu --noconfirm'], env=env)
            packages = spec['msys2_packages']
            if not all(re.fullmatch('[a-z0-9-]+', p) for p in packages):
                raise ValueError('Invalid MSYS2 package name')
            run([bash, '-lc', 'pacman -S --needed --noconfirm ' + ' '.join(packages)], env=env)
        python = provision_python(tools, spec, args.offline, env)
        maps = cached_download(spec['ericw'], cache, args.offline)
        if (tools / 'ericw').exists():
            if not all((tools / 'ericw/bin' / (n + '.exe')).is_file() for n in ('qbsp', 'vis', 'light')):
                raise ValueError('Existing map tools directory is incomplete; inspect before retrying')
            print('Keeping existing map tools; versions are compared with the original reference below.', flush=True)
        else:
            install_zip(maps, tools / 'ericw', spec['ericw']['directory'])
        ffmpeg = tools / 'ffmpeg/bin/ffmpeg.exe'
        # Default is known/pinned. Existing managed FFmpeg may be newer and is recorded.
        if not args.offline or not ffmpeg.is_file():
            archive = cached_download(spec['ffmpeg'], cache, args.offline)
            if not ffmpeg.is_file():
                install_zip(archive, tools / 'ffmpeg', spec['ffmpeg']['directory'])
        ffmpeg_version = subprocess.check_output([str(ffmpeg), '-version'], text=True, env=env).splitlines()[0]
        print('Using ' + ffmpeg_version + '; reference comparison appears in build --versions.', flush=True)
        (tools / 'fonts').mkdir(exist_ok=True)
        shutil.copyfile(font, tools / 'fonts/DejaVuSansMono.ttf')
        shutil.copyfile(msys / 'ucrt64/share/licenses/ttf-dejavu/LICENSE', tools / 'fonts/LICENSE-DejaVu')
        source = cached_download({'filename': 'qcc-source.tar.gz', 'url': QCC_URL}, cache, args.offline)
        qcc = tools / 'Quake-Tools'
        extract_qcc(source, qcc / 'qcc')
        command = [msys / 'usr/bin/gcc.exe', '-std=gnu89', '-include', 'unistd.h', '-O2', '-fcommon',
                   '-o', '../qcc-host.exe', 'qcc.c', 'pr_comp.c', 'pr_lex.c', 'cmdlib.c']
        if not (qcc / 'qcc-host.exe').is_file():
            run(command, cwd=qcc / 'qcc', env=env)
        # Use the installed venv for source-format and bytecode validation.
        validation_env = dict(env, PYTHONPATH=str(ROOT / 'src') + os.pathsep + str(ROOT / 'tools'))
        run([python, '-B', '-c', 'import sys; from build_aga import check_quakec; '
             'from prepare_scenery import check_nif_reader; check_nif_reader(); '
             'check_quakec(sys.argv[1], "3d"); check_quakec(sys.argv[1], "sprites")', qcc / 'qcc-host.exe'], env=validation_env)
        packages = subprocess.check_output([str(msys / 'usr/bin/pacman.exe'), '-Q'], text=True, env=env)
        binaries = [tools / 'sdk/bin/m68k-amigaos-gcc.exe', tools / 'sdk/bin/vasmm68k_mot.exe',
                    msys / 'usr/bin/make.exe', msys / 'usr/bin/gcc.exe', qcc / 'qcc-host.exe', ffmpeg,
                    *[tools / 'ericw/bin' / (n + '.exe') for n in ('qbsp', 'vis', 'light')]]
        receipt = {'schema': 'amiwind-windows-setup-v1', 'manifest_sha256': digest(ROOT / 'config/windows-toolchain.json'),
                   'offline': args.offline, 'qcc_commit': QCC_COMMIT, 'ffmpeg': ffmpeg_version,
                   'msys2_packages': packages.splitlines(), 'python_default_constraints': spec['python_constraints'],
                   'python_constraints': (cache / 'windows-python-constraints.txt').read_text(encoding='utf-8').splitlines(),
                   'binaries': {str(p.relative_to(tools)): digest(p) for p in binaries}}
        (tools / 'windows-setup.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
        run([python, '-B', ROOT / 'tools/build.py', '--versions', '--tools-dir', tools,
             '--sdk', tools / 'sdk', '--ffmpeg', ffmpeg], env=env)
        print('Setup ready. No game data or ROMs used. Receipt: ' + str(tools / 'windows-setup.json'), flush=True)
        print('Next: build.cmd --dry-run --jobs 4', flush=True)
        return 0
    except (OSError, ValueError, subprocess.SubprocessError, zipfile.BadZipFile, tarfile.TarError) as exc:
        print('Windows setup: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
