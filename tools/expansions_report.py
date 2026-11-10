"""The expansions report: one plain block per expansion (Tribunal, Bloodmoon) in every build.

Printed right after the game-file check, again in the build summary at the end, and kept as the "expansions" record
in build-state.json and build-summary.json. It says whether each expansion's master and archive were found, what of
it the build uses now, and what waits for its own world (Mournhold, Solstheim; DLC-BUILD-LATER).

Instrumentation only: it reads what the build already has at hand (the game-file check's verdicts with the masters'
header record counts and the archives' file counts, the MWScript tracker docs/mwscript-features.json when it was
measured on the same masters, and the image's creature census when the run wrote one). No extra pass over the game
data, no build output, never a stage key. A missing master or archive is a clear warning line, never silent.
The coming --no-dlc flag (DLC-BUILD-LATER) only has to pass no_dlc=True: the line then reads "left out by --no-dlc".
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'amiwind-expansions-v1'
TRACKER = ROOT / 'docs/mwscript-features.json'
CENSUS = Path('image/creature-census.json')
REGISTER = 'DLC-BUILD-LATER'
# name, master, archive, its own world
EXPANSIONS = (('Tribunal', 'Tribunal.esm', 'Tribunal.bsa', 'Mournhold'),
              ('Bloodmoon', 'Bloodmoon.esm', 'Bloodmoon.bsa', 'Solstheim'))
RUN_STATES = ('runs', 'carried')        # docs/mwscript-features.json states of a script that runs in the image
WAIT_STATE = 'not-in-image'             # placed only in an add-on's world


def _file(records, name):
    for record in records:
        if record['name'].casefold() == name.casefold():
            return record
    return None


def script_counts(game_data, tracker=TRACKER):
    """{master: {'total', 'run', 'waits'}} from the MWScript tracker, or (None, why) when it is not there or was
    measured on other masters than these (their SHA-256 differ)."""
    try:
        doc = json.loads(Path(tracker).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None, 'MWScript tracker not readable'
    measured = (doc.get('measured') or {}).get('masters') or {}
    have = {r['name']: r.get('sha256') for r in (game_data or {}).get('files', []) if r['kind'] == 'tes3-master'}
    if any(measured.get(name) != digest for name, digest in have.items() if name in measured) or not measured:
        return None, 'MWScript tracker measured on other masters'
    out = {}
    for row in doc.get('scripts') or []:
        entry = out.setdefault(row.get('master'), {'total': 0, 'run': 0, 'waits': 0})
        entry['total'] += 1
        entry['run'] += row.get('state') in RUN_STATES
        entry['waits'] += row.get('state') == WAIT_STATE
    return out, 'docs/mwscript-features.json (v%s)' % doc.get('version', '?')


def creature_counts(census):
    """{master: {'records', 'built'}} of a creature census (tools/creature_census.py), or None."""
    if not census or 'built' not in (census.get('totals') or {}):
        return None
    registers = {m.get('name'): m.get('register') for m in census.get('masters', [])}
    out = {m: {'records': n, 'built': n, 'register': registers.get(m)}
           for m, n in census['totals'].get('per_master', {}).items()}
    for group in census.get('groups', []):
        for row in group.get('records', []):
            if row.get('master') in out:
                out[row['master']]['built'] -= 1
    for row in census.get('unclassified', []):
        if row.get('master') in out:
            out[row['master']]['built'] -= 1
    return out


def report(game_data, no_dlc=False, tracker=TRACKER, census=None, selected=None):
    """The expansions record from the game-file check's report (known_inputs.check_game_data). SELECTED (--dlc): the
    expansion names the build asks for, None = every one found; 'layers' lists the found ones the build uses."""
    if selected == []:
        no_dlc = True
    files = (game_data or {}).get('files', [])
    scripts, scripts_source = (None, 'not counted') if no_dlc else script_counts(game_data, tracker)
    creatures = creature_counts(census)
    rows = []
    for name, master_name, archive_name, world in EXPANSIONS:
        master, archive = _file(files, master_name), _file(files, archive_name)
        usable = lambda r: r is not None and r.get('verdict') != 'invalid'
        if no_dlc:
            status = 'left out by --no-dlc'
        elif selected is not None and name not in selected:
            status = 'left out by --dlc'
        elif usable(master) and usable(archive):
            status = 'found'
        elif usable(master):
            status = 'partly found'
        else:
            status = 'not found'
        identity = lambda r: None if r is None else {
            'name': r['name'], 'version': r.get('version'), 'sha256': r.get('sha256'), 'verdict': r.get('verdict'),
            'label': r.get('label'), 'bytes': r.get('bytes')}
        row = {'name': name, 'status': status, 'world': world, 'register': REGISTER,
               'master': identity(master), 'archive': identity(archive),
               'records': (master or {}).get('identity', {}).get('records') if usable(master) else None,
               'archive_files': (archive or {}).get('identity', {}).get('files') if usable(archive) else None,
               'scripts': (scripts or {}).get(master_name) if status in ('found', 'partly found') else None,
               'creatures': (creatures or {}).get(master_name) if status in ('found', 'partly found') else None}
        rows.append(row)
    return {'schema': SCHEMA, 'no_dlc': bool(no_dlc), 'selected': None if selected is None else list(selected),
            'layers': [row['name'] for row in rows if row['status'] == 'found'],
            'scripts_source': scripts_source,
            'creatures_source': 'image/creature-census.json' if creatures else 'not counted yet (the image step)',
            'expansions': rows}


def finish(record, run, tracker=TRACKER):
    """The record of the build summary: the start record with the image's creature census added when it is there."""
    if not record:
        return None
    path = Path(run) / CENSUS
    try:
        census = json.loads(path.read_text(encoding='utf-8')) if path.is_file() else None
    except (OSError, ValueError):
        census = None
    creatures = creature_counts(census)
    if creatures is None:
        return record
    out = dict(record, creatures_source=str(CENSUS),
               expansions=[dict(row) for row in record['expansions']])
    for row in out['expansions']:
        if row['master'] and row['status'] in ('found', 'partly found'):
            row['creatures'] = creatures.get(row['master']['name'])
    return out


