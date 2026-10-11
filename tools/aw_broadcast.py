# SPDX-License-Identifier: GPL-3.0-only
"""aw announce / inbox / reply / publish / sync-version: the master builder's broadcast (phase 3).
Standard library only.

The master builder tells every worker about the builder: the address list is the set of active worktree leases
(each lease holder is one worker; `aw gate` and `aw request` take or renew the lease of the worktree they run on).

    announce     a CALL FOR FIXES (kind builder-bug or builder-update): one aw-message-1 message into the inbox of
                 every lease holder, recorded in the broadcast register; with --hold every `aw request --kind build`
                 is refused until the call closes (gates are still allowed)
    inbox        a worker's unread messages (run at every checkpoint)
    reply        a worker's answer: --none, --proposal TEXT, --commit REPO:SHA, or --defer "why; when"; one line
                 is also appended to the configured merge queue file
    publish      after a passed gate of COMMIT (the gate result file checked by its SHA-256): moves the integration
                 ref, writes the integration head note and the working-version record (and its copies in the build
                 volume), closes the calls the commit fixes, lifts their hold and posts a new-builder message to
                 every lease holder
    sync-version writes the working-version record into the build volume copies again (SHA-256 checked)

After a publish, `aw gate` and `aw request` on a base without the published head are refused unless the worker
replied to the new-builder message with --defer and a reason; a hold-level builder fix also refuses builds then.
Every location comes from the config file (docs/AW.md, section "Broadcast"); this file holds no paths.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

import aw

CALL_KINDS = ('builder-bug', 'builder-update')
NEW_BUILDER = 'new-builder'
ANSWERS = ('none', 'proposal', 'commit', 'defer')
BUG_ID = re.compile(r'^[A-Z0-9][A-Z0-9-]*[A-Z0-9]$')
STALE = re.compile(r'^STALE BUILDER: \S+ does not contain the published integration head ([0-9a-f]{4,40})\b')
DIRTY_NOTE = re.compile(r'uncommitted/untracked paths \(allowed')
DEFAULT_REPLY_MIN = 30
REGISTER = 'aw-broadcast.json'
POOL_SCRIPT = 'set -e; f="$1"; t="$f.aw-tmp.$$"; cat > "$t"; mv "$t" "$f"; sha256sum "$f"'
REPLY_HOW = ('aw reply {id} --none | --proposal "TEXT" | --commit REPO:SHA | --defer "why; when" '
             '(set AW_REQUESTER=<your job> or give --job)')


# --------------------------------------------------------------------------
# Small helpers

def settings(config):
    value = config.get('broadcast')
    return dict(value) if isinstance(value, dict) else {}


def minute_stamp():
    now = aw.stamp()
    return now[:16] + now[19:]


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def same_commit(one, two):
    one, two = (one or '').lower(), (two or '').lower()
    return bool(one and two and (one.startswith(two) or two.startswith(one)))


def one_line(text):
    return re.sub(r'\s+', ' ', str(text or '')).strip()


def parse_ids(text):
    ids = [part.strip() for part in re.split(r'[,\s]+', text or '') if part.strip()]
    bad = [part for part in ids if not BUG_ID.match(part)]
    if bad:
        raise aw.AwError(f'not a bug ID (AREA-WHAT-NN, capitals, digits and dashes): {", ".join(bad)}')
    return ids


def safe_job(job):
    return re.sub(r'[^A-Za-z0-9._-]+', '-', job).strip('-.') or 'job'


def working_record(config):
    path = config.get('working_version_file')
    if path and Path(path).is_file():
        return json.loads(Path(path).read_text(encoding='utf-8'))
    return {}


def current_version(config):
    record = working_record(config)
    if record.get('working_version'):
        return 'v' + str(record['working_version']).lstrip('v')
    return aw.repo_version(aw.ROOT)


def current_head(config, repo=None):
    import aw_service
    published = aw_service.published_integration(config)
    if published:
        return published['head']
    ref = config.get('integration_ref')
    return aw.git_short(repo or aw.ROOT, ref) if ref else None


# --------------------------------------------------------------------------
# Register (state_dir/aw-broadcast.json): every message once, with its recipients, their reads and replies

def register_path(config):
    return aw.state_dir(config) / REGISTER


def empty_register():
    return {'schema': 'aw-broadcast-1', 'updated': aw.stamp(), 'next_seq': 1, 'messages': []}


def load_register(config):
    path = register_path(config)
    if not path.is_file():
        return empty_register()
    register = json.loads(path.read_text(encoding='utf-8'))
    for key, value in empty_register().items():
        register.setdefault(key, value)
    return register


def save_register(config, register):
    register['updated'] = aw.stamp()
    aw.write_json(register_path(config), register)


def holders(config, exclude=()):
    """{job: worktree} of every active worktree lease (the address list), without the jobs in EXCLUDE."""
    with aw.Lock(config, 'aw-broadcast'):
        state = aw.load_state(config)
        if bool(aw.refresh(state)) | bool(aw.expire_finished(config, state)):   # finished jobs leave the address list
            aw.save_state(config, state)
    found = {}
    for lease in aw.active(state, 'worktree'):
        if lease['requester'] not in exclude:
            found.setdefault(lease['requester'], lease['key'])
    return found


def join(config, repo, requester):
    """Takes or renews REQUESTER's lease of the worktree REPO, so the broadcast reaches it (on when the config has a
    "broadcast" section, unless broadcast.auto_join is false). None, or a note."""
    if not requester or requester == 'anonymous' or not settings(config).get('auto_join', 'broadcast' in config):
        return None
    try:
        lease = aw.lease_worktree(config, str(repo), requester, purpose='job')
        ttl = int(config.get('lease_ttl_s', {}).get('worktree', aw.DEFAULT_TTL['worktree']))
        if lease['expires_epoch'] - time.time() < ttl / 2:
            aw.renew(config, lease['id'], requester)
    except aw.AwError as exc:
        return f'broadcast address: {exc}'
    return None


def deliver(config, message, recipients):
    """One inbox file per recipient: <state_dir>/inbox/<job>/<message id>.json."""
    paths = []
    for job in sorted(recipients):
        folder = aw.state_dir(config) / 'inbox' / safe_job(job)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f'{message["id"]}.json'
        aw.write_json(path, aw.checked(dict(message, to=job), 'aw-message-1'))
        paths.append(str(path))
    return paths


def add_message(config, sender, build, recipients):
    """BUILD(register, message id) -> (message, extra entry fields); recorded under the lock and delivered."""
    with aw.Lock(config, sender):
        register = load_register(config)
        msg_id = f'msg-{register["next_seq"]}'
        register['next_seq'] += 1
        message, extra = build(register, msg_id)
        message = aw.checked(message, 'aw-message-1')
        entry = {'message': message, 'status': 'open' if message['kind'] in CALL_KINDS else 'posted',
                 'closed': None, 'closed_by': None, 'fixed_ids': [],
                 'recipients': {job: {'worktree': path, 'delivered': aw.stamp(), 'read': None, 'reply': None,
                                      'replies': []} for job, path in sorted(recipients.items())}}
        entry.update(extra)
        register['messages'].append(entry)
        save_register(config, register)
    entry['inbox_files'] = deliver(config, message, recipients)
    return entry


def open_calls(register):
    return [entry for entry in register['messages']
            if entry['message']['kind'] in CALL_KINDS and entry['status'] == 'open']


def open_holds(register):
    return [entry for entry in open_calls(register) if entry['message']['hold']]


def latest_new_builder(register):
    for entry in reversed(register['messages']):
        if entry['message']['kind'] == NEW_BUILDER:
            return entry
    return None


# --------------------------------------------------------------------------
# announce

def announce(config, kind, ids, summary, hold, sender, reply_within=None):
    if kind not in CALL_KINDS:
        raise aw.AwError(f'kind {kind!r}: one of {", ".join(CALL_KINDS)}')
    ids = parse_ids(ids) if isinstance(ids, str) else list(ids)
    summary = one_line(summary)
    if not summary:
        raise aw.AwError('a call needs --summary TEXT')
    minutes = reply_within if reply_within is not None else settings(config).get('reply_within_min', DEFAULT_REPLY_MIN)
    reply_by = aw.stamp_epoch(time.time() + float(minutes) * 60)
    recipients = holders(config, exclude={sender})
    version, head = current_version(config), current_head(config)

    def build(register, msg_id):
        text = (f'CALL FOR FIXES ({kind}) from {sender}: {", ".join(ids) or "(no bug ID)"}: {summary}. '
                f'Post your own fix commit or fix proposal, or say you have none, by {reply_by}.')
        if hold:
            text += (' BUILD HOLD: until this call closes, every build request (aw request --kind build) is '
                     'refused; gates are still allowed.')
        message = {'schema': 'aw-message-1', 'id': msg_id, 'kind': kind, 'time': aw.stamp(), 'version': version,
                   'integration_head': head, 'ids': ids, 'summary': summary, 'hold': bool(hold),
                   'reply_by': reply_by, 'from': sender, 'text': text, 'reply_how': REPLY_HOW.format(id=msg_id)}
        return message, {}

    entry = add_message(config, sender, build, recipients)
    aw.log_trial(config, 'announce', message=entry['message'], to=sorted(recipients), requester=sender,
                 version=version, commit=head)
    return entry


# --------------------------------------------------------------------------
# inbox

def inbox(config, job, show_all=False):
    """(messages for JOB - unread ones unless SHOW_ALL - marked read now, open holds)."""
    found = []
    with aw.Lock(config, job):
        register = load_register(config)
        changed = False
        for entry in register['messages']:
            record = entry['recipients'].get(job)
            if record is None or not (show_all or record['read'] is None):
                continue
            found.append({'message': dict(entry['message'], to=job), 'status': entry['status'],
                          'read': record['read'], 'reply': record['reply']})
            if record['read'] is None:
                record['read'] = aw.stamp()
                changed = True
        if changed:
            save_register(config, register)
    holds = [entry['message'] for entry in open_holds(register)]
    if found:
        aw.log_trial(config, 'inbox', requester=job, read=[item['message']['id'] for item in found])
    return found, holds


# --------------------------------------------------------------------------
# reply

def merge_queue_line(config, job, entry, answer, text, commit_ref):
    path = settings(config).get('merge_queue_file')
    if not path:
        return None
    if not Path(path).is_absolute() and config.get('_path'):
        path = Path(config['_path']).parent / path
    message = entry['message']
    about = ', '.join(message['ids']) or (message.get('commit') or '')
    words = {'none': 'no fix or proposal from this job (none)', 'proposal': f'PROPOSAL: {text}',
             'commit': (f'MERGED AT {commit_ref}' if message['kind'] == NEW_BUILDER else f'FIX COMMIT {commit_ref}')
             + (f': {text}' if text else ''),
             'defer': f'DEFERRED (why; when): {text}'}[answer]
    line = (f'| {minute_stamp()} [{current_version(config)}] | AW REPLY ({job}) | {message["id"]} {message["kind"]}'
            f' {about}: {one_line(words).replace("|", "/")} |\n')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lead = ''
    try:
        with open(path, 'rb') as handle:
            handle.seek(0, os.SEEK_END)
            if handle.tell():
                handle.seek(-1, os.SEEK_END)
                lead = '' if handle.read(1) == b'\n' else '\n'
    except OSError:
        pass
    with open(path, 'a', encoding='utf-8', newline='\n') as handle:
        handle.write(lead + line)
    return str(path)


def split_commit(text):
    repo, _, sha = (text or '').rpartition(':')
    if not repo or not re.fullmatch(r'[0-9a-fA-F]{4,40}', sha):
        raise aw.AwError(f'--commit {text!r}: give REPO:SHA (the worktree path, a colon, the commit hash)')
    return repo, sha.lower()


def reply(config, msg_id, job, answer, text='', commit=None):
    if answer not in ANSWERS:
        raise aw.AwError(f'answer {answer!r}: one of {", ".join(ANSWERS)}')
    text = one_line(text)
    if answer in ('proposal', 'defer') and not text:
        raise aw.AwError(f'--{answer} needs a text')
    register = load_register(config)
    entry = next((item for item in register['messages'] if item['message']['id'] == msg_id), None)
    if entry is None:
        raise aw.AwError(f'no message {msg_id}')
    commit_ref = None
    if answer == 'commit':
        repo, sha = split_commit(commit)
        full = aw.git(repo, 'rev-parse', '--verify', '--quiet', sha + '^{commit}')
        if not full:
            raise aw.AwError(f'commit {sha} does not resolve in {repo}')
        new_head = entry['message'].get('commit')
        if entry['message']['kind'] == NEW_BUILDER and aw.is_ancestor(repo, new_head, full) is not True:
            raise aw.AwError(f'{full[:7]} does not contain the new builder {entry["message"]["commit"]}: merge it '
                             'first, or answer --defer "why; when"')
        commit_ref = f'{repo}:{full[:12]}'
    answer_doc = {'time': aw.stamp(), 'answer': answer, 'text': text, 'commit': commit_ref, 'requester': job,
                  'version': current_version(config)}
    with aw.Lock(config, job):
        register = load_register(config)
        entry = next(item for item in register['messages'] if item['message']['id'] == msg_id)
        record = entry['recipients'].get(job)
        if record is None:
            record = entry['recipients'][job] = {'worktree': None, 'delivered': None, 'read': aw.stamp(),
                                                 'reply': None, 'replies': [], 'late': True}
        if entry['status'] == 'closed':
            answer_doc['note'] = f'answered after the call closed ({entry["closed"]})'
        record['reply'] = answer_doc
        record.setdefault('replies', []).append(answer_doc)
        if record['read'] is None:
            record['read'] = aw.stamp()
        save_register(config, register)
    queue = merge_queue_line(config, job, entry, answer, text, commit_ref)
    aw.log_trial(config, 'reply', message=msg_id, kind=entry['message']['kind'], requester=job, reply=answer_doc,
                 merge_queue=queue)
    return entry, answer_doc, queue


# --------------------------------------------------------------------------
# Enforcement used by aw gate and aw request

def deferral(config, requester, head):
    """(entry, reply) when REQUESTER answered the newest new-builder message for HEAD with --defer."""
    entry = latest_new_builder(load_register(config))
    if entry is None or not same_commit(entry['message'].get('commit'), head):
        return None
    record = entry['recipients'].get(requester) or {}
    answer = record.get('reply')
    return (entry, answer) if answer and answer['answer'] == 'defer' else None


def relax_stale(config, requester, refusals, build=False):
    """(refusals, notes): a STALE BUILDER refusal is lifted when REQUESTER deferred that head with a reason (a
    hold-level builder fix never lifts it for a build); otherwise the refusal says how to reply."""
    kept, notes = [], []
    try:
        register = load_register(config)
    except (OSError, ValueError) as exc:
        return list(refusals), [f'broadcast register unreadable: {exc}']
    latest = latest_new_builder(register)
    for text in refusals:
        match = STALE.match(text)
        if not match:
            kept.append(text)
            continue
        found = deferral(config, requester, match.group(1))
        if found is None:
            if latest is not None and same_commit(latest['message'].get('commit'), match.group(1)):
                text += (f'; or, if you cannot merge it yet, reply with why and when: aw reply '
                         f'{latest["message"]["id"]} --defer "why; when"')
            kept.append(text)
            continue
        entry, answer = found
        if build and entry['message'].get('hold_level'):
            kept.append(text + f' (your deferral of {entry["message"]["id"]} does not cover builds: '
                               f'{entry["message"]["commit"]} is a hold-level builder fix; merge it before any build)')
            continue
        notes.append(f'new builder {entry["message"]["commit"]} deferred by {requester} ({entry["message"]["id"]}, '
                     f'{answer["time"]}): "{answer["text"]}"; running on the older base')
    return kept, notes


def hold_refusals(config):
    """The refusal texts of every open call with a build hold."""
    texts = []
    for entry in open_holds(load_register(config)):
        message = entry['message']
        texts.append(f'BUILD HOLD: call {message["id"]} ({message["kind"]}: {", ".join(message["ids"]) or "-"}: '
                     f'{message["summary"]}) is open since {message["time"]}; builds wait until the fixed builder '
                     f'is published (gates are still allowed); answer the call: {REPLY_HOW.format(id=message["id"])}')
    return texts


# --------------------------------------------------------------------------
# publish

def trial_rows(config, event):
    rows = []
    try:
        with open(aw.trial_log_path(config), encoding='utf-8') as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if row.get('event') == event:
                    rows.append(row)
    except OSError:
        pass
    return rows


def judge_gate(document, short):
    """Why DOCUMENT is not a clean passed gate of SHORT (None = it is)."""
    errors = aw.validate(document, aw.schema('aw-result-1'))
    if errors:
        return 'not an aw-result-1 document: ' + '; '.join(errors[:3])
    if document['kind'] != 'gate':
        return f'kind {document["kind"]}, not a gate'
    if document['status'] != 'passed' or document['failed_steps']:
        return f'status {document["status"]}, failed steps {document["failed_steps"]}'
    if not same_commit(document['commit'], short) or not same_commit(document.get('head') or document['commit'], short):
        return f'gated commit {document["commit"]} (head {document.get("head")}) is not {short}'
    numbers = document['numbers']
    if not numbers.get('tests_run') or numbers.get('failures') or numbers.get('errors'):
        return f'suite numbers {numbers}'
    if numbers.get('engine_warnings'):
        return f'{numbers["engine_warnings"]} engine warnings'
    if any(DIRTY_NOTE.search(note) for note in document.get('notes') or []):
        return 'gated with uncommitted files (--allow-dirty): not a clean gate of the commit'
    return None


def gate_evidence(config, short, path=None, sha=None):
    """The passed gate result of SHORT, its file checked against the SHA-256 recorded when it was written."""
    if path:
        if not sha:
            raise aw.AwError('--gate-result FILE needs --gate-sha256 HEX')
        candidates = [(path, sha)]
    else:
        candidates = []
        for row in trial_rows(config, 'result'):
            result = row.get('result') or {}
            if result.get('kind', 'gate') == 'gate' and result.get('status') == 'passed' \
                    and same_commit(result.get('commit'), short):
                candidates.append((row.get('path'), row.get('sha256')))
        if not candidates:
            raise aw.AwError(f'no passed gate of {short} in the trial log: gate it with aw gate first')
    problems = []
    for where, recorded in reversed(candidates):
        if not where:
            continue
        if not recorded:
            problems.append(f'{where}: no SHA-256 was recorded with this result (gated before aw recorded result '
                            'hashes): gate again, or give --gate-result FILE --gate-sha256 HEX')
            continue
        try:
            actual = sha256_file(where)
            document = json.loads(Path(where).read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            problems.append(f'{where}: {exc}')
            continue
        if actual != recorded.lower():
            problems.append(f'{where}: SHA-256 {actual} is not the recorded {recorded}: the result file changed')
            continue
        why = judge_gate(document, short)
        if why:
            problems.append(f'{where}: {why}')
            continue
        return {'result': str(where), 'sha256': actual, 'number': document.get('gate'),
                'tests_run': document['numbers'].get('tests_run')}
    raise aw.AwError(f'no usable passed gate of {short}: ' + '; '.join(problems or ['no result file named']))


def run_with_input(command, data):
    try:
        result = subprocess.run(command, input=data, capture_output=True, timeout=300)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, str(exc)
    return result.returncode, (result.stdout + result.stderr).decode('utf-8', errors='replace')


def write_pool_files(config, data, runner=None):
    """Writes DATA to every configured working-version copy in the build volume and reads back its SHA-256."""
    targets = list(settings(config).get('pool_working_version_files') or [])
    if not targets:
        return []
    build = config.get('build') or {}
    mount = build.get('mount', '/vol')
    if not build.get('image') or not build.get('volume'):
        raise aw.AwError('broadcast.pool_working_version_files needs build.image and build.volume in the config')
    expected = sha256_bytes(data)
    results = []
    for index, target in enumerate(targets):
        if not str(target).startswith(mount.rstrip('/') + '/'):
            results.append({'file': target, 'ok': False, 'sha256': None, 'exit': None,
                            'detail': f'not under the build volume mount {mount}'})
            continue
        name = f'{build.get("container_prefix", "aw")}-publish-version-{os.getpid()}-{index}'
        command = [build.get('docker', 'docker'), 'run', '--pull', 'never', '--rm', '-i', '--network', 'none',
                   '--name', name, '--user', build.get('user', '1000:1000'), '-v', f'{build["volume"]}:{mount}',
                   build['image'], 'sh', '-c', POOL_SCRIPT, 'sh', target]
        code, output = (runner or run_with_input)(command, data)
        match = re.search(r'\b([0-9a-f]{64})\b', output or '')
        got = match.group(1) if match else None
        results.append({'file': target, 'ok': code == 0 and got == expected, 'sha256': got, 'exit': code,
                        'detail': (output or '').strip()[-300:]})
    return results


def record_bytes(record):
    return (json.dumps(record, ensure_ascii=False) + '\n').encode('utf-8')


def write_record(path, data):
    path = Path(path)
    tmp = path.with_name(path.name + f'.tmp-{os.getpid()}')
    tmp.write_bytes(data)
    os.replace(tmp, path)


def sync_version(config, runner=None):
    path = config.get('working_version_file')
    if not path or not Path(path).is_file():
        raise aw.AwError('no working_version_file in the config (or it is missing)')
    data = Path(path).read_bytes()
    results = write_pool_files(config, data, runner)
    aw.log_trial(config, 'sync-version', sha256=sha256_bytes(data), pool=results)
    return sha256_bytes(data), results


def publish(config, commit, contains, sender, repo=None, fixes='', closes='', gate_result=None, gate_sha=None,
            hold_level=False, runner=None):
    repo = Path(repo or aw.ROOT).resolve()
    allowed = settings(config).get('publishers')
    if allowed and sender not in allowed:
        raise aw.AwError(f'{sender} may not publish (broadcast.publishers: {", ".join(allowed)})')
    contains = one_line(contains)
    if not contains:
        raise aw.AwError('publish needs --contains "what the new head brings"')
    full = aw.git(repo, 'rev-parse', '--verify', '--quiet', f'{commit}^{{commit}}')
    if not full:
        raise aw.AwError(f'commit {commit} does not resolve in {repo}')
    short = full[:7]
    version_text = aw.git(repo, 'show', f'{full}:VERSION')
    if not version_text:
        raise aw.AwError(f'{short} has no VERSION file')
    version = 'v' + version_text.strip().lstrip('v')
    evidence = gate_evidence(config, short, gate_result, gate_sha)
    import aw_service
    published = aw_service.published_integration(config)
    ref = config.get('integration_ref')
    ref_old = aw.git(repo, 'rev-parse', '--verify', '--quiet', f'refs/heads/{ref}') if ref else None
    if published and same_commit(published['head'], full):
        raise aw.AwError(f'{short} is already the published integration head')
    for old, what in ((published and published['head'], 'published integration head'), (ref_old, ref)):
        if old and aw.is_ancestor(repo, old, full) is not True:
            raise aw.AwError(f'{short} does not contain the {what} {old[:7]}: a publish only moves forward')
    fix_ids = set(parse_ids(fixes)) if fixes else set()
    close_ids = {part for part in re.split(r'[,\s]+', closes or '') if part}
    register = load_register(config)
    for entry in open_calls(register):
        fix_ids |= {bug for bug in entry['message']['ids'] if re.search(rf'(?<![A-Z0-9-]){re.escape(bug)}(?![A-Z0-9-])',
                                                                         contains)}
    known = {entry['message']['id'] for entry in register['messages']}
    unknown = close_ids - known
    if unknown:
        raise aw.AwError(f'--closes names unknown messages: {", ".join(sorted(unknown))}')
    notes = []
    # 1. the integration ref (compare-and-swap)
    if ref:
        moved = aw.git(repo, 'update-ref', '-m', f'aw publish {short} by {sender}', f'refs/heads/{ref}', full,
                       ref_old or '0' * 40)
        if moved is None:
            raise aw.AwError(f'could not move {ref} to {short} (it changed meanwhile?); nothing else was changed')
    else:
        notes.append('no integration_ref in the config: no git ref moved')
    # 2. the integration head note
    when = minute_stamp()
    head_file = config.get('integration_head_file')
    if head_file:
        old_text = Path(head_file).read_text(encoding='utf-8') if Path(head_file).is_file() else ''
        entry_text = (f'PUBLISHED (aw gate {evidence["number"]} PASSED): {short}  branch {ref or "-"} '
                      f'(VERSION {version[1:]}; suite {evidence["tests_run"]} tests 0 failures; {when}; '
                      f'aw publish by {sender})\nCONTAINS: {contains}\n\n')
        write_record(head_file, (entry_text + old_text).encode('utf-8'))
    else:
        notes.append('no integration_head_file in the config: no head note written')
    # 3. the working-version record and its copies in the build volume
    pool = []
    record_path = config.get('working_version_file')
    if record_path:
        record = working_record(config)
        record.update({'working_version': version[1:], 'head': short, 'updated': when,
                       'note': f'aw publish {short} (aw gate {evidence["number"]}): {contains[:200]}'})
        data = record_bytes(record)
        write_record(record_path, data)
        try:
            pool = write_pool_files(config, data, runner)
        except aw.AwError as exc:
            pool = [{'file': '-', 'ok': False, 'sha256': None, 'exit': None, 'detail': str(exc)}]
    else:
        notes.append('no working_version_file in the config: no working-version record written')
    pool_bad = [item for item in pool if not item['ok']]
    if pool_bad:
        notes.append('build volume working-version copies NOT updated: ' + '; '.join(
            f'{item["file"]}: {item["detail"] or item["exit"]}' for item in pool_bad)
            + ' - run aw sync-version once the container runs')
    # 4. close the calls, lift their holds, post the new builder to every lease holder
    recipients = holders(config, exclude={sender})
    outcome = {}

    def build(register, msg_id):
        closed, proposals = [], []
        for entry in open_calls(register):
            ids = set(entry['message']['ids'])
            entry['fixed_ids'] = sorted(set(entry.get('fixed_ids') or []) | (ids & fix_ids))
            if entry['message']['id'] in close_ids or (ids and ids <= fix_ids):
                entry.update(status='closed', closed=aw.stamp(), closed_by=msg_id)
                closed.append(entry)
                for job, record in sorted(entry['recipients'].items()):
                    answer = record.get('reply') or {}
                    if answer.get('answer') in ('proposal', 'commit'):
                        said = ' '.join(part for part in (answer.get('commit'), answer.get('text')) if part)
                        proposals.append(f'{job}: {said}')
        still = [entry['message']['id'] for entry in open_holds(register)]
        level = bool(hold_level or any(entry['message']['kind'] == 'builder-bug' or entry['message']['hold']
                                       for entry in closed))
        merge = f'git merge {ref}' if ref else f'git merge {short}'
        text = (f'NEW BUILDER {short} ({version}), published {aw.stamp()} by {sender} after aw gate '
                f'{evidence["number"]} ({evidence["tests_run"]} tests, 0 failures). Contains: {contains}.')
        if closed:
            text += ' Closes: ' + ', '.join(f'{entry["message"]["id"]} ({", ".join(entry["message"]["ids"])})'
                                            for entry in closed) + '.'
        text += (' Proposals received: ' + '; '.join(proposals) + '.' if proposals
                 else ' No fix proposals came in: well, here is the new version.')
        text += (f' Merge it at your next checkpoint (never mid-build or mid-test): {merge}, then gate.'
                 f' If you cannot yet, reply with why and when: aw reply {msg_id} --defer "why; when";'
                 f' until you merged or replied, aw gate and aw request refuse a base without {short}.')
        if level:
            text += ' HOLD-LEVEL builder fix: no build on a base without it, deferral or not.'
        if still:
            text += f' BUILD HOLD still in force for: {", ".join(still)}.'
        outcome.update(closed=[entry['message']['id'] for entry in closed], holds_left=still, proposals=proposals,
                       hold_level=level)
        message = {'schema': 'aw-message-1', 'id': msg_id, 'kind': NEW_BUILDER, 'time': aw.stamp(),
                   'version': version, 'integration_head': short, 'ids': sorted(fix_ids),
                   'summary': f'new builder {short}: {contains}', 'hold': bool(still), 'reply_by': None,
                   'from': sender, 'text': text, 'reply_how': REPLY_HOW.format(id=msg_id), 'commit': short,
                   'contains': contains, 'closes': outcome['closed'], 'hold_level': level,
                   'gate': {key: evidence[key] for key in ('result', 'sha256', 'number', 'tests_run')}}
        return message, {}

    entry = add_message(config, sender, build, recipients)
    document = {'head': short, 'full': full, 'version': version, 'gate': evidence, 'ref': ref,
                'previous_ref': (ref_old or '')[:7] or None, 'message': entry['message']['id'],
                'to': sorted(recipients), 'pool': pool, 'notes': notes, **outcome}
    aw.log_trial(config, 'publish', requester=sender, version=version, commit=short, publish=document)
    document['status'] = 'failed' if pool_bad else 'passed'
    return document


# --------------------------------------------------------------------------
# Status

def summary(config):
    register = load_register(config)
    calls = []
    for entry in open_calls(register):
        message = entry['message']
        answered = {job: record['reply']['answer'] for job, record in entry['recipients'].items() if record['reply']}
        calls.append({'id': message['id'], 'kind': message['kind'], 'ids': message['ids'], 'hold': message['hold'],
                      'time': message['time'], 'from': message['from'], 'reply_by': message['reply_by'],
                      'answered': answered,
                      'unanswered': sorted(job for job, record in entry['recipients'].items() if not record['reply'])})
    latest = latest_new_builder(register)
    newest = None
    if latest:
        message = latest['message']
        state = {}
        for job, record in sorted(latest['recipients'].items()):
            answer = record.get('reply') or {}
            merged = aw.is_ancestor(record['worktree'], message['commit'], 'HEAD') if record.get('worktree') else None
            if merged:
                state[job] = 'merged'
            elif answer.get('answer') == 'defer':
                state[job] = f'deferred: {answer["text"]}'
            elif answer.get('answer') == 'commit':
                state[job] = f'merged at {answer["commit"]}'
            else:
                state[job] = 'waiting' + (' (read)' if record.get('read') else ' (unread)')
        newest = {'id': message['id'], 'commit': message['commit'], 'time': message['time'],
                  'hold_level': message.get('hold_level', False), 'holders': state}
    return {'open_calls': calls, 'holds': [call['id'] for call in calls if call['hold']], 'new_builder': newest}


def print_summary(info):
    print(f'  broadcast: {len(info["open_calls"])} open call(s)'
          + (f', BUILD HOLD by {", ".join(info["holds"])}' if info['holds'] else ', no build hold'))
    for call in info['open_calls']:
        print(f'    {call["id"]} {call["kind"]} {", ".join(call["ids"])} from {call["from"]} at {call["time"]}'
              f'{" HOLD" if call["hold"] else ""}; reply by {call["reply_by"]}')
        for job, answer in sorted(call['answered'].items()):
            print(f'      answered: {job} ({answer})')
        print('      not answered: ' + (', '.join(call['unanswered']) or 'nobody'))
    newest = info['new_builder']
    if newest:
        print(f'    last new builder: {newest["id"]} {newest["commit"]} at {newest["time"]}'
              + (' (hold-level)' if newest['hold_level'] else ''))
        for job, state in newest['holders'].items():
            print(f'      {job}: {state}')


# --------------------------------------------------------------------------
# Command line

def print_message(item):
    message = item['message']
    print('-' * 72)
    print(f'{message["id"]}  {message["kind"]}  {message["time"]}  from {message["from"]}'
          + ('  BUILD HOLD' if message['hold'] else '') + (f'  [{item["status"]}]' if item.get('status') else ''))
    print(f'  version {message["version"]}, integration head {message["integration_head"]}'
          + (f', ids {", ".join(message["ids"])}' if message['ids'] else ''))
    print('  ' + message.get('text', message['summary']))
    if item.get('reply'):
        print(f'  your reply: {item["reply"]["answer"]} {item["reply"]["text"]} at {item["reply"]["time"]}')
    else:
        print('  reply: ' + message.get('reply_how', ''))


def add_parsers(sub):
    announce_p = sub.add_parser('announce', help='call for fixes: a message to every lease holder')
    announce_p.add_argument('--kind', required=True, choices=CALL_KINDS)
    announce_p.add_argument('--ids', required=True, help='bug IDs, comma separated')
    announce_p.add_argument('--summary', required=True)
    announce_p.add_argument('--hold', action='store_true', help='refuse every build request until the call closes')
    announce_p.add_argument('--reply-within', type=float, metavar='MINUTES')
    announce_p.add_argument('--requester')
    inbox_p = sub.add_parser('inbox', help="a worker's unread broadcast messages")
    inbox_p.add_argument('--job', help='default: AW_REQUESTER')
    inbox_p.add_argument('--all', action='store_true', help='also the messages already read')
    inbox_p.add_argument('--json', action='store_true')
    inbox_p.add_argument('--requester')
    reply_p = sub.add_parser('reply', help='answer a broadcast message')
    reply_p.add_argument('message', help='the message id (msg-N)')
    answer = reply_p.add_mutually_exclusive_group(required=True)
    answer.add_argument('--none', action='store_true', help='no fix or proposal from this job')
    answer.add_argument('--proposal', metavar='TEXT')
    answer.add_argument('--commit', metavar='REPO:SHA', help='a fix commit (or, to a new builder: merged at)')
    answer.add_argument('--defer', metavar='WHY_WHEN', help='cannot merge the new builder yet: why and when')
    reply_p.add_argument('--text', default='', help='a comment with --commit')
    reply_p.add_argument('--job', help='default: AW_REQUESTER')
    reply_p.add_argument('--requester')
    publish_p = sub.add_parser('publish', help='publish a gated commit as the new builder head and tell every worker')
    publish_p.add_argument('--commit', required=True)
    publish_p.add_argument('--contains', required=True, help='what the new head brings (one line)')
    publish_p.add_argument('--repo', help='a checkout of the repository (default: this one)')
    publish_p.add_argument('--fixes', default='', help='bug IDs the commit fixes (also read from --contains)')
    publish_p.add_argument('--closes', default='', help='message ids of calls to close regardless of their IDs')
    publish_p.add_argument('--gate-result', help='a gate result file (with --gate-sha256) instead of the trial log')
    publish_p.add_argument('--gate-sha256')
    publish_p.add_argument('--hold-level', action='store_true', help='a hold-level builder fix: no deferral for builds')
    publish_p.add_argument('--json', action='store_true')
    publish_p.add_argument('--requester')
    sync_p = sub.add_parser('sync-version', help='copy the working-version record into the build volume again')
    sync_p.add_argument('--requester')


def main(args, config):
    try:
        who = aw.requester_of(args)
        if args.command == 'announce':
            entry = announce(config, args.kind, args.ids, args.summary, args.hold, who, args.reply_within)
            message = entry['message']
            print(f'aw announce: {message["id"]} {message["kind"]} {", ".join(message["ids"])}'
                  + (' with BUILD HOLD' if message['hold'] else '') + f', reply by {message["reply_by"]}')
            print('  sent to: ' + (', '.join(sorted(entry['recipients'])) or
                                   'nobody (no worktree lease is active; the call is recorded)'))
            return 0
        if args.command == 'inbox':
            job = args.job or who
            found, holds = inbox(config, job, args.all)
            if args.json:
                print(json.dumps({'job': job, 'messages': found, 'holds': holds}, indent=2, sort_keys=True))
                return 0
            print(f'aw inbox {job}: {len(found)} {"message(s)" if args.all else "unread message(s)"}')
            for item in found:
                print_message(item)
            for message in holds:
                print(f'BUILD HOLD in force: {message["id"]} ({", ".join(message["ids"])}): builds are refused, '
                      'gates are allowed')
            return 0
        if args.command == 'reply':
            job = args.job or who
            answer = next(name for name in ANSWERS if getattr(args, name) not in (None, False))
            text = {'proposal': args.proposal, 'defer': args.defer}.get(answer) or args.text
            entry, answer_doc, queue = reply(config, args.message, job, answer, text, args.commit)
            print(f'aw reply: {job} -> {args.message} ({entry["message"]["kind"]}): {answer}'
                  + (f' {answer_doc["commit"]}' if answer_doc['commit'] else '') + (f': {text}' if text else ''))
            if queue:
                print(f'  merge queue line appended: {queue}')
            return 0
        if args.command == 'publish':
            document = publish(config, args.commit, args.contains, who, args.repo, args.fixes, args.closes,
                               args.gate_result, args.gate_sha256, args.hold_level)
            if args.json:
                print(json.dumps(document, indent=2, sort_keys=True))
            else:
                print(f'aw publish: {document["head"]} ({document["version"]}) after gate {document["gate"]["number"]}'
                      f' (result SHA-256 {document["gate"]["sha256"][:16]}...): {document["status"].upper()}')
                print(f'  {document["ref"] or "no ref"}: {document["previous_ref"]} -> {document["head"]}')
                print(f'  closed calls: {", ".join(document["closed"]) or "none"}; holds left: '
                      f'{", ".join(document["holds_left"]) or "none"}; proposals: {len(document["proposals"])}')
                print(f'  new-builder message {document["message"]} to: {", ".join(document["to"]) or "nobody"}')
                for item in document['pool']:
                    print(f'  build volume copy {item["file"]}: {"ok" if item["ok"] else "NOT UPDATED"}')
                for note in document['notes']:
                    print('  NOTE: ' + note)
            return 0 if document['status'] == 'passed' else 1
        if args.command == 'sync-version':
            digest, results = sync_version(config)
            print(f'aw sync-version: record SHA-256 {digest}')
            for item in results:
                print(f'  {item["file"]}: {"ok" if item["ok"] else "FAILED " + str(item["detail"])}')
            if not results:
                print('  no broadcast.pool_working_version_files in the config')
            return 0 if all(item['ok'] for item in results) else 1
    except aw.AwError as exc:
        print(f'aw {args.command}: REFUSED: {exc}', file=sys.stderr)
        return aw.EXIT['refused']
    raise aw.AwError(f'unknown command {args.command}')
