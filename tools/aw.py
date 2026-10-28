#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""aw: the master builder's command line (phase 1). Standard library only, Python 3.10+.

One owner of the shared build state: workers ask `aw` for a gate number, a worktree or a run name (a lease),
run gates through it and get back a result in a fixed JSON form (config/schemas/aw-result-1.json) with an
exit code that tells the truth. docs/AW.md describes the commands and the config file.

    aw enter                                  entry check of this source tree (version, integration head, PYTHONPATH)
    aw gate --repo PATH [--commit C] [--reason R] [--range NAME]
                                              lease a gate number, run the gate, judge it from its output files
    aw status                                 working version, integration head, active leases, recent results
    aw lease gate|worktree|run-name|renew|release|list ...
    aw submit REQUEST.json [--dry-run]        hand the build server one request (gate or build; tools/aw_service.py)
    aw request --kind K --repo PATH ...       write one request from options and submit it
    aw announce / inbox / reply / publish / sync-version
                                              the builder broadcast: calls for fixes, new builder heads, the
                                              answers of every worker (tools/aw_broadcast.py)

Every location comes from a config file (--config FILE or the environment variable AMIWIND_AW_CONFIG); the tool
itself holds no paths. Every request, result and lease is appended to the trial log (JSON lines).
"""
import argparse
import datetime
import glob
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / 'config' / 'schemas'
CONFIG_ENV = 'AMIWIND_AW_CONFIG'
REQUESTER_ENV = 'AW_REQUESTER'
KINDS = ('gate', 'build', 'miniwind', 'chimport-region', 'smoke')
LEASE_KINDS = ('gate', 'worktree', 'run-name', 'cores')
DEFAULT_TTL = {'gate': 6 * 3600, 'worktree': 24 * 3600, 'run-name': 24 * 3600, 'cores': 24 * 3600}
GATE_STEPS = ('preflight', 'suite', 'host-parity-linux', 'host-parity-windows', 'engine', 'smoke')
GATE_FILES = ('repo', 'preflight', 'suite', 'hostparity', 'engine', 'smoke')
GATE_USED = ('preflight', 'suite', 'engine', 'source')
EXIT = {'passed': 0, 'failed': 1, 'refused': 2}
EXIT_NO_LEASE = 3
VERSION_RE = r'v[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.]+)?'
RUN_NAME = re.compile(r'(?P<date>[0-9]{4}_[0-9]{2}_[0-9]{2})_(?P<version>' + VERSION_RE
                      + r')_(?P<purpose>[A-Za-z0-9][A-Za-z0-9.-]*)_(?P<git>[0-9a-f]{4,40}|nogit)')


class AwError(Exception):
    """A refusal with a message for the user."""


# --------------------------------------------------------------------------
# Time, version, git

def stamp(moment=None):
    """Host time as 'YYYY-MM-DD HH:MM:SS +ZZZZ'."""
    moment = datetime.datetime.now().astimezone() if moment is None else moment
    return moment.strftime('%Y-%m-%d %H:%M:%S %z')


def stamp_epoch(epoch):
    return stamp(datetime.datetime.fromtimestamp(epoch).astimezone())


def repo_version(repo):
    """The full version 'vX.Y.Z[-suffix]' from the repo's VERSION file."""
    text = (Path(repo) / 'VERSION').read_text(encoding='utf-8').strip()
    return 'v' + text.lstrip('v')


def git(repo, *args):
    """stdout of a git command in REPO, or None when git fails or is missing."""
    try:
        result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def git_short(repo, rev='HEAD'):
    full = git(repo, 'rev-parse', '--verify', '--quiet', rev + '^{commit}')
    return full[:7] if full else None


def is_ancestor(repo, commit, rev='HEAD'):
    """True / False / None (cannot tell)."""
    try:
        result = subprocess.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor', commit, rev],
                                capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return {0: True, 1: False}.get(result.returncode)


def safe_part(text, default='x'):
    """Lower-case [a-z0-9.-] for run-name parts (purpose, reason)."""
    text = re.sub(r'[^a-z0-9.-]+', '-', (text or '').lower()).strip('-.')
    return re.sub(r'-{2,}', '-', text) or default


RUN_NAME_MAX = 128   # a run name is also a request id (aw-request-1 "id": at most 128 characters)


def make_run_name(version, purpose, git_hash, reason=None, today=None, attempt=1):
    """YYYY_MM_DD_vX.Y.Z[-suffix]_<purpose>[-<reason>][-tryN]_<gitshort>. The reason part is shortened so the
    name stays a valid request id (RUN_NAME_MAX; AW-RUN-NAME-LONG-REASON-36)."""
    today = today or datetime.date.today()
    version = 'v' + version.lstrip('v')
    part = safe_part(purpose)
    tail = f'-try{attempt}' if attempt > 1 else ''
    git = (git_hash or "nogit")[:7]
    if reason:
        room = RUN_NAME_MAX - len(f'{today:%Y_%m_%d}_{version}_{part}{tail}_{git}') - 1
        short = safe_part(reason)[:max(0, room)].rstrip('-.')
        if short:
            part += '-' + short
    part += tail
    name = f'{today:%Y_%m_%d}_{version}_{part}_{git}'
    if not RUN_NAME.fullmatch(name):
        raise AwError(f'run name {name!r} does not follow the naming rule')
    return name


# --------------------------------------------------------------------------
# JSON schema subset (const, enum, type, required, properties, additionalProperties, items, pattern,
# minLength, minimum) - enough for the aw schemas, no third-party package

TYPES = {'object': dict, 'array': list, 'string': str, 'boolean': bool, 'null': type(None)}


def _type_ok(value, name):
    if name == 'integer':
        return isinstance(value, int) and not isinstance(value, bool)
    if name == 'number':
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, TYPES[name])


def validate(value, schema, path='$'):
    """A list of error strings (empty = valid)."""
    errors = []
    if 'const' in schema and value != schema['const']:
        errors.append(f'{path}: expected {schema["const"]!r}')
    if 'enum' in schema and value not in schema['enum']:
        errors.append(f'{path}: {value!r} not one of {schema["enum"]}')
    if 'type' in schema:
        names = schema['type'] if isinstance(schema['type'], list) else [schema['type']]
        if not any(_type_ok(value, name) for name in names):
            return errors + [f'{path}: expected type {"/".join(names)}, got {type(value).__name__}']
    if isinstance(value, str):
        if len(value) < schema.get('minLength', 0):
            errors.append(f'{path}: shorter than {schema["minLength"]}')
        if 'pattern' in schema and not re.search(schema['pattern'], value):
            errors.append(f'{path}: {value!r} does not match {schema["pattern"]}')
    if isinstance(value, (int, float)) and not isinstance(value, bool) and 'minimum' in schema \
            and value < schema['minimum']:
        errors.append(f'{path}: below {schema["minimum"]}')
    if isinstance(value, dict):
        for key in schema.get('required', []):
            if key not in value:
                errors.append(f'{path}: missing {key!r}')
        props = schema.get('properties', {})
        extra = schema.get('additionalProperties', True)
        for key, item in value.items():
            if key in props:
                errors += validate(item, props[key], f'{path}.{key}')
            elif extra is False:
                errors.append(f'{path}: unexpected {key!r}')
            elif isinstance(extra, dict):
                errors += validate(item, extra, f'{path}.{key}')
    if isinstance(value, list) and 'items' in schema:
        for index, item in enumerate(value):
            errors += validate(item, schema['items'], f'{path}[{index}]')
    return errors


def schema(name):
    return json.loads((SCHEMAS / f'{name}.json').read_text(encoding='utf-8'))


def checked(document, name):
    errors = validate(document, schema(name))
    if errors:
        raise AwError(f'{name} document does not validate: ' + '; '.join(errors[:5]))
    return document


# --------------------------------------------------------------------------
# Config

