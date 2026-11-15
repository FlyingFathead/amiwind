#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""A small catcher for the builder's status folder (docs/BUILD_STATUS.md), standard library only.

    python3 tools/stall_watch.py RUN_DIR [--on-stall COMMAND] [--max-age SECONDS] [--exit-on-stall] [--once]

It follows RUN_DIR/status/stall.jsonl (one line per stall incident) and the age of RUN_DIR/status/heartbeat.json. A
heartbeat older than --max-age (default 120 s) while the build has not finished means the builder itself is stuck or
gone: that is an incident too. Each incident is printed once and, with --on-stall, COMMAND runs once with the state
and the reason as its last two arguments. --exit-on-stall exits 3 at the first incident (a user's loop or CI wakes on
it); --once reads what is there now and exits (0 nothing, 3 an incident). RUN_DIR may also be the status folder.
"""
import argparse
import json
import shlex
import subprocess
import sys
import time
from pathlib import Path

STALL_EXIT = 3
FINISHED = ('passed', 'failed', 'stopped', 'interrupted', 'cancelled', 'checked')


def status_dir(run):
    run = Path(run)
    return run if (run / 'heartbeat.json').exists() or run.name == 'status' else run / 'status'


class Catcher:
    def __init__(self, run, max_age=120.0, on_stall=None, runner=None, stream=None, clock=time.time):
        self.dir = status_dir(run)
        self.max_age = max_age
        self.on_stall = list(on_stall or [])
        self.runner = runner or (lambda argv: subprocess.run(argv, timeout=120))
        self.stream = stream or sys.stdout
        self.clock = clock
        self.offset = 0
        self.stale_said = None

    def heartbeat(self):
        try:
            return json.loads((self.dir / 'heartbeat.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return None

    def new_lines(self):
        """Complete new lines of stall.jsonl (a line still being written waits for the next read)."""
        path = self.dir / 'stall.jsonl'
        try:
            with open(path, 'rb') as f:
                f.seek(self.offset)
                data = f.read()
        except OSError:
            return []
        end = data.rfind(b'\n') + 1
        self.offset += end
        out = []
        for raw in data[:end].splitlines():
            try:
                out.append(json.loads(raw.decode('utf-8')))
            except ValueError:
                continue
        return out

    def incident(self, state, reason, record=None):
        print('[stall-watch] %s: %s%s' % (state, reason, ('; resume: ' + record['resume'])
                                          if record and record.get('resume') else ''), file=self.stream, flush=True)
        if self.on_stall:
            try:
                self.runner(self.on_stall + [state, reason])
            except (OSError, subprocess.SubprocessError) as exc:
                print('[stall-watch] --on-stall failed: %s' % exc, file=self.stream, flush=True)

    def check(self):
        """Returns the incidents found now: [(state, reason)]."""
        found = []
        for record in self.new_lines():
            reason = '%s: %s' % (record.get('stage') or 'build', record.get('reason') or '')
            self.incident(record.get('state') or 'stalled', reason, record)
            found.append((record.get('state'), reason))
        beat = self.heartbeat()
        if beat and beat.get('status') not in FINISHED:
            age = self.clock() - float(beat.get('written_epoch') or 0)
            if age > self.max_age:
                if self.stale_said != beat.get('written_epoch'):
                    self.stale_said = beat.get('written_epoch')
                    reason = ('the heartbeat is %d s old (limit %d s): the builder itself is stuck or gone (last phase: %s)'
                              % (age, self.max_age, beat.get('phase')))
                    self.incident('no-heartbeat', reason)
                    found.append(('no-heartbeat', reason))
            else:
                self.stale_said = None
        return found


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('run')
    p.add_argument('--on-stall', default='', metavar='COMMAND')
    p.add_argument('--max-age', type=float, default=120.0)
    p.add_argument('--exit-on-stall', action='store_true')
    p.add_argument('--once', action='store_true')
    p.add_argument('--interval', type=float, default=5.0)
    a = p.parse_args(argv)
    catcher = Catcher(a.run, a.max_age, shlex.split(a.on_stall) if a.on_stall else None)
    print('[stall-watch] watching %s' % catcher.dir, flush=True)
    while True:
        found = catcher.check()
        if found and (a.exit_on_stall or a.once):
            return STALL_EXIT
        if a.once:
            return 0
        beat = catcher.heartbeat()
        if beat and beat.get('status') in FINISHED:
            print('[stall-watch] the build finished: %s' % beat.get('status'), flush=True)
            return 0
        time.sleep(a.interval)


if __name__ == '__main__':
    sys.exit(main())
