"""Final build timing and output identity, kept outside the source checkout."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
import time

from mwad.progress import Progress, section
import build_profile


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


MEDIA_CATEGORIES = ('videos', 'music', 'voices', 'effects')
MEDIA_COUNT_FIELDS = ('included', 'missing_source', 'missing_output', 'available_sources')


def read_media_coverage(run, status, output_identity, mode):
    """Read the staged media census without implying a completed-image claim.

    Image coverage is written while the payload is staged, before final HDF
    readback. A failed or cancelled run therefore remains payload-only even if
    the image-side report exists.
    """
    run = Path(run)
    image_report = run / 'image' / 'media-coverage.json'
    conversion_report = run / 'media' / 'media-coverage.json'
    if image_report.is_file():
        path = image_report
        image_path = Path(output_identity.get('path', '')) if output_identity else None
        completed_image = (status == 'passed' and output_identity is not None
                           and output_identity.get('kind') == 'file'
                           and image_path.parent.resolve() == (run / 'image').resolve()
                           and image_path.suffix.lower() == '.hdf'
                           and not image_path.name.casefold().endswith(('-dry-run.hdf', '-play.hdf')))
        scope = 'final-staged-image' if completed_image else 'staged-payload-only'
    elif conversion_report.is_file():
        path, scope = conversion_report, 'conversion-only'
    else:
        mode_key = str(mode).casefold().replace('-', ' ')
        return None, ('not-applicable' if 'terrain' in mode_key or 'asset free' in mode_key else 'not-recorded')
    try:
        with path.open(encoding='utf-8') as source:
            report = json.load(source)
        if not isinstance(report, dict):
            raise ValueError('coverage report must be a JSON object')
        categories = report.get('categories')
        if not isinstance(categories, dict):
            raise ValueError('coverage report has no categories object')
        normalized = {}
        for name in MEDIA_CATEGORIES:
            row = categories.get(name)
            if not isinstance(row, dict):
                normalized[name] = None
                continue
            counts = {}
            for field in MEDIA_COUNT_FIELDS:
                value = row.get(field)
                counts[field] = value if type(value) is int and value >= 0 else None
            normalized[name] = counts
        summary = {'path': str(path), 'format': report.get('format'),
                   'status': report.get('status'), 'expected_known_videos': report.get('expected_known_videos'),
                   'categories': normalized}
        return summary, scope
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        return {'path': str(path), 'error': str(error), 'categories': None}, scope


def media_coverage_lines(coverage, scope):
    if coverage is None:
        if scope == 'not-recorded':
            return ['Media coverage not recorded']
        if scope == 'not-applicable':
            return ['Media coverage not applicable']
        return ['Media coverage not recorded']
    lines = ['Media coverage scope: ' + scope]
    if coverage.get('error'):
        lines.append('Media coverage could not be read: ' + coverage['error'])
        return lines
    categories = coverage.get('categories') or {}
    source_gaps, output_gaps = [], []
    source_unknown, output_unknown = False, False
    for name in MEDIA_CATEGORIES:
        row = categories.get(name)
        if row is None:
            lines.append('  ' + name + ': counts not recorded')
            source_unknown = output_unknown = True
            continue
        lines.append('  {name}: included={included} | available_sources={available_sources} | missing_source={missing_source} | missing_output={missing_output}'.format(name=name, **row))
        if row['missing_source']:
            source_gaps.append(name + '=' + str(row['missing_source']))
        elif row['missing_source'] is None:
            source_unknown = True
        if row['missing_output']:
            output_gaps.append(name + '=' + str(row['missing_output']))
        elif row['missing_output'] is None:
            output_unknown = True
    source_status = ', '.join(source_gaps) if source_gaps else ('not determined (incomplete counts)' if source_unknown else 'none recorded')
    output_status = ', '.join(output_gaps) if output_gaps else ('not determined (incomplete counts)' if output_unknown else 'none recorded')
    lines.append('Missing media sources: ' + source_status)
    lines.append('Missing converted/staged media outputs: ' + output_status)
    videos = categories.get('videos')
    if (scope == 'final-staged-image' and coverage.get('expected_known_videos') == 17
            and videos and videos['included'] == 17 and videos['available_sources'] == 17
            and videos['missing_source'] == 0 and videos['missing_output'] == 0):
        lines.append('All 17 Morrowind GOTY videos found and included')
    return lines


def read_fpu_support(run):
    """The image receipt's optional FPU support library (--amiga-libs); None when
    no image receipt exists (terrain builds, failures before the image step)."""
    for name in ('build.json', 'dry-run-build.json'):
        path = Path(run) / 'image' / name
        if path.is_file():
            try:
                record = json.loads(path.read_text(encoding='utf-8'))
            except (OSError, ValueError):
                return None
            return record.get('fpu_support') or {'status': 'not_requested', 'libraries': [], 'companions': []}
    return None


def read_harvest(run):
    """The image receipt's harvest record (BUILD-HARVEST-NOT-BUILT-32); None when
    no image receipt exists."""
    path = Path(run) / 'image' / 'build.json'
    if not path.is_file():
        return None
    try:
        record = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    return record.get('harvest') or {'status': 'not_recorded'}


def harvest_line(record):
    if record.get('status') != 'installed':
        return 'Harvestable mushrooms in the image: ' + record.get('status', 'not recorded')
    return (f"Harvestable mushrooms in the image: {record['admitted']}/{record['candidates']} maps admitted by the "
            f"heap check, {record['plants']} plants, {record['models']} shared models"
            + (f"; not admitted: {', '.join(record['not_admitted'])}" if record.get('not_admitted') else ''))


def read_file_cache(run):
    """{stage: {group: {'hit', 'miss', 'enabled'}}} from the per-file cache reports (profile/file-cache).

    A stage reused from an earlier run converts nothing and writes no report.
    """
    folder = Path(run) / 'profile' / 'file-cache'
    result = {}
    for path in sorted(folder.glob('*.json')) if folder.is_dir() else ():
        try:
            record = json.loads(path.read_text(encoding='utf-8'))
            result[record.get('stage') or path.stem] = record.get('groups') or {}
        except (OSError, ValueError):
            continue
    return result


def file_cache_lines(record):
    lines = []
    for stage, groups in record.items():
        parts = [f"{group} {row.get('hit', 0)} reused, {row.get('miss', 0)} converted"
                 + ('' if row.get('enabled', True) else ' (no cache)') for group, row in groups.items()]
        lines.append(f'Per-file cache ({stage}): ' + '; '.join(parts))
    return lines



def reuse_and_reference(run, version):
    """(record, lines) of the end summary's reuse and reference section (docs/BUILD_CACHE.md): stages reused and
    rebuilt with their causes, time saved, stage output hashes, the payload preflight and the reference check
    against this version's release checksums. Read only; any problem becomes a line, never a failure."""
    record, lines = {}, []
    run = Path(run)
    if not (run / 'build-state.json').is_file():
        return record, lines  # not a builder run (no stages): no section
    try:
        import reuse_report
        audit = reuse_report.report(run)
        if audit is None:
            lines.append('Reuse: none (built without --reuse-from)')
        else:
            causes = ', '.join(f"{row['stage']}: {row['cause']}" for row in audit['rows'])
            lines.append(f"Reuse: {audit['reused']} of {audit['stages']} stages reused, {audit['rebuilt']} rebuilt"
                         + (f' ({causes})' if causes else ''))
            if audit['unexpected']:
                lines.append(f"WARNING: {audit['unexpected']} unexpected rebuild(s): "
                             + ', '.join(row['stage'] for row in audit['rows'] if row['class'] == 'UNEXPECTED')
                             + ' (tools/build.py --reuse-report RUN)')
            old = json.loads((Path(audit['reuse_from']) / 'build-state.json').read_text(encoding='utf-8'))
            elapsed = {step['name']: step.get('elapsed_seconds') or 0 for step in old.get('steps', [])}
            state = json.loads((run / 'build-state.json').read_text(encoding='utf-8'))
            reused = [name for name, row in ((state.get('stage_cache') or {}).get('reused') or {}).items()
                      if not row.get('refused')]
            saved = sum(elapsed.get(name, 0) for name in reused)
            lines.append(f'Time saved by reuse: about {saved / 60:.0f} min (the old run\'s time for the reused stages)')
            record['reuse'] = dict(audit, saved_seconds=round(saved, 1))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        lines.append(f'Reuse: not readable ({exc})')
    try:
        import build_reference
        hashes = build_reference.stage_hashes(run)
        record['stage_hashes'] = hashes
        lines.append(f'Stage hashes: {len(hashes)} recorded')
        check = build_reference.verify(run, version)
        record['reference_check'] = check
        lines.append(build_reference.verify_line(check))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        lines.append(f'Stage hashes: not recorded ({exc})')
    preflight = run / 'image' / 'payload-preflight.json'
    if preflight.is_file():
        try:
            report = json.loads(preflight.read_text(encoding='utf-8'))
            record['payload_preflight'] = report
            lines.append(f"Payload preflight: {'passed' if not report.get('errors') else 'FAILED'} in "
                         f"{report.get('seconds')} s ({report.get('checks')} checks)")
        except (OSError, ValueError) as exc:
            lines.append(f'Payload preflight: not readable ({exc})')
    return record, lines