def load_config(path=None, environ=None):
    environ = os.environ if environ is None else environ
    path = path or environ.get(CONFIG_ENV)
    if not path:
        raise AwError(f'no config: give --config FILE or set {CONFIG_ENV} (docs/AW.md "Config")')
    path = Path(path)
    config = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(config, dict) or 'state_dir' not in config:
        raise AwError(f'{path}: a config needs "state_dir"')

    def resolve(value):
        return str(value if Path(value).is_absolute() else (path.parent / value).resolve())

    config['state_dir'] = resolve(config['state_dir'])
    for key in ('working_version_file', 'trial_log', 'integration_head_file'):
        if config.get(key):
            config[key] = resolve(config[key])
    gate = config.setdefault('gate', {})
    if gate.get('out_dir'):
        gate['out_dir'] = resolve(gate['out_dir'])
    build = config.get('build')
    if isinstance(build, dict) and build.get('trials_log'):
        build['trials_log'] = resolve(build['trials_log'])
    config['_path'] = str(path)
    return config


def state_dir(config):
    folder = Path(config['state_dir'])
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def trial_log_path(config):
    return Path(config.get('trial_log') or state_dir(config) / 'aw-trials.jsonl')


def log_trial(config, event, **fields):
    """One JSON line in the trial log; every line carries the host time."""
    line = {'time': stamp(), 'event': event, **fields}
    path = trial_log_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(line, sort_keys=True) + '\n')
    return line


def file_sha256(path):
    """SHA-256 of a file's bytes (hex)."""
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def perf_db_post(config, document, result_path):
    """The perf database step after a result file is written (docs/PERF_DATABASE.md): the config's perf_db.command,
    a command template with {kind} {run_name} {result} {run_dir}, run once per result. It never changes the result
    (the database reads the result file as written); its outcome is printed, logged in the trial log, and a failure
    is loud on stderr. Returns its exit code, or None when no perf_db command is configured or it is switched off."""
    spec = config.get('perf_db') or {}
    template = spec.get('command')
    if not template or spec.get('enabled') is False or document.get('dry_run'):
        return None
    run_dir = next((str(a) for a in document.get('artifacts') or [] if str(a).startswith('/')), '')
    fill = {'kind': document.get('kind') or '', 'run_name': document.get('run_name') or '',
            'result': str(result_path), 'run_dir': run_dir}
    command = [str(part).format(**fill) for part in template]
    try:
        done = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace',
                              timeout=int(spec.get('timeout_s') or 900))
        code, output = done.returncode, (done.stdout or '') + (done.stderr or '')
    except (OSError, subprocess.SubprocessError) as exc:
        code, output = None, f'{type(exc).__name__}: {exc}'
    lines = [line for line in output.splitlines() if line.strip()]
    for line in lines[-12:]:
        print('aw perf-db: ' + line)
    detail = (lines or [''])[-1][:300]
    if code != 0:
        print(f'aw perf-db: FAILED (exit {code}) for {fill["run_name"]}: {detail}', file=sys.stderr)
    log_trial(config, 'perf-db', run_name=fill['run_name'], kind=fill['kind'], exit=code, detail=detail)
    return code


