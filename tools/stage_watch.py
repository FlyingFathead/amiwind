# SPDX-License-Identifier: GPL-3.0-only
"""The scheduler's live supervisor of running stages (BUILD-STAGE-ALLOWANCE-STUCK-43).

Every SAMPLE_SECONDS the scheduler (tools/build_parallel.py execute_parallel) asks this watch about each running
pooled stage: the cores its processes really used since the last look (/proc), the workers it is allowed (its
allowance file) and its share of the budget, and what its pools report (tools/pool_status.py: units queued and
running, the slowest running unit by name).

1. It fixes first: the scheduler lends the workers of a stage that has nothing queued to the stages that do
   (lend_shares), and the memory guard grows a held stage back as soon as its workers' measured memory fits
   (tools/resource_plan.py SchedulerGuard).
2. A stage that still runs under half its share for over UNDERUSE_SECONDS while units are queued is an occurrence:
   one [underused] warning line in the build log and one JSON line in RUN/underused.jsonl (stage, cores used and
   allowed, share, queued and running units, the slowest unit, since when, who holds it). One line per occurrence;
   the occurrence ends when the stage is back over half its share or has nothing queued. The build carries on: an
   occurrence is a warning in the build summary (tools/build_digest.py), never a failure.
3. Per stage it keeps the numbers the build summary shows: mean cores used, the allowance over time, and the
   longest stretch under half its share.

Observability and worker shares only (a key-neutral module, tools/build_cache.py INSTRUMENTATION_MODULES): it never
changes what a stage computes.
"""
import json
import time
from pathlib import Path

import pool_status

SAMPLE_SECONDS = 5.0
UNDERUSE_SECONDS = 60.0
UNDERUSE_SHARE = 0.5
FILE = 'underused.jsonl'


def tree_cpu_seconds(pid):
    """CPU seconds of PID and its live descendants (build_profile.tree_usage), or None off Linux."""
    try:
        import build_profile
        if not build_profile.linux_proc():
            return None
        seconds, _rss, count = build_profile.tree_usage(pid)
        return seconds if count else None
    except (OSError, ValueError, ImportError):
        return None


