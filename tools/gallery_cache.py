# SPDX-License-Identifier: GPL-3.0-only
"""Verified host-only appearance reuse; never omit catalogue entries or quality.

Cache hits produce the same complete MDL representation as ordinary conversion.
No additional assembly, lookup or drawing work is moved onto the Amiga. Missing,
corrupt or incompatible entries are rebuilt; failures remain build failures.
"""
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import struct
import sys
import tempfile
import time

from mwad.audit import BSA, normpath
from mwad.paths import child_ci, ensure_external, is_game_input, inside
from npc_geometry import Assets
from prepare_scenery import nif_reader

ROOT = Path(__file__).resolve().parents[1]
FORMAT = 'AmiWind gallery cache 1'
PACKAGES = ('numpy', 'scipy', 'Pillow', 'PyFFI', 'fast-simplification')
# These files implement model extraction, assembly, simplification and encoding.
# Engine, HUD, torch and release-version edits do not invalidate character models.
CONVERTER_FILES = (
    'tools/prepare_gallery.py', 'tools/npc_geometry.py', 'tools/prepare_scenery.py',
    'src/mwad/audit.py', 'src/mwad/scene.py', 'src/mwad/paths.py',
    'config/gallery_model_quality.json',
)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def token(value):
    return digest(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())


def environment():
    return {'python': sys.version, 'machine': platform.machine(),
            'platform': sys.platform, 'packages': {n: importlib.metadata.version(n) for n in PACKAGES}}


def converter_sources(root=ROOT):
    return {name: file_sha(root/name) for name in CONVERTER_FILES}


class Dependencies:
    """Hash resolved source bytes, including absent preferred texture candidates.

    Meshes can share a NIF but select different slots/shapes. The full appearance
    specification remains part of the key. NIF material references are scanned
    conservatively, including unused references, rather than guessing dependencies.
    """
    def __init__(self, data):
        self.assets = Assets(Path(data), BSA(child_ci(Path(data), 'Morrowind.bsa')))
        self.hashes = {}
        self.meshes = {}

    def read(self, name):
        try:
            return self.assets.read(name)
        except KeyError:
            return None

    def record(self, name):
        if name not in self.hashes:
            raw = self.read(name)
            self.hashes[name] = None if raw is None else digest(raw)
        return self.hashes[name]

    def mesh(self, name):
        if name not in self.meshes:
            raw = self.read(name)
            if raw is None:
                raise ValueError('Missing gallery source mesh: ' + name)
            self.hashes[name] = digest(raw)
            N = nif_reader(); data = N.Data(); data.read(io.BytesIO(raw))
            names = {name}
            for block in data.get_global_iterator():
                if isinstance(block, N.NiSourceTexture) and block.file_name:
                    texture = normpath(block.file_name.decode('cp1252'))
                    if not texture.startswith('textures/'):
                        texture = 'textures/' + texture
                    # Match Assets.texture's DDS-first fallback and detect newly
                    # added overrides even if the previous candidate was absent.
                    names.update((str(PurePosixPath(texture).with_suffix('.dds')), texture))
            self.meshes[name] = sorted(names)
        return self.meshes[name]

    def for_spec(self, spec):
        if spec['kind'] == 'NPC_':
            a = spec['appearance']
            meshes = {normpath(a['skeleton'])} | {normpath('meshes/' + p['mesh']) for p in a['parts']}
        else:
            meshes = {normpath('meshes/' + spec['mesh'])}
        names = set()
        for name in sorted(meshes):
            names.update(self.mesh(name))
        return {name: self.record(name) for name in sorted(names)}

    def verify_unchanged(self):
        # Do not publish a successful run after its game inputs changed in flight.
        for name, expected in self.hashes.items():
            raw = self.read(name)
            if (None if raw is None else digest(raw)) != expected:
                raise ValueError('Gallery source changed during conversion: ' + name)


def identity(spec, palette, dependencies, sources, env):
    from prepare_gallery import model_quality
    return {'format': FORMAT, 'spec': spec, 'palette_sha256': digest(palette),
            'dependencies': dependencies, 'sources': sources, 'environment': env,
            'cache_implementation': file_sha(Path(__file__)),
            'quality': model_quality(spec), 'retry_policy': 'unchanged bounded 666 then 1024'}