def write_json(path, document):
    path = Path(path)
    tmp = path.with_name(path.name + f'.tmp-{os.getpid()}')
    tmp.write_text(json.dumps(document, indent=2, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    os.replace(tmp, path)


# --------------------------------------------------------------------------
# Lock: an exclusive lock file, held only for one read-modify-write of the state

class Lock:
    def __init__(self, config, requester='aw', timeout=30.0, poll=0.05):
        self.path = state_dir(config) / 'aw-state.lock'
        self.config = config
        self.stale = float(config.get('lock_stale_s', 300))
        self.timeout, self.poll = timeout, poll
        self.token = f'{requester} pid {os.getpid()} host {socket.gethostname()} at {stamp()} {time.time_ns()}'

    def _read(self):
        try:
            return self.path.read_text(encoding='utf-8')
        except OSError:
            return None

    def __enter__(self):
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                handle = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except (FileExistsError, PermissionError):  # PermissionError: Windows, a lock being deleted
                self._break_if_stale()
                if time.monotonic() > deadline:
                    raise AwError(f'state lock {self.path} held longer than {self.timeout:.0f} s by: '
                                  + (self._read() or '?').strip())
                time.sleep(self.poll)
                continue
            with os.fdopen(handle, 'w', encoding='utf-8') as out:
                out.write(self.token + '\n')
            return self

    def _break_if_stale(self):
        try:
            age = time.time() - self.path.stat().st_mtime
        except OSError:
            return
        if age <= self.stale:
            return
        seen = self._read()
        aside = self.path.with_name(f'{self.path.name}.stale-{int(time.time())}-{os.getpid()}')
        if self._read() != seen:
            return
        try:
            os.replace(self.path, aside)
        except OSError:
            return
        log_trial(self.config, 'stale-lock', lock=str(self.path), age_s=round(age, 1), holder=(seen or '').strip(),
                  moved_to=str(aside))

    def __exit__(self, *exc):
        if (self._read() or '').strip() == self.token:
            try:
                self.path.unlink()
            except OSError:
                pass
        return False


# --------------------------------------------------------------------------
# Lease register (aw-state-1)

def empty_state():
    return {'schema': 'aw-state-1', 'updated': stamp(), 'next_seq': 1, 'leases': [], 'gate_spent': [], 'run_names': [],
            'queue': []}


def load_state(config):
    path = state_dir(config) / 'aw-state.json'
    if not path.is_file():
        return empty_state()
    state = json.loads(path.read_text(encoding='utf-8'))
    for key, value in empty_state().items():
        state.setdefault(key, value)
    return state


def save_state(config, state):
    state['updated'] = stamp()
    write_json(state_dir(config) / 'aw-state.json', state)


def refresh(state, now=None):
    """Marks active leases past their expiry as expired; returns the newly expired ones."""
    now = time.time() if now is None else now
    gone = []
    for lease in state['leases']:
        if lease['status'] == 'active' and lease['expires_epoch'] < now:
            lease['status'] = 'expired'
            gone.append(lease)
    return gone


def active(state, kind=None):
    return [lease for lease in state['leases'] if lease['status'] == 'active' and (kind is None or lease['kind'] == kind)]


def new_lease(config, state, kind, key, requester, purpose='', reason='', version='', commit=''):
    ttl = int(config.get('lease_ttl_s', {}).get(kind, DEFAULT_TTL[kind]))
    now = time.time()
    lease = {'id': f'{kind}-{state["next_seq"]}', 'kind': kind, 'key': key, 'requester': requester,
             'purpose': purpose, 'reason': reason or '', 'version': version or '', 'commit': commit or '',
             'created': stamp(), 'created_epoch': now, 'renewed': None, 'expires_epoch': now + ttl,
             'expires': stamp_epoch(now + ttl), 'status': 'active'}
    state['next_seq'] += 1
    state['leases'].append(lease)
    return lease


def gate_number_used(out_dir, number):
    """Outputs of gate NUMBER already exist in the gate folder (par-N-*, preflight-N, suite-N, engine-N, source-N)."""
    if not out_dir:
        return False
    folder = Path(out_dir)
    if glob.glob(str(folder / f'par-{number}-*')):
        return True
    return any((folder / f'{prefix}-{number}').exists() for prefix in GATE_USED)


def gate_range(config, name=None):
    gate = config.get('gate', {})
    ranges = gate.get('ranges') or {}
    name = name or gate.get('default_range')
    if not name or name not in ranges:
        raise AwError(f'gate range {name!r} is not in the config (known: {", ".join(sorted(ranges)) or "none"})')
    low, high = ranges[name]
    return name, int(low), int(high)


def lease_gate(config, requester, range_name=None, number=None, purpose='gate', reason='', version='', commit=''):
    name, low, high = gate_range(config, range_name)
    out_dir = config.get('gate', {}).get('out_dir')
    with Lock(config, requester):
        state = load_state(config)
        refresh(state)
        held = {lease['key'] for lease in active(state, 'gate')}
        candidates = [number] if number is not None else range(low, high + 1)
        for candidate in candidates:
            if not low <= candidate <= high:
                raise AwError(f'gate number {candidate} is outside range {name} {low}-{high}')
            why = ('spent' if candidate in state['gate_spent'] else 'leased' if str(candidate) in held
                   else 'outputs exist' if gate_number_used(out_dir, candidate) else None)
            if why is None:
                lease = new_lease(config, state, 'gate', str(candidate), requester, purpose, reason, version, commit)
                state['gate_spent'].append(candidate)
                save_state(config, state)
                break
            if number is not None:
                raise AwError(f'gate number {candidate} is not free ({why})')
        else:
            raise AwError(f'gate range {name} {low}-{high} is exhausted (every number spent, leased or used)')
    log_trial(config, 'lease', lease=lease)
    return lease


def lease_worktree(config, path, requester, purpose='', reason='', version='', commit=''):
    key = os.path.normcase(os.path.abspath(path)).replace('\\', '/')
    with Lock(config, requester):
        state = load_state(config)
        refresh(state)
        for lease in active(state, 'worktree'):
            if lease['key'] == key:
                if lease['requester'] == requester:
                    return lease
                raise AwError(f'worktree {key} is leased by {lease["requester"]} until {lease["expires"]} ({lease["id"]})')
        lease = new_lease(config, state, 'worktree', key, requester, purpose, reason, version, commit)
        save_state(config, state)
    log_trial(config, 'lease', lease=lease)
    return lease


def lease_run_name(config, repo, purpose, requester, reason='', today=None, version=None, commit=None, taken=(),
                   record=True):
    """A run name from REPO's VERSION and HEAD, or from VERSION/COMMIT when given (a build of another commit).
    RECORD False: the name a lease would get now, without spending it (a dry run or a refusal: the lease returned
    is marked 'preview' and kept out of the register)."""
    version = version or repo_version(repo)
    commit = commit or git_short(repo)
    with Lock(config, requester):
        state = load_state(config)
        refresh(state)
        taken = set(state['run_names']) | set(taken)  # TAKEN: names that exist elsewhere (runs on disk)
        attempt = 1
        while True:
            name = make_run_name(version, purpose, commit, reason, today, attempt)
            if name not in taken:
                break
            attempt += 1
        if not record:
            return {'id': 'preview', 'kind': 'run-name', 'key': name, 'requester': requester, 'status': 'preview'}
        state['run_names'].append(name)
        lease = new_lease(config, state, 'run-name', name, requester, purpose, reason, version, commit or 'nogit')
        save_state(config, state)
    log_trial(config, 'lease', lease=lease)
    return lease


def _change(config, lease_id, requester, how):
    with Lock(config, requester):
        state = load_state(config)
        refresh(state)
        for lease in state['leases']:
            if lease['id'] == lease_id:
                break
        else:
            raise AwError(f'no lease {lease_id}')
        if how == 'renew':
            if lease['status'] != 'active':
                raise AwError(f'lease {lease_id} is {lease["status"]}; lease again instead')
            ttl = int(config.get('lease_ttl_s', {}).get(lease['kind'], DEFAULT_TTL[lease['kind']]))
            lease['expires_epoch'] = time.time() + ttl
            lease['expires'] = stamp_epoch(lease['expires_epoch'])
            lease['renewed'] = stamp()
        else:
            lease['status'] = 'released'
            lease['released'] = stamp()
        save_state(config, state)
    log_trial(config, how, lease=lease, by=requester)
    return lease


def renew(config, lease_id, requester='aw'):
    return _change(config, lease_id, requester, 'renew')


def release(config, lease_id, requester='aw'):
    return _change(config, lease_id, requester, 'release')


# --------------------------------------------------------------------------
# Machine-wide core leases (docs/AW.md "Core leases"): no oversubscription

CORE_PRIORITIES = {'release': 3, 'dev': 2, 'optional': 1}   # release-critical > dev > optional/experimental


def core_settings(config):
    """(host threads, minimum cores per build, cores held by each running gate, enabled) from the build section."""
    build = config.get('build') or {}
    host = int(build.get('host_threads') or os.cpu_count() or build.get('cpus') or 24)
    return (host, int(build.get('min_cores') or 2), int(build.get('gate_cores') or 4),
            bool(build.get('core_leases', True)))


def memory_gib(text):
    """'44g' / '512m' / '2048' (MiB) / 44 -> GiB as a float."""
    if isinstance(text, (int, float)):
        return float(text)
    text = str(text).strip().lower()
    unit = text[-1] if text[-1:] in ('k', 'm', 'g') else 'm'
    number = float(text[:-1] if text[-1:] in ('k', 'm', 'g') else text)
    return {'k': number / (1024 * 1024), 'm': number / 1024, 'g': number}[unit]


def memory_settings(config):
    """(container memory of the host in GiB, host reserve GiB, GiB held by each running gate): the memory leases
    never exceed host - reserve - gates."""
    build = config.get('build') or {}
    return (float(build.get('host_memory_gib') or 47), float(build.get('memory_reserve_gib') or 4),
            float(build.get('gate_memory_gib') or 6))


def core_plan(host, holders, fixed=0, minimum=2):
    """Cores for each holder ({id, priority, want}): every holder gets MINIMUM, then one core at a time goes to the
    holder with the fewest cores per priority weight (ties: higher priority, then earlier holder) until the
    host's threads (less FIXED, e.g. running gates) are used up or every holder has what it wants. The sum never
    exceeds host - fixed. None when even MINIMUM each does not fit."""
    room = host - fixed
    if not holders:
        return {}
    if minimum * len(holders) > room:
        return None
    grant = {h['id']: min(minimum, h['want']) for h in holders}
    left = room - sum(grant.values())
    order = {h['id']: index for index, h in enumerate(holders)}
    weight = {h['id']: CORE_PRIORITIES.get(h.get('priority'), 2) for h in holders}
    while left > 0:
        open_ = [h for h in holders if grant[h['id']] < h['want']]
        if not open_:
            break
        pick = min(open_, key=lambda h: (grant[h['id']] / weight[h['id']], -weight[h['id']], order[h['id']]))
        grant[pick['id']] += 1
        left -= 1
    return grant


def core_holders(state):
    """The active core leases as plan holders, oldest first."""
    return [{'id': lease['id'], 'priority': lease.get('priority', 'dev'), 'want': int(lease.get('want') or 1),
             'cores': int(lease.get('cores') or 0), 'container': lease.get('container'), 'key': lease['key'],
             'memory_gib': float(lease.get('memory_gib') or 0)}
            for lease in active(state, 'cores')]


# A queued request asks again every build.queue_poll_s (30 s) and marks its ticket seen each time; a ticket not seen
# for this long belongs to a request that is gone (killed while queued) and is dropped, or it would head the strict
# first-come queue forever and hold every later build back (AW-QUEUE-DEAD-TICKET-54). A ticket of an older aw without
# the mark counts from when it was queued, and a live one of those simply queues again at its next poll.
QUEUE_STALE_S = 1800


def prune_queue(state, now=None, keep=None):
    """Drop queued tickets not seen for QUEUE_STALE_S (KEEP: a ticket never dropped); returns the dropped ones."""
    now = time.time() if now is None else now
    queue = state.setdefault('queue', [])
    gone = [item for item in queue if item['ticket'] != keep
            and now - float(item.get('seen_epoch', item.get('since_epoch', now))) > QUEUE_STALE_S]
    if gone:
        state['queue'] = [item for item in queue if item not in gone]
    return gone


def _queue_turn(state, ticket, priority, now=None):
    """True when no request queued before this one has a higher or equal priority (release-critical first, then
    first come first served); the ticket is queued (once) either way and marked seen; tickets of requests that stopped
    asking are dropped first (prune_queue)."""
    now = time.time() if now is None else now
    prune_queue(state, now, keep=ticket)
    queue = state['queue']
    if not any(item['ticket'] == ticket for item in queue):
        queue.append({'ticket': ticket, 'priority': priority, 'since': stamp(), 'since_epoch': now})
    for item in queue:
        if item['ticket'] == ticket:
            item['seen_epoch'] = now
    weight = CORE_PRIORITIES.get(priority, 2)
    for item in queue:
        if item['ticket'] == ticket:
            return True
        if CORE_PRIORITIES.get(item['priority'], 2) >= weight:
            return False
    return True


def dequeue(config, ticket, requester='aw'):
    with Lock(config, requester):
        state = load_state(config)
        state['queue'] = [item for item in state.get('queue', []) if item['ticket'] != ticket]
        save_state(config, state)


def touch_ticket(config, ticket, requester='aw'):
    """Mark a queued ticket seen while its request waits for a busy machine (it does not ask for a lease then)."""
    with Lock(config, requester):
        state = load_state(config)
        hit = False
        for item in state.get('queue', []):
            if item['ticket'] == ticket:
                item['seen_epoch'] = time.time()
                hit = True
        if hit:
            save_state(config, state)


def _rebalance(state, holders, plan):
    changes = []
    for holder in holders:
        if plan.get(holder['id'], holder['cores']) != holder['cores']:
            changes.append((holder['container'], holder['cores'], plan[holder['id']]))
            for row in state['leases']:
                if row['id'] == holder['id']:
                    row['cores'] = plan[holder['id']]
    return changes


# A core lease whose build container is gone (the build was killed, its aw request with it) holds its cores and
# memory until its TTL: two killed builds of 2026-10-27 held 32 GB and queued the v0.0.54-dev2 build
# (AW-LEASE-DEAD-CONTAINER-54). Such a lease ends like a worktree lease whose worktree is gone, once it is older
# than the grace a build needs to start its container; a container this host cannot ask about is never judged.
DEAD_CONTAINER_GRACE_S = 600
# (name) -> True (the container exists), False (no such container) or None (cannot tell); None: docker on this host.
# A launcher that runs aw in a container without docker sets one that asks the host.
CONTAINER_PROBE = None


def docker_container_exists(name):
    """True / False / None (docker not reachable) for a container NAME, by `docker container inspect`."""
    try:
        done = subprocess.run(['docker', 'container', 'inspect', '--format', '{{.State.Status}}', name],
                              capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode == 0:
        return True
    return False if 'no such container' in (done.stderr or '').lower() else None


def expire_dead_cores(config, state, now=None, probe=None):
    """Ends the core leases whose build container is gone (each expiry logged); returns the ended leases."""
    now = time.time() if now is None else now
    probe = probe or CONTAINER_PROBE or docker_container_exists
    ttl = int(config.get('lease_ttl_s', {}).get('cores', DEFAULT_TTL['cores']))
    ended = []
    for lease in active(state, 'cores'):
        name = lease.get('container')
        start = float(lease.get('created_epoch') or (lease['expires_epoch'] - ttl))
        if not name or now - start < DEAD_CONTAINER_GRACE_S:
            continue
        if probe(name) is False:
            lease.update(status='expired', expired=stamp(), expired_because=f'the build container {name} is gone')
            ended.append(lease)
    for lease in ended:
        log_trial(config, 'expire', lease=lease, why=lease['expired_because'])
    return ended


def lease_cores(config, run_name, requester, priority, want, container, purpose='', reason='', memory_gib=0.0,
                ticket=None):
    """Lease cores AND memory for one build under the machine-wide plan (docs/AW.md "Core leases").
    Returns (lease, changes): the lease ('cores' = the build's --jobs and --cpus, 'memory_gib' = its --memory) and
    [(container, old, new)] for running builds whose core share moved (the caller applies them with docker
    update). With a TICKET a request that does not fit now, or that a queued request of higher or equal priority
    precedes, stays queued and (None, why) comes back: call again later. Without a ticket a misfit raises AwError."""
    host, minimum, gate_cores, _ = core_settings(config)
    host_mem, reserve, gate_mem = memory_settings(config)
    with Lock(config, requester):
        state = load_state(config)
        refresh(state)
        expire_dead_cores(config, state)
        holders = core_holders(state)
        gates = len(active(state, 'gate'))
        new = {'id': '(new)', 'priority': priority, 'want': want}
        plan = core_plan(host, holders + [new], gate_cores * gates, minimum)
        mem_free = host_mem - reserve - gate_mem * gates - sum(h['memory_gib'] for h in holders)
        why = None
        if plan is None:
            why = (f'no cores free: {host} threads, {len(holders)} builds and {gate_cores * gates} gate cores leased '
                   f'(minimum {minimum} per build)')
        elif memory_gib > mem_free + 1e-9:
            why = (f'no memory free: {memory_gib:g} GiB wanted, {max(0.0, mem_free):g} GiB of {host_mem:g} free '
                   f'({reserve:g} reserved for the host; {len(holders)} builds and {gates} gates leased)')
        if ticket is not None and not _queue_turn(state, ticket, priority) and why is None:
            why = 'a queued request of higher or equal priority goes first'
        if why is not None:
            save_state(config, state)
            if ticket is None:
                raise AwError(why + '; wait for a build to end')
            return None, why
        state['queue'] = [item for item in state.get('queue', []) if item['ticket'] != ticket]
        lease = new_lease(config, state, 'cores', run_name, requester, purpose, reason)
        lease.update(priority=priority, want=want, cores=plan['(new)'], container=container, host_threads=host,
                     memory_gib=memory_gib, host_memory_gib=host_mem)
        changes = _rebalance(state, holders, plan)
        save_state(config, state)
    log_trial(config, 'lease', lease=lease, by=requester, rebalanced=changes)
    return lease, changes


def release_cores(config, lease_id, requester='aw'):
    """Release a core lease (and its memory) and give its cores to the builds still running:
    [(container, old, new)]."""
    host, minimum, gate_cores, _ = core_settings(config)
    with Lock(config, requester):
        state = load_state(config)
        refresh(state)
        for lease in state['leases']:
            if lease['id'] == lease_id and lease['status'] == 'active':
                lease['status'] = 'released'
                lease['released'] = stamp()
        holders = core_holders(state)
        plan = core_plan(host, holders, gate_cores * len(active(state, 'gate')), minimum) or {}
        changes = _rebalance(state, holders, plan)
        save_state(config, state)
    log_trial(config, 'release', lease_id=lease_id, by=requester, rebalanced=changes)
    return changes


def rebalance_running(config, requester='aw'):
    """Share the cores again among the running builds after a gate started or ended: [(container, old, new)]
    (AW-LEASE-NO-GROW-36: a build grows back when gates end, not only when another build ends)."""
    host, minimum, gate_cores, enabled = core_settings(config)
    if not enabled:
        return []
    with Lock(config, requester):
        state = load_state(config)
        refresh(state)
        holders = core_holders(state)
        plan = core_plan(host, holders, gate_cores * len(active(state, 'gate')), minimum) or {}
        changes = _rebalance(state, holders, plan)
        save_state(config, state)
    if changes:
        log_trial(config, 'rebalance', by=requester, rebalanced=changes)
    return changes


def resize_builds(config, changes):
    """docker update --cpus for each changed build container; returns note lines."""
    docker = (config.get('build') or {}).get('docker', 'docker')
    lines = []
    for container, old, new in changes:
        if not container:
            continue
        try:
            done = subprocess.run([docker, 'update', '--cpus', str(new), container], capture_output=True, text=True,
                                  timeout=60)
            ok = done.returncode == 0
        except (OSError, subprocess.SubprocessError):
            ok = False
        lines.append(f'core lease rebalance: {container} {old} -> {new} cores' + ('' if ok else ' (docker update failed)'))
    return lines


# --------------------------------------------------------------------------
# Leases of finished jobs end (docs/AW.md "Finished jobs")

DEFAULT_IDLE_S = 2 * 3600


def finished_reason(config, lease, now=None):
    """Why an active worktree lease belongs to a finished job, or None: the worktree is gone; or its HEAD is merged
    into the integration ref, the worktree is clean, and neither the lease nor a commit moved for idle_s."""
    now = time.time() if now is None else now
    repo = Path(lease['key'])
    if not repo.is_dir():
        # a removed worktree (its folder's parent still there); a path this host cannot see is never judged
        return 'the worktree is gone' if repo.parent.is_dir() else None
    ref = config.get('integration_ref')
    head = git(repo, 'rev-parse', 'HEAD')
    if not ref or not head or is_ancestor(repo, head, ref) is not True:
        return None
    if git(repo, 'status', '--porcelain'):
        return None
    ttl = int(config.get('lease_ttl_s', {}).get('worktree', DEFAULT_TTL['worktree']))
    touched = lease['expires_epoch'] - ttl
    committed = git(repo, 'log', '-1', '--format=%ct', 'HEAD')
    last = max(touched, float(committed) if committed and committed.isdigit() else 0.0)
    idle = float(config.get('lease_idle_s', {}).get('worktree', DEFAULT_IDLE_S))
    if now - last < idle:
        return None
    return f'finished: HEAD {head[:7]} is merged into {ref}, the worktree is clean and idle for {(now - last) / 3600:.1f} h'


def expire_finished(config, state, now=None):
    """Ends the worktree leases of finished jobs (each expiry logged); returns the ended leases."""
    ended = []
    for lease in active(state, 'worktree'):
        why = finished_reason(config, lease, now)
        if why:
            lease['status'] = 'expired'
            lease['expired'] = stamp()
            lease['expired_because'] = why
            ended.append(lease)
    for lease in ended:
        log_trial(config, 'expire', lease=lease, why=lease['expired_because'])
    return ended


def job_done(config, requester):
    """The job REQUESTER reports done: every active lease it holds ends (core leases give their cores back)."""
    ended, changes = [], []
    with Lock(config, requester):
        state = load_state(config)
        refresh(state)
        held = [lease for lease in active(state) if lease['requester'] == requester]
    for lease in held:
        if lease['kind'] == 'cores':
            changes += release_cores(config, lease['id'], requester)
        else:
            release(config, lease['id'], requester)
        ended.append(lease['id'])
    log_trial(config, 'done', by=requester, ended=ended)
    return ended, changes


def list_leases(config, everything=False):
    with Lock(config, 'aw-list'):
        state = load_state(config)
        if bool(refresh(state)) | bool(expire_finished(config, state)) | bool(expire_dead_cores(config, state)):
            save_state(config, state)
    return state['leases'] if everything else active(state)


# --------------------------------------------------------------------------
# Gate result: read par-N-*.out (and the suite receipt), never the script's exit code

def _read(path):
    try:
        return Path(path).read_text(encoding='utf-8', errors='replace').splitlines()
    except OSError:
        return None


def _exit_line(lines, name):
    """(exit code, index) of the first 'NAME-exit=K' line."""
    for index, line in enumerate(lines or []):
        match = re.match(re.escape(name) + r'-exit=(-?[0-9]+)', line.strip())
        if match:
            return int(match.group(1)), index
    return None, None


def _suite_receipt(out_dir, number, lines):
    """The suite receipt: suite-N/receipt.json, else the JSON line in par-N-suite.out (it may be cut short)."""
    path = Path(out_dir) / f'suite-{number}' / 'receipt.json'
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if isinstance(data, dict):
            return data, str(path)
    except (OSError, ValueError):
        pass
    for line in reversed(lines or []):
        if line.startswith('{"started"'):
            try:
                return json.loads(line), 'par-suite line'
            except ValueError:
                data = {}
                for key in ('tests_run', 'failures', 'errors', 'skipped', 'unexpected_skips'):
                    match = re.search(f'"{key}": ([0-9]+)', line)
                    if match:
                        data[key] = int(match.group(1))
                match = re.search(r'"successful": (true|false)', line)
                if match:
                    data['successful'] = match.group(1) == 'true'
                match = re.search(r'"seconds": ([0-9.]+)', line)
                if match:
                    data['seconds'] = float(match.group(1))
                return data, 'par-suite line (cut short, fields read one by one)'
    return None, None


def parse_gate(out_dir, number, expect_head=None):
    """Everything the par-N-*.out files say, judged. Returns a dict with status passed|failed|refused."""
    out_dir = Path(out_dir)
    files = {name: out_dir / f'par-{number}-{name}.out' for name in GATE_FILES}
    text = {name: _read(path) for name, path in files.items()}
    present = [name for name, lines in text.items() if lines is not None]
    result = {'gate': number, 'head': None, 'repo': None, 'dirty': None, 'steps': {}, 'numbers': {},
              'failures': [], 'notes': [], 'timings': {}, 'logs': [str(files[name]) for name in present],
              'artifacts': []}
    if not present:
        result['status'] = 'refused'
        result['failed_steps'] = list(GATE_STEPS)
        result['notes'].append(f'no par-{number}-*.out files: the gate script refused or never started')
        for step in GATE_STEPS:
            result['steps'][step] = {'exit': None, 'ok': False, 'detail': 'not run'}
        return result
    for line in text['repo'] or []:
        match = re.match(r'gate ([0-9]+) repo (.+?) head (\S+) dirty ([0-9]+)', line)
        if match:
            result['repo'], result['head'], result['dirty'] = match.group(2), match.group(3), int(match.group(4))
        match = re.match(r'gate-times: queued_at=([0-9]+) started_at=([0-9]+)', line)
        if match:
            result['timings']['queued_at'] = int(match.group(1))
            result['timings']['started_at'] = int(match.group(2))
        match = re.match(r'gate-queue: .*waited_s=([0-9]+)', line)
        if match:
            result['timings']['queue_wait_s'] = int(match.group(1))
        if line.startswith('fail-fast:'):
            result['notes'].append(line.strip())

    def step(name, lines, extra_ok=True, detail=''):
        code, index = _exit_line(lines, name)
        if lines is None:
            result['steps'][name] = {'exit': None, 'ok': False, 'detail': 'missing output file'}
        elif code is None:
            result['steps'][name] = {'exit': None, 'ok': False, 'detail': 'no exit line'}
        else:
            if not detail and index is not None and index + 1 < len(lines):
                detail = lines[index + 1].strip()[:200]
            result['steps'][name] = {'exit': code, 'ok': code == 0 and extra_ok, 'detail': detail}
        return code, index

    step('preflight', text['preflight'])
    # suite: exit line AND the receipt
    receipt, origin = _suite_receipt(out_dir, number, text['suite'])
    numbers = result['numbers']
    for key in ('tests_run', 'failures', 'errors', 'skipped', 'unexpected_skips'):
        numbers[key] = receipt.get(key) if receipt else None
    suite_ok, why = True, ''
    if receipt is None:
        suite_ok, why = False, 'no suite receipt'
    else:
        if receipt.get('successful') is not True:
            suite_ok, why = False, 'suite receipt: successful is not true'
        elif not numbers['tests_run']:
            suite_ok, why = False, 'suite receipt: no tests run'
        elif numbers['failures'] or numbers['errors']:
            suite_ok, why = False, 'suite receipt: failures or errors'
        if receipt.get('seconds') is not None:
            result['timings']['suite_s'] = receipt['seconds']
        if origin and origin.endswith('receipt.json'):
            result['artifacts'].append(origin)
    if receipt is not None:
        why = why or (f"{numbers['tests_run']} tests, {numbers['failures']} failures, {numbers['errors']} errors"
                      f" ({origin})")
    step('suite', text['suite'], suite_ok, why)
    result['failures'] = [line.strip() for line in text['suite'] or [] if re.match(r'(FAIL|FAIL-MODULE) ', line)][:200]
    step('host-parity-linux', text['hostparity'])
    step('host-parity-windows', text['hostparity'])
    code, index = _exit_line(text['engine'], 'engine')
    warnings = None
    if index is not None and index + 1 < len(text['engine']) and text['engine'][index + 1].strip().isdigit():
        warnings = int(text['engine'][index + 1].strip())
    numbers['engine_warnings'] = warnings
    if warnings is None and code is not None:
        result['notes'].append('engine: warning count not found')
    step('engine', text['engine'], warnings == 0, f'{warnings} compiler warnings' if warnings is not None else '')
    # engine boot + map-load smoke in FS-UAE (CHIM-DEV3-MAPLOAD-CRASH-36): the engine just built, in a finished image
    step('smoke', text['smoke'])
    if expect_head and result['head'] and not (expect_head.startswith(result['head'])
                                               or result['head'].startswith(expect_head)):
        result['notes'].append(f'gated head {result["head"]} is not the requested commit {expect_head}')
        result['steps']['preflight']['ok'] = False
    result['failed_steps'] = [name for name in GATE_STEPS if not result['steps'][name]['ok']]
    result['status'] = 'failed' if result['failed_steps'] else 'passed'
    return result


# --------------------------------------------------------------------------
# Entry check

def stale_builder_text(repo, rev, head, origin, ref):
    """The refusal of a request whose commit lacks the published integration head (the builder head broadcast)."""
    merge = f'git -C {repo} merge {ref}' if ref else f'git -C {repo} merge {head}'
    rev = rev[:7] if re.fullmatch(r'[0-9a-f]{40}', rev) else rev
    return (f'STALE BUILDER: {rev} does not contain the published integration head {head} ({origin}); '
            f'merge it first ({merge}), gate the merge, then ask again')


def entry_findings(config, repo, accept_mismatch=None, rev='HEAD', version=None):
    """(refusals, warnings, facts) of the cheap entry checks against REV in REPO (default its checkout):
    working version and integration head. VERSION: the version of REV when it is not the checkout."""
    refusals, warnings, facts = [], [], {}
    version = version or repo_version(repo)
    facts['version'] = version
    record_path = config.get('working_version_file')
    record = {}
    if record_path and Path(record_path).is_file():
        record = json.loads(Path(record_path).read_text(encoding='utf-8'))
        wanted = 'v' + str(record.get('working_version', '')).lstrip('v')
        facts['working_version'] = wanted
        if wanted != version:
            text = f'source VERSION {version} != working version {wanted}'
            (warnings if accept_mismatch else refusals).append(
                text + (f' (accepted: {accept_mismatch})' if accept_mismatch else ''))
    else:
        warnings.append('working version: no working_version_file in the config (or it is missing)')
    heads = []
    ref = config.get('integration_ref')
    if ref:
        resolved = git_short(repo, ref)
        if resolved:
            heads.append((resolved, ref))
        else:
            warnings.append(f'integration ref {ref} does not resolve in {repo}')
    for key in ('integration_head', 'head'):
        if record.get(key):
            heads.append((str(record[key]), f'working-version record "{key}"'))
            break
    facts['integration_head'] = heads[0][0] if heads else None
    seen = []
    for commit, origin in heads:
        if any(commit.startswith(other) or other.startswith(commit) for other in seen):
            continue  # the ref and the record name the same head: one check, one message
        seen.append(commit)
        contained = is_ancestor(repo, commit, rev)
        if contained is False:
            refusals.append(stale_builder_text(repo, rev, commit, origin, ref))
        elif contained is None:
            warnings.append(f'cannot check the integration head {commit} ({origin}) in {repo}')
    return refusals, warnings, facts


def cmd_enter(args, config):
    sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
    import entry_check
    refusals, warnings, facts = entry_findings(config, ROOT, args.accept_version_mismatch)
    record = entry_check.check(root=ROOT, working_version=config.get('working_version_file'),
                               accept_mismatch=args.accept_version_mismatch or None)
    for text in record['refusals']:
        if not text.startswith('working version:'):
            refusals.append(text)
    bad = entry_check.foreign_path_entries(os.environ.get('PYTHONPATH', '').split(os.pathsep), ROOT)
    if bad:
        refusals.append('PYTHONPATH points into another builder tree: ' + ', '.join(bad)
                        + f'; set it to {ROOT}/src{os.pathsep}{ROOT}/tools or unset it')
    ok = not refusals
    print('=' * 72)
    print(f'aw enter: {"OK" if ok else "REFUSED"} (source {ROOT})')
    print(f'  version {facts["version"]}, working version {facts.get("working_version", "unknown")}')
    print(f'  integration head {facts.get("integration_head") or "unknown"}')
    print('  imports: ' + ('every builder module from this tree' if record['source_imports']['ok']
                           else f'{len(record["source_imports"]["foreign"])} module(s) from elsewhere'))
    for text in warnings:
        print('  WARNING: ' + text)
    for text in refusals:
        print('  REFUSED: ' + text)
    print('=' * 72)
    log_trial(config, 'enter', source=str(ROOT), ok=ok, refusals=refusals, warnings=warnings, **facts)
    return 0 if ok else 1


# --------------------------------------------------------------------------
# aw gate

def requester_of(args):
    return args.requester or os.environ.get(REQUESTER_ENV) or 'anonymous'


def gate_command(config, number):
    template = config.get('gate', {}).get('command')
    if not template:
        raise AwError('no gate.command in the config')
    return [str(part).replace('{number}', str(number)) for part in template]


def run_logged(command, env, log_path, echo=True):
    """Runs COMMAND, copies its output to LOG_PATH (and stdout); returns the exit code."""
    with open(log_path, 'w', encoding='utf-8', newline='\n') as log:
        process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, encoding='utf-8', errors='replace')
        for line in process.stdout:
            log.write(line)
            if echo:
                sys.stdout.write(line)
                sys.stdout.flush()
        return process.wait()


def unlisted_test_refusals(repo):
    """The gate stages only the files of tools/release-files.json: a test source of the checkout missing from it
    would never run (OPS-GATE-UNLISTED-TESTS-36). Refused before any gate number is spent, naming the files."""
    if not (Path(repo) / 'tools' / 'release-files.json').is_file():
        return []
    tools = str(Path(__file__).resolve().parent)
    if tools not in sys.path:
        sys.path.append(tools)
    import release
    try:
        missing = release.unlisted_test_files(repo)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        return [f'cannot check the test files against tools/release-files.json: {exc}']
    if not missing:
        return []
    return [f'{len(missing)} test file(s) not in tools/release-files.json, so the gate would never run them '
            f'(add them to the list): {", ".join(missing)}']


def executable_mode_refusals(repo):
    """A file committed executable must be in tools/release.py EXECUTABLES and the other way round, or the source
    ZIP (0755 exactly for that list) no longer matches the commit (BUILD-EXECUTABLES-LIST-UNGATED-36: found only at
    kit time). The gate source has no git, so this is checked here, on the checkout."""
    if not (Path(repo) / 'tools' / 'release.py').is_file():
        return []
    tools = str(Path(__file__).resolve().parent)
    if tools not in sys.path:
        sys.path.append(tools)
    import release
    if not hasattr(release, 'executable_mismatches'):
        return []
    try:
        found = release.executable_mismatches(repo)
    except (OSError, ValueError, SyntaxError) as exc:
        return [f'cannot check executable modes against tools/release.py EXECUTABLES: {exc}']
    if found is None:
        return []
    unlisted, plain = found
    refusals = []
    if unlisted:
        refusals.append('committed executable (100755) but not in tools/release.py EXECUTABLES (add it, or commit it '
                        'without the bit: git update-index --chmod=-x): ' + ', '.join(unlisted))
    if plain:
        refusals.append('in tools/release.py EXECUTABLES but not committed executable: ' + ', '.join(plain))
    return refusals


def cmd_gate(args, config):
    repo = Path(args.repo).resolve()
    requester = requester_of(args)
    if not (repo / 'VERSION').is_file():
        raise AwError(f'{repo} is not a source checkout (no VERSION)')
    version = repo_version(repo)
    head = git_short(repo)
    if head is None:
        raise AwError(f'{repo}: no git HEAD')
    notes = []
    refusals = []
    if args.commit:
        wanted = git_short(repo, args.commit)
        if wanted != head:
            refusals.append(f'--commit {args.commit} is not the checked-out HEAD {head}: the gate checks the checkout')
    dirty = git(repo, 'status', '--porcelain')
    if dirty:
        count = len(dirty.splitlines())
        if args.allow_dirty:
            notes.append(f'{count} uncommitted/untracked paths (allowed: the result is NOT a clean {head} gate)')
        else:
            refusals.append(f'{count} uncommitted/untracked paths: commit first (or --allow-dirty)')
    refusals += unlisted_test_refusals(repo)
    refusals += executable_mode_refusals(repo)
    entry_refusals, entry_warnings, facts = entry_findings(config, repo, args.accept_version_mismatch)
    import aw_broadcast
    joined = aw_broadcast.join(config, repo, requester)
    if joined:
        notes.append(joined)
    entry_refusals, deferred = aw_broadcast.relax_stale(config, requester, entry_refusals)
    refusals += entry_refusals
    notes += entry_warnings + deferred
    started = stamp()
    t0 = time.time()
    gate_lease = None
    if not refusals:
        gate_lease = lease_gate(config, requester, args.range, args.number, 'gate', args.reason, version, head)
        for line in resize_builds(config, rebalance_running(config, requester)):   # running builds make room
            print('aw gate: ' + line, flush=True)
    purpose = f'gate-{gate_lease["key"]}' if gate_lease else 'gate'
    try:
        run_lease = lease_run_name(config, repo, purpose, requester, args.reason)
    except AwError:
        if gate_lease:
            release(config, gate_lease['id'], requester)
        raise
    run_name = run_lease['key']
    request = checked({'schema': 'aw-request-1', 'id': run_name, 'kind': 'gate', 'repo': str(repo), 'commit': head,
                       'purpose': purpose, 'version': version, 'reason': args.reason or '', 'requester': requester,
                       'time': started, 'options': {'range': args.range, 'number': args.number}}, 'aw-request-1')
    log_trial(config, 'request', request=request)
    results = state_dir(config) / 'results'
    logs = state_dir(config) / 'logs'
    results.mkdir(exist_ok=True)
    logs.mkdir(exist_ok=True)

    def finish(parsed, script_exit, leases):
        document = {'schema': 'aw-result-1', 'request_id': run_name, 'kind': 'gate', 'status': parsed['status'],
                    'version': version, 'commit': head, 'run_name': run_name, 'time': stamp(), 'started': started,
                    'finished': stamp(), 'seconds': round(time.time() - t0, 1), 'numbers': parsed['numbers'],
                    'steps': parsed['steps'], 'failed_steps': parsed['failed_steps'], 'failures': parsed['failures'],
                    'artifacts': parsed['artifacts'], 'logs': parsed['logs'], 'timings': parsed['timings'],
                    'reuse': {'applicable': False}, 'leases': leases, 'gate': parsed.get('gate'),
                    'head': parsed.get('head'), 'script_exit': script_exit, 'notes': notes + parsed['notes']}
        path = results / f'{run_name}.json'
        document['artifacts'] = document['artifacts'] + [str(path)]
        write_json(path, checked(document, 'aw-result-1'))
        log_trial(config, 'result', result={key: document[key] for key in (
            'request_id', 'kind', 'status', 'version', 'commit', 'gate', 'numbers', 'failed_steps', 'seconds',
            'script_exit')}, path=str(path), sha256=file_sha256(path))
        perf_db_post(config, document, path)
        return document, path

    if refusals:
        release(config, run_lease['id'], requester)
        parsed = {'status': 'refused', 'numbers': {}, 'steps': {s: {'exit': None, 'ok': False, 'detail': 'not run'}
                                                                  for s in GATE_STEPS},
                  'failed_steps': list(GATE_STEPS), 'failures': [], 'artifacts': [], 'logs': [], 'timings': {},
                  'notes': refusals, 'gate': None, 'head': head}
        document, path = finish(parsed, None, [run_lease['id']])
        for text in refusals:
            print('aw gate: REFUSED: ' + text, file=sys.stderr)
        print(f'aw gate: result {path}')
        return EXIT['refused']
    number = int(gate_lease['key'])
    leases = [run_lease['id'], gate_lease['id']]
    print(f'aw gate: {run_name}: gate {number} ({gate_lease["id"]}) on {repo} head {head}', flush=True)
    env = dict(os.environ)
    env.update({str(k): str(v) for k, v in (config.get('gate', {}).get('env') or {}).items()})
    env['REPO'] = str(repo).replace('\\', '/')
    log_path = logs / f'{run_name}.console.log'
    script_exit = None
    try:
        script_exit = run_logged(gate_command(config, number), env, log_path, echo=not args.quiet)
    finally:
        out_dir = config.get('gate', {}).get('out_dir')
        parsed = parse_gate(out_dir, number, head) if out_dir else {
            'status': 'failed', 'numbers': {}, 'steps': {s: {'exit': None, 'ok': False, 'detail': 'no gate.out_dir'}
                                                        for s in GATE_STEPS}, 'failed_steps': list(GATE_STEPS),
            'failures': [], 'artifacts': [], 'logs': [], 'timings': {}, 'notes': ['no gate.out_dir in the config'],
            'gate': number, 'head': None}
        parsed['logs'] = parsed['logs'] + [str(log_path)]
        if script_exit not in (None, 0) and parsed['status'] == 'passed':
            parsed['status'] = 'failed'
            parsed['notes'].append(f'the gate script exited {script_exit} although every step line says 0')
        if script_exit == 0 and parsed['status'] != 'passed':
            parsed['notes'].append('the gate script exited 0 but steps failed: judged failed from the step lines')
        document, path = finish(parsed, script_exit, leases)
        for lease_id in leases:
            release(config, lease_id, requester)
        for line in resize_builds(config, rebalance_running(config, requester)):   # running builds grow back
            print('aw gate: ' + line, flush=True)
    n = document['numbers']
    print(f'aw gate {number}: {document["status"].upper()}: suite {n.get("tests_run")} tests, '
          f'{n.get("failures")} failures, {n.get("errors")} errors, engine warnings {n.get("engine_warnings")}'
          + (f'; failed steps: {", ".join(document["failed_steps"])}' if document['failed_steps'] else ''))
    print(f'aw gate: result {path}')
    return EXIT[document['status']]


# --------------------------------------------------------------------------
# aw status / aw lease

def recent_results(config, count=10):
    path = trial_log_path(config)
    rows = []
    try:
        with open(path, encoding='utf-8') as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if row.get('event') == 'result':
                    rows.append(row)
    except OSError:
        pass
    return rows[-count:]


def stair_walk_text(block):
    """The stair-walk records of a build result in one phrase (BUILD-CHIM-STAIR-WALK-UNCACHED-36)."""
    if not block:
        return ''
    return ('; stair walks %s reused, %s walked, %s records checked'
            % (block.get('reused', '?'), block.get('walked', '?'), block.get('marked', '?')))


def over_budget_text(rows):
    """The CHIM frames over their memory budget in one phrase, worst first, with how much each is over."""
    if not rows:
        return ''
    return '; %d frame(s) over the CHIM memory budget: %s' % (len(rows), ', '.join(
        '%s over by %d bytes (%.0f KiB)' % (r.get('frame'), r.get('over', 0), r.get('over', 0) / 1024) for r in rows))


def perf_guard_text(block):
    """The perf guard's verdict of a build result in one phrase (docs/BUILD_PROFILE.md "Perf guard")."""
    if not block:
        return ''
    text = '; perf guard %s' % str(block.get('verdict', '?')).upper()
    if block.get('failed'):
        text += ' (%s failing)' % block['failed']
    if block.get('waived'):
        text += ', %s waived (%s)' % (block['waived'], ', '.join(block.get('waivers') or []))
    return text


def cmd_status(args, config):
    repo = Path(args.repo).resolve() if args.repo else ROOT
    record = {}
    if config.get('working_version_file') and Path(config['working_version_file']).is_file():
        record = json.loads(Path(config['working_version_file']).read_text(encoding='utf-8'))
    ref = config.get('integration_ref')
    import aw_service
    published = aw_service.published_integration(config)
    status = {'time': stamp(), 'working_version': record.get('working_version'),
              'working_version_updated': record.get('updated'),
              'integration_ref': ref, 'integration_head': git_short(repo, ref) if ref else None,
              'published': published,
              'leases': list_leases(config), 'recent_results': recent_results(config, args.count)}
    host, _, gate_cores, enabled = core_settings(config)
    builds = [lease for lease in status['leases'] if lease['kind'] == 'cores']
    gates = [lease for lease in status['leases'] if lease['kind'] == 'gate']
    leased = sum(int(lease.get('cores') or 0) for lease in builds)
    host_mem, reserve, gate_mem = memory_settings(config)
    memory = sum(float(lease.get('memory_gib') or 0) for lease in builds)
    with Lock(config, 'aw-status'):
        queue = load_state(config).get('queue', [])
    status['core_leases'] = {'host_threads': host, 'enabled': enabled, 'builds': len(builds), 'leased': leased,
                             'gates': len(gates), 'gate_cores': gate_cores * len(gates),
                             'free': host - leased - gate_cores * len(gates),
                             'host_memory_gib': host_mem, 'memory_reserve_gib': reserve, 'memory_leased_gib': memory,
                             'memory_free_gib': round(host_mem - reserve - memory - gate_mem * len(gates), 1),
                             'queue': queue}
    import aw_broadcast
    status['broadcast'] = aw_broadcast.summary(config)
    if published and status['integration_head'] and not (
            published['head'].startswith(status['integration_head'])
            or status['integration_head'].startswith(published['head'])):
        status['warning'] = (f'the published head {published["head"]} is not {ref} = {status["integration_head"]}'
                             ' (the publisher moves both together)')
    if args.json:
        print(json.dumps(status, indent=2, sort_keys=True))
        return 0
    print(f'aw status {status["time"]}')
    print(f'  working version: {status["working_version"]} (record updated {status["working_version_updated"]})')
    print(f'  integration head: {status["integration_head"]} ({ref})')
    if published:
        print(f'  published builder head: {published["head"]}  {published["note"]}')
        for line in published['contains']:
            print(f'    {line}')
        print('  every build and gate request must contain it; merge with: git merge ' + (ref or published['head']))
    if status.get('warning'):
        print('  WARNING: ' + status['warning'])
    aw_broadcast.print_summary(status['broadcast'])
    print(f'  active leases: {len(status["leases"])}')
    for lease in status['leases']:
        cores = (f'  {lease.get("cores")} cores, {lease.get("memory_gib", 0):g} GiB ({lease.get("priority")}, '
                 f'wanted {lease.get("want")})'
                 if lease['kind'] == 'cores' else '')
        print(f'    {lease["id"]:<14} {lease["kind"]:<9} {lease["key"]}  {lease["requester"]}  until {lease["expires"]}'
              + cores)
    core = status['core_leases']
    print(f'  core leases: {core["leased"]} of {core["host_threads"]} threads to {core["builds"]} build(s), '
          f'{core["gate_cores"]} held by {core["gates"]} gate(s), {core["free"]} free'
          + ('' if core['enabled'] else ' (core leases switched off in the config)'))
    print(f'  memory leases: {core["memory_leased_gib"]:g} of {core["host_memory_gib"]:g} GiB '
          f'({core["memory_reserve_gib"]:g} reserved for the host), {core["memory_free_gib"]:g} free; '
          f'queued: {len(core["queue"])}')
    for item in core['queue']:
        print(f'    queued {item["ticket"]}  {item["priority"]}  since {item["since"]}')
    print(f'  recent results: {len(status["recent_results"])}')
    for row in status['recent_results']:
        result = row.get('result', {})
        n = result.get('numbers') or {}
        if result.get('kind', 'gate') == 'gate':
            what = f'tests {n.get("tests_run")} failures {n.get("failures")} errors {n.get("errors")}'
        else:
            what = (f'{result.get("kind")} {result.get("run_name")}'
                    + (' (dry run)' if result.get('dry_run') else
                       f' stages reused {n.get("reused_stages")} rebuilt {n.get("rebuilt_stages")}'
                       + (f' failed stage {result["failed_stage"]}' if result.get('failed_stage') else '')
                       + stair_walk_text(result.get('stair_walk')) + perf_guard_text(result.get('perf_guard'))
                       + over_budget_text(result.get('over_budget'))))
        print(f'    {row["time"]}  {result.get("request_id")}  {result.get("status")}  {what}')
    return 0


def cmd_lease(args, config):
    requester = requester_of(args)
    if args.what == 'gate':
        lease = lease_gate(config, requester, args.range, args.number, args.purpose or 'gate', args.reason)
    elif args.what == 'worktree':
        if not args.target:
            raise AwError('aw lease worktree PATH')
        lease = lease_worktree(config, args.target, requester, args.purpose or '', args.reason)
    elif args.what == 'run-name':
        if not args.purpose:
            raise AwError('aw lease run-name --purpose P [--reason R] [--repo PATH]')
        lease = lease_run_name(config, Path(args.repo or ROOT), args.purpose, requester, args.reason)
    elif args.what == 'done':
        ended, changes = job_done(config, requester)
        print(json.dumps({'requester': requester, 'ended': ended, 'rebalanced': changes}, indent=2))
        return 0
    elif args.what in ('renew', 'release'):
        if not args.target:
            raise AwError(f'aw lease {args.what} LEASE_ID')
        lease = (renew if args.what == 'renew' else release)(config, args.target, requester)
    else:
        print(json.dumps(list_leases(config, args.all), indent=2, sort_keys=True))
        return 0
    print(json.dumps(lease, indent=2, sort_keys=True))
    return 0


# --------------------------------------------------------------------------

def parser():
    top = argparse.ArgumentParser(prog='aw', description='AmiWind master builder: entry check, leases, gates, build '
                                                         'requests, builder broadcast')
    top.add_argument('--config', help=f'config file (default: ${CONFIG_ENV})')
    sub = top.add_subparsers(dest='command', required=True)
    enter = sub.add_parser('enter', help='entry check of this source tree')
    enter.add_argument('--accept-version-mismatch', metavar='REASON')
    gate = sub.add_parser('gate', help='lease a gate number, run the gate, judge its output files')
    gate.add_argument('--repo', required=True)
    gate.add_argument('--commit', help='refuse unless the checkout HEAD is this commit')
    gate.add_argument('--reason', default='')
    gate.add_argument('--range', help='gate number range name from the config')
    gate.add_argument('--number', type=int, help='a specific number inside the range')
    gate.add_argument('--requester')
    gate.add_argument('--allow-dirty', action='store_true')
    gate.add_argument('--accept-version-mismatch', metavar='REASON')
    gate.add_argument('--quiet', action='store_true', help='do not echo the gate output (it is still logged)')
    status = sub.add_parser('status', help='working version, integration head, leases, recent results')
    status.add_argument('--repo')
    status.add_argument('--count', type=int, default=10)
    status.add_argument('--json', action='store_true')
    lease = sub.add_parser('lease', help='lease gate|worktree|run-name, renew|release LEASE_ID, done (the job ended: '
                                         'all its leases end), list')
    lease.add_argument('what', choices=['gate', 'worktree', 'run-name', 'renew', 'release', 'done', 'list'])
    lease.add_argument('target', nargs='?', help='worktree path or lease id')
    lease.add_argument('--range')
    lease.add_argument('--number', type=int)
    lease.add_argument('--purpose')
    lease.add_argument('--reason', default='')
    lease.add_argument('--repo')
    lease.add_argument('--requester')
    lease.add_argument('--all', action='store_true', help='list: also released and expired leases')
    import aw_service
    aw_service.add_parsers(sub)
    import aw_broadcast
    aw_broadcast.add_parsers(sub)
    return top


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        config = load_config(args.config)
        if args.command in ('submit', 'request'):
            import aw_service
            return aw_service.main(args, config)
        if args.command in ('announce', 'inbox', 'reply', 'publish', 'sync-version'):
            import aw_broadcast
            return aw_broadcast.main(args, config)
        handler = {'enter': cmd_enter, 'gate': cmd_gate, 'status': cmd_status, 'lease': cmd_lease}[args.command]
        return handler(args, config)
    except AwError as exc:
        print(f'aw {args.command}: {exc}', file=sys.stderr)
        return EXIT_NO_LEASE if args.command in ('lease', 'gate') else 2


if __name__ == '__main__':
    raise SystemExit(main())
