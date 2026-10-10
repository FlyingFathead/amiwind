#!/usr/bin/env python3
"""Prepare an allowlisted Docker context and validate the Linux builder."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mwad.paths import ensure_external, inside
from release import inspect_source, EXECUTABLES

ROOT = Path(__file__).resolve().parents[1]
BASE_IMAGE = 'ubuntu@sha256:a853f94d226358a79c740cfc7bce0c289748f3fe3488d921d038ccd752c61b60'
IMAGE = 'amiwind-builder:local'
# `check` runs these short test modules in the image (its tools, paths and builder entry points); the full
# suite runs once per revision in the source-and-dry-run CI job, or here with --full-suite.
SMOKE_TESTS = ('test_build_docker', 'test_build_host', 'test_build', 'test_release',
               'test_collision_bsp', 'test_engine_hulls')
DOCKERFILE = f'''FROM {BASE_IMAGE}
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv python3-pip ca-certificates build-essential ffmpeg unzip xz-utils fonts-dejavu-core libgmp10 libmpfr6 libmpc3 && rm -rf /var/lib/apt/lists/*
COPY source/ /opt/amiwind/
WORKDIR /opt/amiwind
RUN chmod +x build.sh && python3 tools/build.py --autoinstall --install-dependencies --yes --tools-dir /opt/amiwind-tools && rm -rf /var/lib/apt/lists/* /root/.cache/pip
ENV PATH="/opt/amiwind-tools/venv/bin:${{PATH}}" PYTHONPATH="/opt/amiwind/src:/opt/amiwind/tools" QCC_PATH="/opt/amiwind-tools/Quake-Tools/qcc-host" AMIWIND_TEST_QBSP="/opt/amiwind-tools/ericw/bin/qbsp"
CMD ["python", "tools/build.py", "--help"]
'''


def prepare_context(destination, root=ROOT):
    destination = ensure_external(destination, 'Docker context')
    root = root.resolve()
    if inside(root, destination):
        raise ValueError('Docker context cannot contain the source checkout')
    if destination.exists():
        raise ValueError('Docker context must be new; existing files are never removed')
    # Complete source validation BEFORE writing any build context. Do not copy
    # the checkout/parent tree: even ignored files might contain private assets.
    content = inspect_source(root)
    destination.mkdir(parents=True)
    manifest = {}
    for name, data in sorted(content.items()):
        target = destination / 'source' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(0o755 if name in EXECUTABLES else 0o644)
        manifest[name] = hashlib.sha256(data).hexdigest()
    (destination / 'Dockerfile').write_text(DOCKERFILE, encoding='utf-8', newline='\n')
    (destination / '.dockerignore').write_text(
        '*\n!Dockerfile\n!source/\n!source/**\n', encoding='utf-8', newline='\n')
    return manifest


def docker_command(args):
    command = [args.docker]
    if args.docker_host:
        command += ['--host', args.docker_host]
    return command


def logged(command, log):
    display = list(command)
    if '--host' in display:
        index = display.index('--host') + 1
        if index < len(display):
            display[index] = '<selected Docker endpoint>'
    print('Command: ' + shlex.join(display), flush=True)
    with log.open('w', encoding='utf-8', newline='\n') as output:
        process = subprocess.Popen(command, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True,
                                   encoding='utf-8', errors='replace')
        try:
            for line in process.stdout:
                output.write(line)
                output.flush()
                print(line, end='', flush=True)
            status = process.wait()
        except BaseException:
            process.terminate()
            process.wait()
            raise
        finally:
            process.stdout.close()
    if status:
        raise RuntimeError(f'Command exited {status}; full output: {log}')


def check_script(run, jobs, full_suite=False):
    """Container script of `check`: source checks, image tools, tests (smoke or full), asset-free build."""
    if full_suite:
        tests = f'python tools/run_tests.py -v --jobs {jobs} --module-timeout 900\n'
    else:
        tests = ''.join(f"python -m unittest discover -s tests -p '{name}.py' -v\n" for name in SMOKE_TESTS)
    return ('set -eu\npython tools/release.py --check\n'
            "python -c 'from prepare_scenery import check_nif_reader; check_nif_reader()'\n"
            + tests +
            'python tools/build.py --dry-run --tools-dir /opt/amiwind-tools '
            f'--workspace /work --name {run} --any-run-name --jobs {jobs}\n')


def main(argv=None):
    # Windows redirected console streams otherwise use the legacy code page.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('context', 'build', 'check'))
    parser.add_argument('--context', type=Path, required=True,
                        help='New external directory for allowlisted context')
    parser.add_argument('--output', type=Path, required=True,
                        help='New external directory for diagnostic logs/receipts')
    parser.add_argument('--image', default=IMAGE)
    parser.add_argument('--volume', default='amiwind-docker-builds')
    parser.add_argument('--jobs', type=int, default=os.cpu_count() or 1)
    parser.add_argument('--docker', default='docker')
    parser.add_argument('--docker-host', help='Optional explicit Docker engine endpoint')
    parser.add_argument('--full-suite', action='store_true',
                        help='check: run the full test suite in the image instead of the smoke modules')
    args = parser.parse_args(argv)
    if args.jobs < 1:
        parser.error('--jobs must be positive')
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]*', args.volume):
        parser.error('Use a simple Docker named-volume identifier')
    output = ensure_external(args.output, 'Docker results')
    context = ensure_external(args.context, 'Docker context')
    if inside(output, context) or inside(context, output):
        parser.error('Keep context and results in separate directories')
    if output.exists():
        parser.error('Results directory must be new; previous evidence is retained')
    output.mkdir(parents=True)
    receipt = {'started_at': datetime.now(timezone.utc).isoformat(),
               'action': args.action, 'status': 'running', 'base': BASE_IMAGE,
               'image': args.image, 'jobs': args.jobs, 'volume': args.volume,
               'tests': 'full' if args.full_suite else 'smoke'}
    status = 0
    try:
        receipt['source_sha256'] = prepare_context(context)
        if args.action != 'context':
            docker = docker_command(args)
            logged(docker + ['build', '--progress=plain', '-t', args.image, str(context)],
                   output / 'image-build.log')
            if args.action == 'check':
                run = 'docker-ci-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
                receipt['run'] = run
                script = check_script(run, args.jobs, args.full_suite)
                logged(docker + ['run', '--rm', '--mount',
                       f'type=volume,source={args.volume},target=/work',
                       args.image, 'bash', '-c', script], output / 'validation.log')
        receipt['status'] = 'passed'
    except (OSError, ValueError, RuntimeError) as exc:
        receipt['status'] = 'failed'
        receipt['error'] = str(exc)
        print(f'Error: {exc}', file=sys.stderr)
        status = 1
    finally:
        receipt['finished_at'] = datetime.now(timezone.utc).isoformat()
        (output / 'docker-result.json').write_text(
            json.dumps(receipt, indent=2) + '\n', encoding='utf-8', newline='\n')
    return status


if __name__ == '__main__':
    raise SystemExit(main())