class BuildSummary:
    def __init__(self, run, version, mode):
        self.run = Path(run)
        self.version, self.mode = version, mode
        self.started_at = timestamp()
        self.started = time.monotonic()
        self.finished = False
        self.environment = None
        self.known_inputs = None  # known-inputs verdicts and hash mode (tools/known_inputs.py)
        self.build_type = None  # a build type other than the normal one (tools/miniwind.py)
        print('Compilation started: ' + self.started_at, flush=True)

    def record_environment(self, metadata):
        """Reuse pre-build observations; never substitute reference versions.

        Packages describe the interpreter environment. Only tools selected for
        this recipe are included, not every executable the version probe found.
        Selection is not proof of execution (especially on a failed build).
        """
        self.build_type = metadata.get('build_type')
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
            'npc_gallery': metadata.get('npc_gallery', 'not recorded'),
            # Quick test builds (--exclude, tools/build_exclusions.py): "quick test build, excluded: ...".
            'excluded_content': (metadata.get('excluded_content') or {}).get('summary', 'not recorded'),
            'world_flora': (metadata.get('world_flora') or {}).get('status', 'not recorded'),
            'harvest': (metadata.get('harvest') or {}).get('status', 'not recorded'),
            'extra_towns': (metadata.get('extra_town_selection') or {}).get('status', 'not recorded'),
            'worker_budget': metadata.get('compiler_jobs'),
            'jobs_warning': metadata.get('jobs_warning'),
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
        media_coverage, coverage_scope = read_media_coverage(self.run, status, identity, self.mode)
        artifacts = None
        if identity and Path(identity['path']).suffix == '.hdf':
            image = Path(identity['path'])
            if (image.parent/'build.json').is_file() or (image.parent/'dry-run-build.json').is_file():
                from emulator_configs import output_paths
                artifacts = output_paths(image)
        try:
            warnings = compiler_warnings(self.run)
        except OSError:
            warnings = {'count': None, 'logs': []}
        diagnostic = bool(actor_acceptance and not actor_acceptance['production_gate_passed'])
        fpu_receipt = read_fpu_support(self.run)
        harvest = read_harvest(self.run)
        file_cache = read_file_cache(self.run)
        elapsed = max(0, time.monotonic() - self.started)
        result = {'schema': 'amiwind-build-summary-v1', 'version': self.version,
                  'mode': self.mode, 'status': status,
                  'started_at': self.started_at, 'finished_at': timestamp(),
                  'elapsed_seconds': round(elapsed, 3), 'elapsed': duration(elapsed),
                  'timing_scope': 'provenance, build stages and final output hashing; excludes prerequisites/setup and emulator launch',
                  'output': identity, 'artifacts': artifacts, 'compiler_warnings': warnings,
                  'media_coverage': media_coverage, 'coverage_scope': coverage_scope,
                  'build_environment': self.environment,
                  'actor_ground_audit': actor_acceptance,
                  'fpu_support': fpu_receipt,
                  'harvest': harvest,
                  'file_cache': file_cache,
                  'known_inputs': self.known_inputs,
                  **({'build_type': self.build_type} if self.build_type else {}),
                  'profile': build_profile.summary_record(self.run),
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
        if self.build_type:
            lines.append('Build type: ' + self.build_type['name'] + ' | ' + self.build_type['partial_area'])
            if self.build_type.get('label'):
                lines.append('MiniWind scope: %s (%s)' % (self.build_type.get('scope'), self.build_type['label']))
            lines.extend(self.build_type['notice'])
            if self.build_type.get('description'):
                lines.append('Scene: ' + self.build_type['description'])
        if self.environment:
            env = self.environment
            lines.append('NPC gallery selection: ' + env.get('npc_gallery', 'not recorded'))
            lines.append('World flora (trees and grass): ' + env.get('world_flora', 'not recorded'))
            lines.append('Harvestable mushrooms: ' + env.get('harvest', 'not recorded'))
            lines.append('Extra towns: ' + env.get('extra_towns', 'not recorded'))
            lines.append('Content: ' + env.get('excluded_content', 'not recorded'))
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
        lines.extend(media_coverage_lines(media_coverage, coverage_scope))
        if self.known_inputs:
            from known_inputs import summary_lines as known_input_lines
            lines.extend(known_input_lines(self.known_inputs))
        if harvest is not None:
            lines.append(harvest_line(harvest))
        lines.extend(file_cache_lines(file_cache))
        if fpu_receipt is not None:
            from fpu_support import summary_lines as fpu_support_lines
            lines.extend(fpu_support_lines(fpu_receipt))
        if result['profile']:
            lines.extend(build_profile.summary_lines(build_profile.load(result['profile']['path'])))
        if saved:
            lines.append('Summary: ' + str(saved))
        if save_error:
            lines.append('Summary save warning: ' + save_error)
        section('\n'.join(lines))
        # Reuse, stage hashes, preflight and the reference check: their own section (docs/BUILD_CACHE.md).
        reuse_record, reuse_lines = reuse_and_reference(self.run, self.version)
        if reuse_lines and self.run.is_dir():
            section('Reuse and reference\n' + '\n'.join(reuse_lines))
            if saved:
                result.update(reuse_record)
                try:
                    temporary.write_text(json.dumps(result, indent=2) + '\n')
                    temporary.replace(saved)
                except OSError:
                    pass
        if artifacts:
            from emulator_configs import print_outputs
            print_outputs(Path(identity['path']))
        self.finished = True
        return result
