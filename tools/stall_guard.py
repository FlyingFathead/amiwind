"""The master builder's stall fallback (standard library only), on by default for every long step aw runs.

A long step (a build, a gate, a delivery step) that shows no progress for a set time is stopped with the reason
instead of sitting idle for hours. No progress means all three at once:
  * no new output line (the builder's own "[heartbeat]" lines do not count: they say the stage is silent),
  * no growth of the step's log files, and
  * the step's own containers together under a small CPU share (IDLE_CPU percent), or no CPU reading at all for
    twice the limit.
The limit is DEFAULT_LIMIT_S, or for a stage with a history a multiple (HISTORY_FACTOR) of the longest silence that
stage showed in an earlier passing run (kept in the history file), whichever is longer.

On a stall it prints what the step waits on (the last lines), the processes of its own containers, the processes of a
named shell container and any leftover process there older than ORPHAN_S, then ends ONLY the step's own containers
and process and returns STALL_EXIT with the reason and the resume command. Another job's containers are never touched.

A known transient wait (a line matching WAIT_RE: a memory wait, a lease or gate queue) is not a stall: the clock is
held and the guard prints what the step waits for every WAIT_REPORT_S seconds instead.

Settings (environment, so every caller gets the same defaults): AW_STALL=off turns the fallback off for one run (a
loud debugging switch); AW_STALL_LIMIT_S, AW_STALL_IDLE_CPU, AW_STALL_SHELL_CONTAINER.
"""
import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

STALL_EXIT = 75
DEFAULT_LIMIT_S = 20 * 60
HISTORY_FACTOR = 3.0
IDLE_CPU = 5.0                  # percent of one core, the step's containers together
ORPHAN_S = 45 * 60
WAIT_REPORT_S = 300
WAIT_MAX_S = 6 * 3600           # a known wait holds the clock at most this long (the lease queue's own timeout)
UNDERUSED_S = 5 * 60           # under half the planned cores this long = flagged (printed, in the result)
CHECK_S = 10
HEARTBEAT_RE = re.compile(r'\[heartbeat\] ([^:]+):.*\(no output for ([0-9hms .]+)\)')
WAIT_RE = re.compile(r'(?i)(gate-queue: queued|queued behind|waiting for (a |the )?(lease|memory|slot|free|gate)|'
                     r'lease queue|waits? for a gate-free|memory wait|in the queue)')


def enabled():
    return os.environ.get('AW_STALL', '').strip().lower() not in ('off', '0', 'no', 'false')


def _seconds(text):
    """'1h 02m 03s' / '45.0s' / '12m' -> seconds."""
    total = 0.0
    for value, unit in re.findall(r'([0-9.]+)\s*([hms])', text):
        total += float(value) * {'h': 3600, 'm': 60, 's': 1}[unit]
    return total