def checked_result(raw, result, key, palette_sha):
    if (result.get('status') != 'ready' or result.get('key') != key or
            result.get('sha256') != digest(raw) or result.get('bytes') != len(raw) or
            result.get('palette_sha256') != palette_sha or len(raw) < 84 or
            raw[:8] != b'IDPO\x06\0\0\0'):
        raise ValueError('Incomplete or changed gallery model/receipt pair')
    vertices, triangles = struct.unpack_from('<ii', raw, 60)
    if (vertices != result.get('vertices') or triangles != result.get('triangles') or
            not 0 < vertices <= 3072 or not 0 < triangles <= 1024):
        raise ValueError('Gallery cache model budget differs from receipt')
    return result


def atomic_write(path, raw):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(raw); f.flush(); os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def load(cache, ident, key):
    directory = Path(cache) / token(ident)[:2] / token(ident)
    try:
        record = json.loads((directory/'entry.json').read_text())
        if record['identity'] != ident:
            raise ValueError('Cache identity mismatch')
        raw = (directory/'model.mdl').read_bytes()
        result = checked_result(raw, record['result'], key, ident['palette_sha256'])
        return raw, result
    except (OSError, ValueError, KeyError, TypeError):
        return None


def publish(cache, ident, key, raw, result):
    checked_result(raw, result, key, ident['palette_sha256'])
    directory = Path(cache) / token(ident)[:2] / token(ident)
    existing = load(cache, ident, key)
    if existing is not None:
        if existing[0] != raw:
            raise ValueError('Different model bytes for the same gallery cache identity')
        return
    # Receipt is the commit marker. Readers always hash both files, so a partial
    # write or concurrent repair is a miss, never an accepted partial model.
    atomic_write(directory/'model.mdl', raw)
    atomic_write(directory/'entry.json', (json.dumps({'identity': ident, 'result': result}, sort_keys=True)+'\n').encode())


def materialize(output, key, raw, result):
    atomic_write(Path(output)/(key+'.mdl'), raw)
    atomic_write(Path(output)/(key+'.json'), (json.dumps(result, indent=2)+'\n').encode())


_worker_assets = None
_worker_data = None


def verify_dependencies(data, ident):
    if converter_sources() != ident['sources'] or file_sha(Path(__file__)) != ident['cache_implementation']:
        raise ValueError('Gallery converter changed before cache publication')
    global _worker_assets, _worker_data
    if _worker_data != str(data):
        _worker_assets = Assets(Path(data), BSA(child_ci(Path(data), 'Morrowind.bsa')))
        _worker_data = str(data)
    for name, expected in ident['dependencies'].items():
        try: actual = digest(_worker_assets.read(name))
        except KeyError: actual = None
        if actual != expected:
            raise ValueError('Gallery input changed before cache publication: ' + name)


def convert_cached(task):
    from prepare_gallery import convert_model, GALLERY_FACE_LIMIT
    data, output, key, spec, palette, cache, ident = task
    started = time.monotonic()
    found = load(cache, ident, key)
    if found is not None:
        raw, result = found; materialize(output, key, raw, result)
        return result, 'hit', round(time.monotonic()-started, 6)
    verify_dependencies(data, ident)
    result = convert_model((data, output, key, spec, palette))
    if result['status'] != 'ready' and 'Alias' in result.get('error', ''):
        result = convert_model((data, output, key, dict(spec, face_limit=GALLERY_FACE_LIMIT), palette))
    if result['status'] == 'ready':
        verify_dependencies(data, ident)
        publish(cache, ident, key, (Path(output)/(key+'.mdl')).read_bytes(), result)
    return result, 'converted', round(time.monotonic()-started, 6)


