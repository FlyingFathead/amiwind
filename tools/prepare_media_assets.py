#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Import every available owned sound and known video into a private catalogue.

Discovery is separate from playback eligibility. Listing a voiced INFO record
does not execute its conditions or make text-only dialogue into recorded speech.
"""
import argparse
import copy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mwad.audit import BSA, records, subrecords, string
from mwad.paths import child_ci, ensure_external, resolve_data_files
from build_jobs import add_jobs, resolve_jobs

AUDIO_SUFFIXES = {'.wav', '.mp3', '.ogg', '.flac'}
MASTERS = ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def key(path):
    value = str(path).replace('\\', '/').casefold()
    if value.startswith('/') or any(p in ('', '.', '..') for p in value.split('/')) or ':' in value:
        raise ValueError('Invalid media source path: ' + value)
    return value


def discover(data):
    """Named archives in original order; loose assets override archived copies."""
    assets, ignored, containers = {}, [], []
    for name in MASTERS:
        archive = child_ci(data, Path(name).with_suffix('.bsa').name, required=False)
        if archive is None:
            continue
        bsa = BSA(archive)
        containers.append({'file': archive.name, 'sha256': sha(archive)})
        for name, record in bsa.entries.items():
            path = key(name)
            if path.startswith('sound/') and Path(path).suffix in AUDIO_SUFFIXES:
                assets[path] = {'source': path, 'archive': str(archive), **record}
    for category in ('Sound', 'Music', 'Video'):
        folder = child_ci(data, category, required=False)
        if folder is None:
            continue
        seen = set()
        for source in sorted(p for p in folder.rglob('*') if p.is_file()):
            relative = source.relative_to(data).as_posix()
            path = key(relative)
            if path in seen:
                raise ValueError('Case-ambiguous media file: ' + relative)
            seen.add(path)
            suffix = source.suffix.casefold()
            if ((category in ('Sound', 'Music') and suffix in AUDIO_SUFFIXES)
                    or (category == 'Video' and suffix == '.bik')):
                assets[path] = {'source': path, 'source_spelling': relative,
                                'file': str(source), 'bytes': source.stat().st_size}
            else:
                ignored.append({'source': relative, 'bytes': source.stat().st_size,
                                'reason': 'non-media metadata or unsupported extension'})
    return assets, ignored, containers


def resolve_sound(path, assets):
    requested = key(path)
    if not requested.startswith('sound/'):
        requested = 'sound/' + requested
    if requested in assets:
        return requested
    if requested.endswith('.wav'):
        fallback = requested[:-4] + '.mp3'
        if fallback in assets:
            return fallback
    return None


def lookups(data, assets):
    sounds, voices, masters = [], [], []
    provenance, tombstones = [], []
    for master_order, name in enumerate(MASTERS):
        master = child_ci(data, name, required=False)
        if master is None:
            masters.append({'file': name, 'order': master_order, 'status': 'missing_source'})
            continue
        master_bytes = master.read_bytes()
        masters.append({'file': name, 'order': master_order, 'status': 'available', 'sha256': sha(master)})
        topic = ''
        for record_order, (tag, flags, raw) in enumerate(records(master_bytes)):
            if tag not in ('DIAL', 'INFO', 'SOUN'):
                continue
            ordered_subrecords = list(subrecords(raw))
            fields = dict(ordered_subrecords)
            deleted = bool(flags & 0x20) or 'DELE' in fields
            if tag == 'DIAL':
                topic = string(fields.get('NAME', b''))
                if deleted:
                    tombstones.append({
                        'record_type': tag, 'record_id': topic,
                        'master': name, 'master_order': master_order,
                        'record_order': record_order, 'record_flags': flags,
                        'status': 'deleted', 'topic': topic,
                        'subrecords': [{'tag': subtag, 'data_hex': value.hex()}
                                       for subtag, value in ordered_subrecords],
                        'sound_references': [],
                    })
                continue

            ref_field = 'FNAM' if tag == 'SOUN' else 'SNAM'
            id_field = 'NAME' if tag == 'SOUN' else 'INAM'
            record_id = string(fields.get(id_field, b''))
            requested_values = [string(value) for subtag, value in ordered_subrecords
                                if subtag == ref_field and string(value)]
            raw_record = {
                'record_type': tag, 'record_id': record_id,
                'master': name, 'master_order': master_order,
                'record_order': record_order, 'record_flags': flags,
                'status': 'deleted' if deleted else 'active',
                'topic': topic if tag == 'INFO' else None,
                'subrecords': [{'tag': subtag, 'data_hex': value.hex()}
                               for subtag, value in ordered_subrecords],
                'sound_references': [
                    {'requested': requested,
                     'resolved': resolve_sound(requested, assets)}
                    for requested in requested_values],
            }
            if deleted:
                tombstones.append(raw_record)
                continue
            provenance.append(raw_record)

            if not fields.get(ref_field):
                continue
            source = string(fields[ref_field])
            row = {'master': name, 'master_order': master_order,
                   'record_order': record_order, 'record_flags': flags,
                   'id': record_id, 'requested': source,
                   'resolved': resolve_sound(source, assets)}
            if tag == 'INFO':
                row.update(topic=topic, speaker=string(fields.get('ONAM', b'')),
                           race=string(fields.get('RNAM', b'')), text=string(fields.get('NAME', b'')))
                voices.append(row)
            else:
                row['parameters_hex'] = fields.get('DATA', b'').hex()
                sounds.append(row)
    return {'masters': masters, 'sounds': sounds, 'voiced_dialogue': voices,
            'record_provenance': provenance, 'deletion_tombstones': tombstones,
            'provenance_format': 'MWLOOKUP1; ordered subrecord bytes are hex encoded',
            'eligibility': 'source lookup only; dialogue conditions and load-order evaluation remain runtime responsibilities'}


def sound_output(source):
    return 'sound/pool/a' + hashlib.sha256(source.encode('utf-8')).hexdigest()[:16] + '.wav'


def convert_sound(task):
    record, output, ffmpeg = task
    record = dict(record)
    relative = sound_output(record['source'])
    target = output / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix='amiwind-audio-') as temporary:
            if 'archive' in record:
                source = Path(temporary) / 'source'
                with Path(record['archive']).open('rb') as stream:
                    stream.seek(record['offset']); raw = stream.read(record['bytes'])
                if len(raw) != record['bytes']:
                    raise ValueError('Truncated archived sound')
                source.write_bytes(raw)
            else:
                source = Path(record['file'])
            record['source_sha256'] = sha(source)
            subprocess.run([ffmpeg, '-v', 'error', '-nostdin', '-threads', '1', '-i', str(source),
                            '-threads', '1', '-filter_threads', '1', '-vn', '-ac', '1', '-ar', '11025',
                            '-c:a', 'pcm_u8', '-n', str(target)], check=True, capture_output=True)
        with wave.open(str(target)) as audio:
            if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 1, 11025):
                raise ValueError('Invalid converted PCM format')
            frames = audio.getnframes()
            if frames <= 0 or len(audio.readframes(frames)) != frames:
                raise ValueError('Empty or truncated converted PCM')
        return {'source': record['source'], 'source_sha256': record['source_sha256'],
                'category': 'voices' if record['source'].startswith('sound/vo/') else 'effects',
                'status': 'included', 'path': relative, 'bytes': target.stat().st_size,
                'sha256': sha(target), 'frames': frames, 'rate': 11025}
    except (OSError, ValueError, wave.Error, subprocess.CalledProcessError) as error:
        # Partial files are never referenced as valid assets.
        return {'source': record['source'], 'category': 'voices' if record['source'].startswith('sound/vo/') else 'effects',
                'path': relative, 'status': 'missing_output', 'error': str(error)[:400]}


def coverage(rows, references=()):
    result = {}
    for category in ('videos', 'music', 'voices', 'effects'):
        group = [r for r in rows if r['category'] == category]
        missing = {key('sound/' + r['requested']) for r in references
                   if not r.get('resolved') and r.get('category') == category}
        result[category] = {'included': sum(r['status'] == 'included' for r in group),
                            'missing_source': sum(r['status'] == 'missing_source' for r in group) + len(missing),
                            'missing_output': sum(r['status'] == 'missing_output' for r in group),
                            'available_sources': sum(r['status'] != 'missing_source' for r in group)}
    return result


def summary_lines(counts):
    return [f"Included {r['included']} {name}; {r['missing_source']} missing sources; {r['missing_output']} missing outputs."
            for name, r in counts.items()]


def prepare(data, output, ffmpeg='ffmpeg', jobs=None, videos=True):
    data = resolve_data_files(data); output = ensure_external(output, 'complete media catalogue')
    output.mkdir(parents=True, exist_ok=False)
    assets, ignored, archives = discover(data)
    lookup = lookups(data, assets)
    # Source provenance is written before conversion so interruption is inspectable.
    (output / 'source-inventory.json').write_text(json.dumps({'assets': assets, 'ignored': ignored, 'archives': archives}, indent=2)+'\n')
    rows = []
    tasks = [(r, output/'id1', ffmpeg) for source, r in sorted(assets.items()) if source.startswith('sound/')]
    paths = [sound_output(r['source']) for r, _, _ in tasks]
    if len(paths) != len(set(paths)):
        raise ValueError('Sound output hash collision; no files converted')
    workers = min(resolve_jobs(jobs), max(1, len(tasks)))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for i, row in enumerate(executor.map(convert_sound, tasks), 1):
            rows.append(row)
            if i % 100 == 0 or i == len(tasks):
                print(f'Sound import {i}/{len(tasks)}', flush=True)
    if videos:
        from prepare_video import VIDEO_CATALOG, prepare_video
        video_sources = {Path(k).name: r for k, r in assets.items() if k.startswith('video/')}
        known = {source for _, _, source in VIDEO_CATALOG}
        for number, name, source_name in VIDEO_CATALOG:
            row = {'category': 'videos', 'source': 'video/'+source_name, 'id': number, 'name': name}
            source = video_sources.get(source_name)
            if source is None:
                rows.append(dict(row, status='missing_source')); continue
            try:
                relative = 'intro/mw_intro.awv' if number == 15 else f'intro/video/{number:02}.awv'
                with tempfile.TemporaryDirectory(prefix='video-', dir=output) as temporary:
                    converted = Path(temporary)/'converted'
                    info = prepare_video(source['file'], converted, ffmpeg, (160, 100), output_name='movie.awv')
                    target = output/'id1'/relative; target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(converted/'movie.awv', target)
                rows.append(dict(row, status='included', path=relative, sha256=sha(target),
                                 bytes=target.stat().st_size, source_sha256=info['source_sha256']))
            except (OSError, ValueError, subprocess.CalledProcessError) as error:
                rows.append(dict(row, status='missing_output', error=str(error)[:400]))
        # Unrecognized installed videos must never vanish silently.
        for name, source in video_sources.items():
            if name not in known:
                row = {'category': 'videos', 'source': source['source'], 'name': name,
                       'path': 'intro/extra/v'+hashlib.sha256(source['source'].encode()).hexdigest()[:16]+'.awv'}
                try:
                    with tempfile.TemporaryDirectory(prefix='video-', dir=output) as temporary:
                        converted = Path(temporary)/'converted'
                        info = prepare_video(source['file'], converted, ffmpeg, (160, 100), output_name='movie.awv')
                        target = output/'id1'/row['path']; target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(converted/'movie.awv', target)
                    rows.append(dict(row, status='included', sha256=sha(target), bytes=target.stat().st_size,
                                     source_sha256=info['source_sha256'], lookup='JSON path; no legacy numeric video ID'))
                except (OSError, ValueError, subprocess.CalledProcessError) as error:
                    rows.append(dict(row, status='missing_output', error=str(error)[:400]))
        catalogue = ['AWVC1'] + [f"{r['id']} {r['name']} {r['path']}" for r in rows
                                if r['category'] == 'videos' and r['status'] == 'included' and 'id' in r]
        (output/'id1/intro').mkdir(parents=True, exist_ok=True)
        (output/'id1/intro/videos.awl').write_text('\n'.join(catalogue)+'\n', encoding='ascii')
    for group, category in (('sounds', 'effects'), ('voiced_dialogue', 'voices')):
        for r in lookup[group]:
            r['category'] = category
    by_source = {r['source']: r for r in rows}
    for group in ('sounds', 'voiced_dialogue'):
        for r in lookup[group]:
            target = by_source.get(r['resolved'], {})
            r['output'] = target.get('path') if target.get('status') == 'included' else None
    counts = coverage(rows, lookup['sounds']+lookup['voiced_dialogue'])
    report = {'format': 'AWMEDIA1', 'expected_known_videos': 17,
              'status': 'complete' if not any(r['missing_output'] for r in counts.values()) else 'missing_outputs',
              'categories': counts, 'entries': rows, 'lookups': lookup, 'ignored_nonmedia': ignored,
              'music': 'Converted by the separate complete soundtrack stage; reconciled at image assembly',
              'runtime': 'On-disk converted assets and source lookup tables; does not preload all audio or implement every event trigger'}
    (output/'id1/media').mkdir(parents=True, exist_ok=True)
    (output/'id1/media/catalogue.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    (output/'media-coverage.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    for line in summary_lines(counts): print(line, flush=True)
    for category, count in counts.items():
        if count['missing_source']:print(f"[warning: missing source] {category}: {count['missing_source']}", flush=True)
        if count['missing_output']:print(f"[warning: missing output] {category}: {count['missing_output']}", flush=True)
    return report


def stage_catalogue(media, id1, music_manifest, intro_receipt=None):
    """Copy only validated outputs; bind coverage to the final prepared payload.

    Preserve the higher-resolution story intro when its original source digest
    matches. All other collisions must be byte-identical, never overwritten.
    """
    media = ensure_external(media, 'converted media'); id1 = ensure_external(id1, 'image payload')
    report = copy.deepcopy(json.loads((media/'media-coverage.json').read_text()))
    if report.get('format') != 'AWMEDIA1':
        raise ValueError('Unsupported media catalogue')
    seen = set()
    for row in report['entries']:
        if row['status'] != 'included':continue
        relative = key(row['path'])
        if relative in seen:raise ValueError('Duplicate converted media output path')
        seen.add(relative)
        src, target = media/'id1'/relative, id1/relative
        try:
            if not src.is_file() or sha(src) != row['sha256']:
                raise ValueError('Converted media file absent or changed')
            if target.exists() and relative == 'intro/mw_intro.awv':
                if not intro_receipt or intro_receipt.get('source_sha256') != row.get('source_sha256'):
                    raise ValueError('Existing story intro lacks matching source provenance')
                from prepare_video import validate
                validate(target)
                row['reused_story_intro'] = True
            elif target.exists():
                if sha(target) != row['sha256']:raise ValueError('Conflicting existing media payload')
            else:
                target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(src, target)
            row['sha256'], row['bytes'] = sha(target), target.stat().st_size
        except (OSError, ValueError) as error:
            row.update(status='missing_output', error=str(error)[:400])
    inventory = json.loads((media/'source-inventory.json').read_text())['assets']
    music_by_source = {key(r['source']): r for r in music_manifest['tracks']}
    for source in sorted(k for k in inventory if k.startswith('music/')):
        track = music_by_source.get(source)
        row = {'category': 'music', 'source': source, 'status': 'missing_output'}
        if track:
            relative = 'music/'+key(track['file']); target=id1/relative
            row['path'] = relative
            original = inventory[source]
            source_matches = ('file' in original and track.get('source_sha256')
                              and sha(original['file']) == track['source_sha256'])
            if target.is_file() and source_matches and sha(target) == track['sha256']:
                row.update(status='included', bytes=target.stat().st_size, sha256=track['sha256'],
                           source_sha256=track.get('source_sha256'))
        if row['status'] == 'missing_output':row['error']='Available music source has no validated staged output'
        report['entries'].append(row)
    targets = {r['source']: r for r in report['entries']}
    references = report['lookups']['sounds']+report['lookups']['voiced_dialogue']
    for ref in references:
        row = targets.get(ref.get('resolved'), {})
        ref['output'] = row.get('path') if row.get('status') == 'included' else None
    report['categories'] = coverage(report['entries'], references)
    report['expected_known_videos'] = 17
    report['scope'] = 'staged-payload; final HDF readback remains the image builder responsibility'
    report['status'] = 'complete' if not any(r['missing_output'] for r in report['categories'].values()) else 'missing_outputs'
    catalogue = ['AWVC1']+[f"{r['id']} {r['name']} {r['path']}" for r in report['entries']
                         if r['category']=='videos' and r['status']=='included' and 'id' in r]
    (id1/'intro').mkdir(parents=True,exist_ok=True)
    (id1/'intro/videos.awl').write_text('\n'.join(catalogue)+'\n', encoding='ascii', newline='\n')
    (id1/'media').mkdir(parents=True, exist_ok=True)
    (id1/'media/catalogue.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    for line in summary_lines(report['categories']):print(line, flush=True)
    for category, counts in report['categories'].items():
        for field, label in (('missing_source', 'missing source'), ('missing_output', 'missing output')):
            if counts[field]:print(f"[warning: {label}] {category}: {counts[field]}", flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-files', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--ffmpeg', default='ffmpeg')
    add_jobs(parser)
    args = parser.parse_args()
    prepare(args.data_files, args.out, args.ffmpeg, args.jobs)