def _run(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
        return r.returncode, r.stdout
    except (OSError, subprocess.TimeoutExpired):
        return 1, ''


def docker_containers(patterns):
    """Names of running containers that contain one of PATTERNS (this job's own names only)."""
    if not patterns:
        return []
    code, out = _run(['docker', 'ps', '--format', '{{.Names}}'])
    if code:
        return []
    return [n for n in out.split() if any(own_name(n, p) for p in patterns)]


def own_name(name, part):
    """NAME is this job's container: it is PART, or PART is one of its dash-separated pieces (a gate number "-10645"
    matches amiwind-gate-suite-10645 and amiwind-gate-stage-10645-source, never amiwind-gate-suite-106450)."""
    if name == part:
        return True
    piece = part.strip('-')
    pieces = name.split('-')
    width = len(piece.split('-'))
    return any('-'.join(pieces[i:i + width]) == piece for i in range(len(pieces) - width + 1))


def docker_cpu(names):
    """Total CPU percent of NAMES, or None when it cannot be read."""
    if not names:
        return None
    code, out = _run(['docker', 'stats', '--no-stream', '--format', '{{.CPUPerc}}'] + list(names), timeout=90)
    if code:
        return None
    total = 0.0
    for line in out.split():
        try:
            total += float(line.strip().rstrip('%') or 0)
        except ValueError:
            pass
    return total


def command_containers(command):
    """The container names a docker command line names with --name (its own job's containers)."""
    names = []
    for i, part in enumerate(command):
        part = str(part)
        if part == '--name' and i + 1 < len(command):
            names.append(str(command[i + 1]))
        elif part.startswith('--name='):
            names.append(part.split('=', 1)[1])
    return names


def load_history(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError, TypeError):
        return {}


def save_history(path, history):
    if not path:
        return
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(history, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    except OSError:
        pass


class Guard:
    """The clock and the verdict for one step. Feed it lines (line()), log sizes and CPU readings (check());
    check() returns None while the step is fine, else the stall reason."""

    def __init__(self, name, limit_s=None, history=None, idle_cpu=None, factor=HISTORY_FACTOR, clock=time.monotonic,
                 stream=None, wait_report_s=WAIT_REPORT_S, planned_cores=None):
        self.name = name
        self.base = float(limit_s if limit_s is not None else os.environ.get('AW_STALL_LIMIT_S') or DEFAULT_LIMIT_S)
        self.idle_cpu = float(idle_cpu if idle_cpu is not None else os.environ.get('AW_STALL_IDLE_CPU') or IDLE_CPU)
        self.history = dict(history or {})
        self.factor = factor
        self.clock = clock
        self.stream = stream or sys.stdout
        self.wait_report_s = wait_report_s
        now = clock()
        self.last_progress = now
        self.waiting = None          # the wait line while a known wait holds the clock
        self.wait_since = now
        self.wait_said = None
        self.planned = planned_cores
        self.started = now
        self.under_since, self.under_said = None, False
        self.underused = []          # the UNDERUSED texts of this run (for the result)
        self.stage = None
        self.beat_cpu = None         # (percent, when) from the last builder heartbeat
        self.silences = {}           # stage -> the longest silence seen in this run
        self.last_lines = []
        self.sizes = {}

    def limit(self):
        seen = float(self.history.get(self.stage, 0) or 0) if self.stage else 0.0
        return max(self.base, self.factor * seen)

    def line(self, text):
        text = text.rstrip('\n')
        self.last_lines = (self.last_lines + [text])[-12:]
        beat = HEARTBEAT_RE.search(text)
        if beat:                                     # the builder says a stage is silent: no progress
            self.waiting = None                      # and the stage runs, so it is no longer in a wait
            self.stage = beat.group(1).strip()
            cores = re.search(r', ([0-9.]+) cores \(no output', text)
            # the builder's own reading of the stage's process tree: a CPU reading where docker cannot be asked
            self.beat_cpu = (float(cores.group(1)) * 100.0, self.clock()) if cores else None
            self.silences[self.stage] = max(self.silences.get(self.stage, 0), _seconds(beat.group(2)))
            return
        if WAIT_RE.search(text):
            if self.waiting is None:
                self.wait_since = self.clock()
            self.waiting = text.strip()[:200]
            self.last_progress = self.clock()
            return
        self.waiting = None
        self.last_progress = self.clock()

    def logs(self, paths):
        """Log growth counts as progress."""
        for p in paths or ():
            try:
                size = os.path.getsize(p)
            except OSError:
                continue
            if self.sizes.get(p) is not None and size != self.sizes[p]:
                self.last_progress = self.clock()
            self.sizes[p] = size

    def cores(self, cpu):
        """UNDER HALF ITS PLANNED CORES for UNDERUSED_S: a flag, not a stop (the step is working, too slowly).
        Prints what runs, how long, and the cores used against the cores planned; once per stretch."""
        now = self.clock()
        if not self.planned or cpu is None or self.waiting:
            self.under_since = None
            return None
        used = cpu / 100.0
        if used >= self.planned / 2:
            self.under_since, self.under_said = None, False
            return None
        if self.under_since is None:
            self.under_since = now
        if self.under_said or now - self.under_since < UNDERUSED_S:
            return None
        self.under_said = True
        text = ('%s: %s on %.1f of %g planned cores (under half) for %d s, %d s into the step; last line: %s'
                % (self.name, ('stage ' + self.stage) if self.stage else 'the step', used, self.planned,
                   now - self.under_since, now - self.started, (self.last_lines[-1] if self.last_lines else '')[:160]))
        self.underused.append(text)
        print('[stall-guard] UNDERUSED ' + text, file=self.stream, flush=True)
        return text

    def check(self, cpu):
        now = self.clock()
        self.cores(cpu)
        if self.waiting and now - self.wait_since >= WAIT_MAX_S:
            # a wait has an upper bound: past it, the step is judged like any other (its CPU and output)
            self.waiting = None
        if self.waiting:
            self.last_progress = now                 # a known wait holds the clock
            if self.wait_said is None or now - self.wait_said >= self.wait_report_s:
                self.wait_said = now
                print('[stall-guard] %s: waiting, not stalled: %s' % (self.name, self.waiting), file=self.stream,
                      flush=True)
            return None
        silent = now - self.last_progress
        limit = self.limit()
        if self.beat_cpu and now - self.beat_cpu[1] <= 120:
            cpu = max(cpu or 0.0, self.beat_cpu[0])
        if cpu is not None and cpu >= self.idle_cpu:
            return None                              # working without printing: not a stall
        if cpu is None and silent < 2 * limit:
            return None
        if silent < limit:
            return None
        where = ('stage %s' % self.stage) if self.stage else 'the step'
        return ('%s: %s showed no progress for %d s (limit %d s%s): no new output line, no log growth, its containers '
                'at %s CPU' % (self.name, where, silent, limit,
                               ', %.0f x its recorded silence' % self.factor if limit > self.base else '',
                               'unknown' if cpu is None else '%.1f %%' % cpu))

    def passed_history(self):
        """The history after a passing run: each stage keeps its longest silence."""
        merged = dict(self.history)
        for stage, secs in self.silences.items():
            merged[stage] = max(float(merged.get(stage, 0) or 0), secs)
        return merged


def diagnose(guard, own, shell=None, stream=None):
    """What the step waits on: its last lines, its own containers' processes, the shell container's processes and its
    leftovers older than ORPHAN_S."""
    stream = stream or sys.stdout
    say = lambda text: print('[stall-guard] ' + text, file=stream, flush=True)  # noqa: E731
    say('STALLED: last lines of the step:')
    for text in guard.last_lines[-8:]:
        say('  | ' + text[:200])
    for name in own:
        code, out = _run(['docker', 'top', name])
        say('processes of %s:' % name)
        for text in out.splitlines()[:20]:
            say('  ' + text[:200])
    orphans = []
    if shell:
        code, out = _run(['docker', 'exec', shell, 'ps', '-eo', 'pid=,etimes=,stat=,args='])
        say('processes of %s:' % shell)
        for text in out.splitlines():
            say('  ' + text[:200])
            parts = text.split(None, 3)
            if len(parts) == 4 and parts[1].isdigit() and parts[0] != '1' and not parts[2].startswith('Z') \
                    and not parts[3].startswith('ps ') and int(parts[1]) > ORPHAN_S:
                orphans.append((parts[0], int(parts[1]), parts[3]))
        for pid, secs, args in orphans:
            say('LEFTOVER in %s, running %d min, pid %s: %s (end it: docker exec %s kill %s)'
                % (shell, secs // 60, pid, args[:120], shell, pid))
    return orphans


def run_watched(command, env=None, log_path=None, echo=True, name='step', containers=None, extra_logs=(),
                history_path=None, resume='', limit_s=None, cpu_probe=None, kill=None, shell=None, stream=None,
                check_s=CHECK_S, planned_cores=None, report=None):
    """Runs COMMAND like aw.run_logged (output copied to LOG_PATH and stdout), under the stall guard. CONTAINERS =
    name parts of this job's own containers (default: the --name values of the command). Returns the exit code, or
    STALL_EXIT after ending the step's own containers and process."""
    stream = stream or sys.stdout
    if not enabled():
        print('[stall-guard] %s: OFF for this run (AW_STALL=off)' % name, file=stream, flush=True)
    own = list(containers if containers is not None else command_containers(command))
    shell = shell if shell is not None else (os.environ.get('AW_STALL_SHELL_CONTAINER') or None)
    history = load_history(history_path) if history_path else {}
    guard = Guard(name, limit_s=limit_s, history=history, stream=stream, planned_cores=planned_cores)
    report = report if report is not None else {}
    report['underused'] = guard.underused          # the same list: filled while the step runs
    probe = cpu_probe or (lambda: docker_cpu(docker_containers(own)))
    log = open(log_path, 'w', encoding='utf-8', newline='\n') if log_path else None
    process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                               encoding='utf-8', errors='replace')
    lock = threading.Lock()

    def reader():
        try:
            lines = iter(process.stdout)
            for text in lines:
                with lock:
                    guard.line(text)
                    if log and not log.closed:       # never after the step's log was closed (a stall kill)
                        log.write(text)
                        log.flush()
                if echo:
                    stream.write(text)
                    stream.flush()
        except (ValueError, OSError):
            pass                                     # the pipe closed under us after a stall kill

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    reason = None
    try:
        while process.poll() is None:
            thread.join(check_s)
            if process.poll() is not None or not enabled():
                continue
            cpu = probe()
            with lock:
                guard.logs(list(extra_logs))
                reason = guard.check(cpu)
            if reason:
                break
        if reason:
            report['stalled'] = reason
            print('[stall-guard] ' + reason, file=stream, flush=True)
            mine = docker_containers(own) if cpu_probe is None else list(own)
            diagnose(guard, mine, shell, stream)
            (kill or _kill)(process, mine, stream)
            print('[stall-guard] FAILED FAST: %s' % reason, file=stream, flush=True)
            if resume:
                print('[stall-guard] resume: %s' % resume, file=stream, flush=True)
            thread.join(10)                          # the reader drains what the ended step still printed
            with lock:
                if log:
                    log.write('[stall-guard] FAILED FAST: %s\n' % reason)
            return STALL_EXIT
        thread.join(5)
        code = process.wait()
        if code == 0 and history_path:
            save_history(history_path, guard.passed_history())
        return code
    finally:
        with lock:                                   # the reader checks log.closed under the same lock
            if log:
                log.close()
        if process.stdout:
            process.stdout.close()


def _kill(process, own, stream):
    """Ends only this step's own containers and process."""
    for name in own:
        print('[stall-guard] ending own container %s' % name, file=stream, flush=True)
        _run(['docker', 'kill', name])
    try:
        process.terminate()
        process.wait(30)
    except (OSError, subprocess.TimeoutExpired):
        process.kill()
