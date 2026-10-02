#!/usr/bin/env python3
"""Run a private full-game conversion with offline, read-only Docker inputs."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from build_docker import IMAGE, docker_command, logged
from mwad.paths import ensure_external, inside, resolve_data_files


def stage_inputs(docker, data, volume, image, log):
    """Stream private data into runtime storage, never into an image layer."""
    existing = subprocess.check_output(docker + ['volume', 'ls', '--format', '{{.Name}}'],
                                       text=True).splitlines()
    if volume in existing:
        raise ValueError('Input staging volume already exists; refusing to overwrite it')
    tar = shutil.which('tar.exe' if os.name == 'nt' else 'tar')
    if not tar:
        raise ValueError('Private staging needs the host tar executable')
    # Runtime volumes are deliberately distinct from docker build contexts.
    subprocess.run(docker + ['volume', 'create', volume], check=True)
    started = time.monotonic()
    with log.open('w', encoding='utf-8', newline='\n') as output:
        producer = subprocess.Popen([tar, '-C', str(data), '-cf', '-', '.'],
                                    stdout=subprocess.PIPE, stderr=output)
        try:
            consumer = subprocess.Popen(docker + [
                'run', '--rm', '-i', '--network', 'none', '--mount',
                f'type=volume,source={volume},target=/data', image,
                'tar', '-xf', '-', '-C', '/data'],
                stdin=producer.stdout, stdout=output, stderr=output)
            producer.stdout.close()
            consumer_status = consumer.wait()
            producer_status = producer.wait()
        except BaseException:
            if "consumer" in locals() and consumer.poll() is None:
                consumer.terminate()
                consumer.wait()
            producer.terminate()
            producer.wait()
            raise
        finally:
            producer.stdout.close()
    if producer_status or consumer_status:
        raise RuntimeError(f'Input copy failed: tar={producer_status}, '
                           f'container={consumer_status}; partial volume retained; see {log}')
    return round(time.monotonic() - started, 3)


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--data-files', type=Path, help='Owned installation root or Data Files')
    source.add_argument('--input-volume', help='Previously staged private input volume')
    parser.add_argument('--stage-inputs', action=argparse.BooleanOptionalAction,
                        default=os.name == 'nt', help='Copy input into Linux runtime storage (Windows default)')
    parser.add_argument('--output', type=Path, required=True, help='New external export/log directory')
    parser.add_argument('--name', default='docker-full-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    parser.add_argument('--volume', default='amiwind-docker-builds', help='Persistent Linux output/cache volume')
    parser.add_argument('--image', default=IMAGE)
    parser.add_argument('--jobs', type=int, default=os.cpu_count() or 1)
    parser.add_argument('--docker', default='docker')
    parser.add_argument('--docker-host')
    args = parser.parse_args(argv)
    for value in (args.name, args.volume, args.input_volume):
        if value and not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]*', value):
            parser.error('Run/volume names need simple letters, digits, dash, dot or underscore')
    if args.jobs < 1:
        parser.error('--jobs must be positive')
    output = ensure_external(args.output, 'private Docker results')
    data = resolve_data_files(args.data_files) if args.data_files else None
    if data and (inside(data, output) or inside(output, data)):
        parser.error('Keep private game input and output directories separate')
    if output.exists():
        parser.error('Results directory must be new; previous evidence is retained')
    output.mkdir(parents=True)
    docker = docker_command(args)
    container = 'amiwind-' + args.name
    receipt = {'status': 'running', 'started_at': datetime.now(timezone.utc).isoformat(),
               'run': args.name, 'container': container, 'jobs': args.jobs,
               'network': 'none', 'output_volume': args.volume}
    status = 0
    created = False
    try:
        receipt['image_inspect'] = json.loads(subprocess.check_output(
            docker + ['image', 'inspect', args.image], text=True))[0]
        input_volume = args.input_volume
        if data and args.stage_inputs:
            input_volume = 'amiwind-input-' + args.name
            receipt['staging_seconds'] = stage_inputs(
                docker, data, input_volume, args.image, output / 'input-staging.log')
        if input_volume:
            existing = subprocess.check_output(docker + ['volume', 'ls', '--format', '{{.Name}}'],
                                               text=True).splitlines()
            if input_volume not in existing:
                raise ValueError('Private input volume does not exist; refusing an empty mount')
            if input_volume == args.volume:
                raise ValueError('Input and writable output volumes must be separate')
            mount = f'type=volume,source={input_volume},target=/input,readonly'
            receipt['input_volume'] = input_volume
        else:
            if ',' in str(data):
                raise ValueError('Docker bind-mount paths cannot contain commas; use --stage-inputs')
            mount = f'type=bind,source={data},target=/input,readonly'
        command = docker + ['create', '--name', container, '--network', 'none',
                   '--mount', mount, '--mount',
                   f'type=volume,source={args.volume},target=/work', args.image,
                   'python', 'tools/build.py', '--data-files', '/input',
                   '--tools-dir', '/opt/amiwind-tools', '--workspace', '/work',
                   '--name', args.name, '--jobs', str(args.jobs)]
        subprocess.run(command, check=True)
        created = True
        logged(docker + ['start', '--attach', container], output / 'full-build.log')
        state = json.loads(subprocess.check_output(docker + ['inspect', container], text=True))[0]['State']
        receipt['container_state'] = state
        if state['ExitCode']:
            raise RuntimeError(f"Full conversion exited {state['ExitCode']}; see full-build.log")
        logged(docker + ['cp', f'{container}:/work/build/{args.name}', str(output)],
               output / 'export.log')
        receipt['status'] = 'passed'
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        receipt['status'] = 'failed'
        receipt['error'] = str(exc)
        print(f'Error: {exc}', file=sys.stderr)
        status = 1
    finally:
        # Retain input/output volumes and failed containers for diagnosis.
        if created and receipt['status'] == 'passed':
            subprocess.run(docker + ['rm', container], check=False)
        receipt['finished_at'] = datetime.now(timezone.utc).isoformat()
        (output / 'full-result.json').write_text(json.dumps(receipt, indent=2) + '\n',
                                                encoding='utf-8', newline='\n')
    return status


if __name__ == '__main__':
    raise SystemExit(main())