class StageWatch:
    def __init__(self, run, clock=time.monotonic, cpu=tree_cpu_seconds, status=pool_status.read, log=None,
                 wall=time.time, sample_seconds=SAMPLE_SECONDS, underuse_seconds=UNDERUSE_SECONDS):
        self.run = Path(run)
        self.clock, self.cpu, self.status, self.wall = clock, cpu, status, wall
        self.log = log or (lambda line: print(line, flush=True))
        self.sample_seconds, self.underuse_seconds = sample_seconds, underuse_seconds
        self.at = None
        self.stages = {}          # name -> live numbers
        self.occurrences = []     # every underuse occurrence (also in RUN/underused.jsonl)
        self.demand = {}          # name -> pool_status.read() of the last look

    def started(self, name, pid, allowance_file, start):
        self.stages[name] = {'pid': pid, 'file': allowance_file, 'start': start, 'last': None, 'samples': 0,
                             'cpu_seconds': 0.0, 'watched_seconds': 0.0, 'allowed_seconds': 0.0,
                             'under_since': None, 'under_longest': 0.0, 'open': None}

    def finished(self, name):
        stage = self.stages.get(name)
        if stage is not None:
            self._close(name, stage, self.clock())
            stage['done'] = True
        self.demand.pop(name, None)

    def due(self):
        now = self.clock()
        return self.at is None or now - self.at >= self.sample_seconds

    def sample(self, running):
        """RUNNING: {stage: (allowance now, share now)} of the pooled stages. Returns {stage: demand} (pool status,
        or None when the stage's pools say nothing)."""
        now = self.clock()
        self.at = now
        for name, (allowance, share) in running.items():
            stage = self.stages.get(name)
            if stage is None or stage.get('done'):
                continue
            demand = self.status(stage['file'])
            self.demand[name] = demand
            seconds = self.cpu(stage['pid'])
            last, stage['last'] = stage['last'], (now, seconds)
            if last is None or seconds is None or last[1] is None or now <= last[0]:
                continue
            dt = now - last[0]
            cores = max(0.0, (seconds - last[1]) / dt)
            stage['samples'] += 1
            stage['cpu_seconds'] += cores * dt
            stage['watched_seconds'] += dt
            stage['allowed_seconds'] += allowance * dt
            stage['cores_now'], stage['allowance_now'], stage['share_now'] = round(cores, 2), allowance, share
            allowed = max(allowance, share)
            queued = demand is not None and demand.get('more')
            under = allowed >= 2 and cores < UNDERUSE_SHARE * allowed
            if under:
                if stage['under_since'] is None:
                    stage['under_since'] = last[0]
                stage['under_longest'] = max(stage['under_longest'], now - stage['under_since'])
            else:
                stage['under_since'] = None
            if under and queued:
                since = stage['under_since']
                if stage['open'] is None and now - since >= self.underuse_seconds:
                    self._open(name, stage, since, now, cores, allowance, share, demand)
                elif stage['open'] is not None:
                    stage['open']['seconds'] = round(now - since, 1)
            else:
                self._close(name, stage, now)
        return dict(self.demand)

    def _open(self, name, stage, since, now, cores, allowance, share, demand):
        slowest = demand.get('slowest')
        record = {'time': round(self.wall(), 3), 'stage': name, 'cores_used': round(cores, 2),
                  'allowed': allowance, 'share': share, 'queued': demand.get('queued'),
                  'running': demand.get('running'), 'slowest': {'unit': slowest[0], 'seconds': slowest[1]}
                  if slowest else None, 'since_seconds': round(now - since, 1),
                  'held_by': 'memory guard' if allowance < share else 'stage (its pools run fewer units than allowed)',
                  'key': 'underused:%s' % name}
        # the stage's phase running now (build_profile.phase, the stage's own timer): which step the cores wait in
        # (BUILD-IMAGE-FINALIZE-UNDERUSED-48: the record named no sub-step and was read as the player view's)
        current = self.phase_of(stage)
        record['phase'] = current.get('name') if current else None
        if current and current.get('started_at') is not None:
            record['phase_seconds'] = round(max(0.0, self.wall() - float(current['started_at'])), 1)
        stage['open'] = record
        self.occurrences.append(record)
        self.log('[underused] WARNING: %s ran on %.1f of %d cores (allowance %d, share %d) for %.0f s with %s units '
                 'queued and %d running; slowest running unit: %s; phase now: %s; held by: %s; the build carries on '
                 '(%s)' % (
                     name, cores, max(allowance, share), allowance, share, now - since,
                     'more' if record['queued'] is None else record['queued'], record['running'] or 0,
                     '%s (%.0f s)' % (slowest[0], slowest[1]) if slowest else 'none named',
                     '%s (running %.0f s)' % (record['phase'], record.get('phase_seconds', 0)) if record['phase']
                     else 'none named', record['held_by'], self.run / FILE))
        try:
            with (self.run / FILE).open('a', encoding='utf-8', newline='\n') as out:
                out.write(json.dumps(record) + '\n')
        except OSError:
            pass

    def phase_of(self, stage):
        """The stage's current phase ({name, started_at, ...}, build_profile.read_now) or None. The stage's sections
        file is RUN/profile/sections/<NN-name>.jsonl, the name of its allowance file (build_parallel)."""
        try:
            import build_profile
            return build_profile.read_now(self.run / 'profile' / 'sections' / (Path(stage['file']).name + '.jsonl'))
        except (ImportError, OSError, TypeError, ValueError):
            return None

    def _close(self, name, stage, now):
        if stage.get('open') is not None and stage.get('under_since') is not None:
            stage['open']['seconds'] = round(now - stage['under_since'], 1)
        stage['open'] = None

    def summary(self, name):
        """{'cores_mean', 'allowed_mean', 'under_half_longest_seconds', 'underused'} of one stage, or None."""
        stage = self.stages.get(name)
        if stage is None or not stage['watched_seconds']:
            return None
        watched = stage['watched_seconds']
        return {'cores_mean': round(stage['cpu_seconds'] / watched, 2),
                'allowed_mean': round(stage['allowed_seconds'] / watched, 2),
                'watched_seconds': round(watched, 1),
                'under_half_longest_seconds': round(stage['under_longest'], 1),
                'underused': [o for o in self.occurrences if o['stage'] == name]}


def lend_shares(shares, demand):
    """SHARES {stage: workers} of the pooled stages after the even split; DEMAND {stage: pool status or None}.
    The workers a stage with nothing queued does not run go, on loan, to the stages with queued units, evenly, so
    the free cores go where the work is. The idle stage keeps its own share (a pass it starts next still sizes itself
    on it: build_parallel.live_jobs); the loan ends at the scheduler's next look once that stage queues units again,
    so the budget is exceeded at most by the borrowers' running units, for a moment. Unknown demand (no status file)
    neither lends nor borrows. Returns the new {stage: workers}."""
    idle = [n for n in sorted(shares) if demand.get(n) is not None and not demand[n].get('more')]
    busy = [n for n in sorted(shares) if demand.get(n) is not None and demand[n].get('more')]
    if not idle or not busy:
        return dict(shares)
    spare = sum(max(0, shares[n] - max(1, int(demand[n].get('running') or 0))) for n in idle)
    result = dict(shares)
    base, extra = divmod(spare, len(busy))
    for index, name in enumerate(busy):
        result[name] += base + (1 if index < extra else 0)
    return result
