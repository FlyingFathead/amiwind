"""Final build timing and output identity, kept outside the source checkout."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
import time

from mwad.progress import Progress, section


def timestamp():
    return datetime.now().astimezone().isoformat(timespec='seconds')


def duration(seconds):
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f'{hours} hrs {minutes:02d} mins {seconds:02d} secs'


def output_identity(path):
    path = Path(path)
    if path.is_dir():
        files = [p for p in path.rglob('*') if p.is_file()]
        return {'path': str(path), 'kind': 'directory', 'files': len(files),
                'bytes': sum(p.stat().st_size for p in files), 'sha256': None}
    digest = hashlib.sha256()
    with path.open('rb') as source:
        before = path.stat()
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
        after = path.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
        raise ValueError('Output changed while calculating SHA-256: ' + str(path))
    return {'path': str(path), 'kind': 'file', 'bytes': after.st_size,
            'sha256': digest.hexdigest()}


def compiler_warnings(run):
    """Count recognized warning lines, not unique defects or all tool warnings."""
    logs = sorted((Path(run) / 'logs').glob('*-engine.log'))
    if not logs:
        return {'count': None, 'logs': []}
    pattern = re.compile(r'\bwarning(?:\s+\d+)?\s*:', re.IGNORECASE)
    count = 0
    for path in logs:
        with path.open(errors='replace') as source:
            count += sum(bool(pattern.search(line)) for line in source)
    return {'count': count, 'logs': [str(p) for p in logs]}


class BuildSummary:
    def __init__(self, run, version, mode):
        self.run = Path(run)
        self.version, self.mode = version, mode
        self.started_at = timestamp()
        self.started = time.monotonic()
        self.finished = False
        self.environment = None
        print('Compilation started: ' + self.started_at, flush=True)

    def record_environment(self, metadata):
        """Reuse pre-build observations; never substitute reference versions.

        Packages describe the interpreter environment. Only tools selected for
        this recipe are included, not every executable the version probe found.
        Selection is not proof of execution (especially on a failed build).
        """
        rows = metadata.get('version_comparison', [])
        by_name = {row['name']: row for row in rows}
        native = []
        for name, path in metadata.get('tools', {}).items():
            if name == 'console-font':
                continue  # An input asset, not an executable.
            row = by_name.get(name, {})
            native.append({'name': name, 'path': str(path),
                           'detected': row.get('detected'),
                           'status': row.get('status', 'not recorded'),
                           'sha256': metadata.get('tool_sha256', {}).get(name) or row.get('sha256')})
        self.environment = {
            'scope': 'pre-build interpreter/packages and selected recipe tools; not an execution trace',
            'python': by_name.get('Python', {}).get('detected') or sys.version.split()[0],
            'python_executable': sys.executable,
            'packages': [{'name': row['name'], 'version': row.get('detected')}
                         for row in rows if row.get('kind') == 'package'],
            'tools': native,
            'worker_budget': metadata.get('compiler_jobs'),
            'stage_scheduling': 'serial' if metadata.get('serial_stages') or metadata.get('compiler_jobs') == 1 else 'dependency-aware',
        }

    def finish(self, status, output=None, actor_acceptance=None):
        if status not in ('passed', 'failed', 'cancelled'):
            raise ValueError('Unknown build status: ' + status)
        # Failed/cancelled runs must never advertise a partial HDF as completed.
        identity = None
        if status == 'passed':
            with Progress('Checking final output size and SHA-256'):
                identity = output_identity(output)
        try:
            warnings = compiler_warnings(self.run)
        except OSError:
            warnings = {'count': None, 'logs': []}
        diagnostic = bool(actor_acceptance and not actor_acceptance['production_gate_passed'])
        elapsed = max(0, time.monotonic() - self.started)
        result = {'schema': 'amiwind-build-summary-v1', 'version': self.version,
                  'mode': self.mode, 'status': status,
                  'started_at': self.started_at, 'finished_at': timestamp(),
                  'elapsed_seconds': round(elapsed, 3), 'elapsed': duration(elapsed),
                  'timing_scope': 'provenance, build stages and final output hashing; excludes prerequisites/setup and emulator launch',
                  'output': identity, 'compiler_warnings': warnings,
                  'build_environment': self.environment,
                  'actor_ground_audit': actor_acceptance,
                  'validation': 'private-test-only' if diagnostic else 'selected-pipeline'}
        saved, save_error = None, None
        if self.run.is_dir():
            saved = self.run / 'build-summary.json'
            temporary = self.run / 'build-summary.tmp'
            try:
                temporary.write_text(json.dumps(result, indent=2) + '\n')
                temporary.replace(saved)
            except OSError as exc:
                saved, save_error = None, str(exc)
        titles = {'passed': 'Compilation finished without errors',
                  'failed': 'Compilation failed', 'cancelled': 'Compilation cancelled'}
        if diagnostic and status == 'passed':
            titles['passed'] = 'Private test image assembled; production actor gate DID NOT PASS'
        lines = [titles[status], f'AmiWind v{self.version} | {self.mode}',
                 'Started: ' + self.started_at, 'Finished: ' + result['finished_at'],
                 'Elapsed: ' + result['elapsed']]
        if self.environment:
            env = self.environment
            lines.append('Python: ' + env['python'])
            if env['packages']:
                lines.append('Python environment packages (not all required by every recipe):')
                lines.extend('  ' + row['name'] + ': ' + (row['version'] or 'not installed')
                             for row in env['packages'])
            if env['tools']:
                lines.append('Selected compiler/toolkit versions and identities (captured before build):')
                for row in env['tools']:
                    detected = row['detected'] or 'version not recorded'
                    if detected.startswith('sha256:'):
                        detected = 'no recorded version; identified by binary SHA-256'
                    lines.append('  ' + row['name'] + ': ' + detected)
                    if row['sha256']:
                        lines.append('    Binary SHA-256: ' + row['sha256'])
            lines.append(f"Worker budget: {env['worker_budget']} | stage scheduling: {env['stage_scheduling']}")
        else:
            lines.append('Compiler/toolkit inventory: not captured')
        if warnings['count'] is not None:
            lines.append(f"Compiler warning lines: {warnings['count']} (engine log)")
            if warnings['count']:
                lines.extend('Warning details: ' + path for path in warnings['logs'])
        elif self.mode == 'terrain conversion':
            lines.append('Compiler warning lines: not applicable (terrain-only build)')
        else:
            lines.append('Compiler warning lines: not counted (no readable engine log)')
        if identity:
            label = 'File' if identity['kind'] == 'file' else 'Directory'
            lines.extend([label + ': ' + Path(identity['path']).name,
                          'Path: ' + identity['path'],
                          f"Size: {identity['bytes'] / (1024 ** 3):.6f} GiB ({identity['bytes']:,} bytes)",
                          'SHA-256: ' + (identity['sha256'] or 'not applicable to a directory')])
        else:
            lines.append('Output: no completed output verified')
        if saved:
            lines.append('Summary: ' + str(saved))
        if save_error:
            lines.append('Summary save warning: ' + save_error)
        section('\n'.join(lines))
        self.finished = True
        return result