def _n(value):
    return '{:,}'.format(value)


def lines(record, at_end=False):
    """The block as it prints: 'Expansions:' and one line per expansion; missing ones start with [warning]."""
    if not record:
        return []
    out = ['Expansions:']
    for row in record['expansions']:
        master, archive = row['master'], row['archive']
        if row['status'] == 'left out by --no-dlc':
            out.append('  %s: LEFT OUT by --no-dlc: none of its records, scripts, creatures or archive files are '
                       'built; its world %s waits (%s).' % (row['name'], row['world'], row['register']))
            continue
        if row['status'] == 'left out by --dlc':
            out.append('  %s: LEFT OUT by --dlc: not chosen for this build; none of it is built, its world %s neither '
                       '(%s).' % (row['name'], row['world'], row['register']))
            continue
        if row['status'] == 'not found':
            why = ('%s is not a usable master (%s)' % (master['name'], master.get('verdict'))) if master else \
                'no %s in Data Files' % EXPANSION_FILES[row['name']][0]
            out.append('  [warning] %s: NOT FOUND (%s): left out; nothing of it is built, its world %s neither.'
                       % (row['name'], why, row['world']))
            continue
        files = '%s%s' % (master['name'], ' v' + master['version'] if master.get('version') else '')
        files += ' + ' + archive['name'] if row['status'] == 'found' else ', no ' + EXPANSION_FILES[row['name']][1]
        files += ', ' + master['label'] if master.get('label') else ', not a known edition (%s)' % master.get('verdict')
        used = ['%s records in its master' % _n(row['records'])] if row['records'] is not None else []
        if row['archive_files'] is not None:
            used.append('%s files in its archive' % _n(row['archive_files']))
        scripts = row['scripts']
        if scripts:
            used.append('%s of its %s scripts run in Vvardenfell' % (_n(scripts['run']), _n(scripts['total'])))
        creatures = row['creatures']
        if creatures:
            used.append('%d of %d creatures built%s' % (creatures['built'], creatures['records'],
                                                        ' (%s)' % creatures['register']
                                                        if creatures.get('register') and creatures['built'] < creatures['records'] else ''))
        elif not at_end:
            used.append('creatures counted in the summary')
        waits = 'Waits for its world: %s' % row['world']
        waits += ' (%s scripts, %s).' % (_n(scripts['waits']), row['register']) if scripts else ' (%s).' % row['register']
        prefix = '  [warning] ' if row['status'] == 'partly found' else '  '
        status = 'PARTLY FOUND' if row['status'] == 'partly found' else 'FOUND'
        out.append('%s%s: %s (%s). Used now: %s. %s' % (prefix, row['name'], status, files, ', '.join(used), waits))
    if record.get('scripts_source') and not record.get('no_dlc'):
        out.append('  (scripts: %s; creatures: %s)' % (record['scripts_source'], record['creatures_source']))
    return out


EXPANSION_FILES = {name: (master, archive) for name, master, archive, _ in EXPANSIONS}