def import_rc9(run, data, palette, specs, identities, cache, env):
    """Import completed pairs only from a stopped, provenance-compatible rc9 run.

    This does not trust loose old model files, mtimes or an unchanged filename.
    Full original input inventory, converter sources, Python/packages, palette
    and each output pair must match. Incomplete pairs are left for conversion.
    """
    from prepare_gallery import model_quality
    run = ensure_external(Path(run), 'rc9 gallery seed run').resolve()
    state = json.loads((run/'build-state.json').read_text())
    if (state.get('schema') != 'amiwind-build-receipt-v1' or state.get('runtime_version') != '0.0.25-rc9' or
            state.get('status') not in ('passed', 'failed', 'cancelled')):
        raise ValueError('Gallery seed must be a stopped rc9 build with provenance; keep a running build intact')
    source = run/'npc-gallery'
    steps = [s for s in state.get('steps', []) if s['name'] == 'npc-gallery']
    if len(steps) != 1 or '--out' not in steps[0]['command']:
        raise ValueError('Seed run has no recorded gallery command')
    command = steps[0]['command']
    if Path(command[command.index('--out')+1]).resolve() != source.resolve():
        raise ValueError('Seed gallery output differs from its recorded command')
    if state.get('python') != env['python']:
        raise ValueError('Seed Python differs; use ordinary conversion')
    recorded = {r['name']: r.get('detected') for r in state.get('version_comparison', [])}
    if any(recorded.get(n) != version for n, version in env['packages'].items()):
        raise ValueError('Seed conversion package versions differ')
    sources = converter_sources()
    # rc9's source receipt records Python files, not JSON; protected quality
    # settings are checked against each model's original conversion receipt.
    if any(state.get('source_sha256', {}).get(n) != sha for n, sha in sources.items() if n.endswith('.py')):
        raise ValueError('Seed converter sources differ')
    inputs = {str(p.relative_to(data)): file_sha(p) for p in sorted(Path(data).rglob('*'))
              if p.is_file() and is_game_input(p.relative_to(data))}
    if not inputs or state.get('input_sha256') != inputs:
        raise ValueError('Seed game input inventory/hashes differ')
    if (source/'gfx/palette.lmp').read_bytes() != palette:
        raise ValueError('Seed gallery palette differs')
    imported = rejected = 0
    pending = []
    for key, spec in specs.items():
        try:
            raw = (source/'gallery'/(key+'.mdl')).read_bytes()
            result = json.loads((source/'gallery'/(key+'.json')).read_text())
            checked_result(raw, result, key, digest(palette))
            quality = model_quality(spec)
            quality_id = digest(json.dumps(quality, sort_keys=True).encode()) if quality else ''
            if result.get('quality_profile') != quality_id or result.get('quality_settings') != quality:
                raise ValueError('Seed protected quality profile differs')
            pending.append((key, len(raw)))
        except (OSError, ValueError, KeyError, TypeError):
            rejected += 1
    require_space([(Path(cache), sum(size + len(json.dumps(identities[key])) + 16384 for key, size in pending))])
    for key, _ in pending:
        raw = (source/'gallery'/(key+'.mdl')).read_bytes()
        result = json.loads((source/'gallery'/(key+'.json')).read_text())
        publish(cache, identities[key], key, raw, result)
        imported += 1
    return {'imported': imported, 'missing_or_rejected': rejected, 'source_state_sha256': file_sha(run/'build-state.json')}


def cache_location(path, data, output):
    path = ensure_external(Path(path), 'persistent NPC gallery cache').resolve()
    data = Path(data).resolve(); output = Path(output).resolve()
    if any(inside(a, b) or inside(b, a) for a, b in ((path, data), (path, output))):
        raise ValueError('Gallery cache must be separate from game inputs and run output')
    path.mkdir(parents=True, exist_ok=True)
    return path


def require_space(requests):
    """Check shared-filesystem totals before model copies/conversion, with margin."""
    volumes = {}
    for path, size in requests:
        path = Path(path)
        volume = path.stat().st_dev
        previous = volumes.get(volume, (path, 0))
        volumes[volume] = (path, previous[1] + size)
    for path, size in volumes.values():
        required = size + 128*1024*1024
        available = shutil.disk_usage(path).free
        if available < required:
            raise ValueError(f'Insufficient gallery capacity: need {required} free bytes including margin; have {available}. Keep completed outputs; provide space without omitting models.')


def preflight(cache, output, identities):
    """Conservative one-frame gallery bound; hits use measured verified sizes."""
    output_bytes = 64*1024*1024  # catalogue, footprint models and map scratch
    cache_bytes = 0
    hits = 0
    for key, ident in identities.items():
        found = load(cache, ident, key)
        if found:
            output_bytes += len(found[0]) + len(json.dumps(found[1]))
            hits += 1
        else:
            # One-frame IDPO, <=3072 vertices/1024 triangles and <=512x480
            # palette skin, plus model receipt. Preserve existing codec limits.
            output_bytes += 360*1024
            cache_bytes += 360*1024 + len(json.dumps(ident))
        output_bytes += 1024  # footprint model and catalogue row
    require_space([(Path(cache), cache_bytes), (Path(output), output_bytes)])
    return {'verified_hits': hits, 'misses': len(identities)-hits,
            'output_estimate_bytes': output_bytes, 'new_cache_estimate_bytes': cache_bytes}
