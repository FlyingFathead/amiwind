# SPDX-License-Identifier: GPL-3.0-only
"""The player view's 80 units as one flow over the worker pool (BUILD-PLAYER-VIEW-UNDERUSED-48, NPC-BAKE-FALLBACK-62).

The v0.0.62 release build's player view ran 24 cores for about 15 minutes, 11-12 from 37 minutes, 7 after 63 minutes
and 1 core for its last 25 minutes: each body ran every fitting try of its body one after the other on one core (the
whole hair share, the plain share, the previous head reducer, then the same again with the v0.0.62-dev1 body rules),
and the torch bodies waited in a second map for the slowest body. Three changes, none of them in the bake code (the
units' key, the bake-reach digest of bake_unit, stays what it was, and every result is byte for byte what
prepare_player_view.bake_unit makes):

1. One flow: the torch body of a race starts the moment its body is done (no second map).
2. The fitting tries of one body are units of their own (fit_tries: the exact order prepare_player_view._fit_body and
   _fit_body_rules try them, each with the settings that try runs under). The first try of every body runs first; a
   worker with nothing else to do starts the next try of a body still running (the tail gets the cores). A body's
   result is the first try, in that order, that fits: a later try that finished earlier waits for the earlier ones
   to say "no fit"; tries after the one that fits are dropped.
3. The try that fitted is kept in the unit cache beside the body (fit_inputs), under the same key as the body unit
   (code, settings, game data, race, sex, palette): the next build that bakes that body with the same code starts at
   that try (a body known not to fit the new rules goes straight to its fallback), the earlier tries are known not
   to fit.

Each try is the body bake with prepare_player_view._fit_body replaced, in the worker only, by one _fit_body_search
under that try's settings. That stands for _fit_body only while _fit_body and _fit_body_rules are the code this module
was written against (FIT_SOURCES_SHA256); when they change, every body runs whole as before (split_ok) until this
module is brought up to date (tests/test_player_view_schedule.py fails first).
"""
import hashlib
import heapq
import inspect
import os
import time
from contextlib import contextmanager

LABEL = 'Player view'
AHEAD = 6           # how many tries past a body's current try an idle worker may start
# a body's try in order that waits stops the furthest speculative try: off, it made no difference on the release
# build's unit times (tests/test_player_view_schedule.py) and loses the stopped try's work
PREEMPT = False
NO_FIT = 'no body fits the existing budgets'
HAIR_VARIABLE = 'AMIWIND_NPC_HAIR_SHARE'
# SHA-256 of the source of prepare_player_view._fit_body + _fit_body_rules that fit_tries() follows
FIT_SOURCES_SHA256 = 'de34b5af93a5eeba67bd97e2fcfe5bc93cec0b5da540aa6f6890b8bc6481ec1f'


class NoFit:
    """A fitting try that found no body (picklable: the message only)."""

    def __init__(self, message):
        self.message = message


class Failed:
    """A unit's error, returned instead of raised (picklable: the message only)."""

    def __init__(self, message):
        self.message = message


class _NoFitSignal(Exception):
    pass


def fit_sources_digest():
    import prepare_player_view as view
    text = inspect.getsource(view._fit_body) + inspect.getsource(view._fit_body_rules)
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def split_ok():
    """True while _fit_body and _fit_body_rules are the code fit_tries() follows."""
    try:
        return fit_sources_digest() == FIT_SOURCES_SHA256
    except (OSError, TypeError):
        return False


@contextmanager
def applied(overrides):
    """The environment with OVERRIDES ((name, value), ...) set, restored afterwards."""
    saved = {name: os.environ.get(name) for name, _ in overrides}
    os.environ.update(dict(overrides))
    try:
        yield
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def fit_tries():
    """Every fitting try of _fit_body in its order, as the settings each runs _fit_body_search under:
    _fit_body_rules (on no fit: the plain hair share and _fit_body_rules again; with the plain share, the previous
    head reducer once), then, unless the settings already are the dev1 body rules, the same under them."""
    from mesh_geometry_env import NPC_HEAD_REDUCER_VARIABLE, npc_head_reducer
    from npc_geometry import DEV1_BODY_RULES, hair_share

    def rules(env):
        with applied(env):
            hair, head = hair_share(), npc_head_reducer()
        if hair != 'plain':
            return [env] + rules(env + ((HAIR_VARIABLE, 'plain'),))
        if head == 'locked':
            return [env, env + ((NPC_HEAD_REDUCER_VARIABLE, 'default'),)]
        return [env]

    tries = rules(())
    if not all(os.environ.get(k) == v for k, v in DEV1_BODY_RULES.items()):
        tries += rules(tuple(sorted(DEV1_BODY_RULES.items())))
    return tries


def fit_once(env, identifier, *args):
    """One fitting try: prepare_player_view._fit_body_search under the settings ENV; no fit raises _NoFitSignal."""
    import prepare_player_view as view
    with applied(env):
        try:
            return view._fit_body_search(identifier, *args)
        except ValueError as error:
            if NO_FIT in str(error):
                raise _NoFitSignal(str(error))
            raise


def bake_try(work):
    """Pool worker: WORK (index, try, settings, unit) -> (index, try, seconds, result). TRY None: the whole unit
    (prepare_player_view.bake_unit); else the body bake with its fitting done by one _fit_body_search under SETTINGS.
    RESULT: the unit's result, NoFit or Failed."""
    import prepare_player_view as view
    index, number, env, unit = work
    began = time.monotonic()
    original = view._fit_body
    try:
        if number is not None:
            view._fit_body = lambda identifier, *args: fit_once(env, identifier, *args)
        result = view.bake_unit(unit)
    except _NoFitSignal as error:
        result = NoFit(str(error))
    except Exception as error:   # collected and named; every other unit is kept
        result = Failed('%s: %s' % (type(error).__name__, error))
    finally:
        view._fit_body = original
    return index, number, round(time.monotonic() - began, 3), result


def try_name(name, number):
    """The cost-history name of one fitting try: the body's own name for the first."""
    return name if not number else '%s try%d' % (name, number + 1)


class Planner:
    """Which unit or fitting try a free worker takes next. Units: index -> name; a body's tries are numbered from
    START (a try known to fit from the unit cache) to TRIES - 1. Ready work goes longest first by COST(name); a free
    worker with nothing ready starts the next try of a body still running (speculation), the body expected to take
    longest first."""

    def __init__(self, cost, ahead=AHEAD, likely=lambda name: False):
        self.cost, self.ahead, self.likely = cost, ahead, likely
        self.preempting = PREEMPT
        self.ready = []            # heap of (-seconds, seq, index, try)
        self.seq = 0
        self.names = {}
        self.bodies = {}           # index -> {'tries': n, 'current': k, 'results': {}, 'started': set()}
        self.running = {}          # (index, try) -> started
        self.open = set()          # units not decided yet

    def _push(self, index, number, first=False):
        name = try_name(self.names[index], number or 0)
        self.seq += 1
        heapq.heappush(self.ready, (float('-inf') if first else -self.cost(name), self.seq, index, number))

    def add(self, index, name, tries=None, start=0):
        """A unit to make; TRIES: a body run as its fitting tries (None: the whole unit)."""
        self.names[index] = name
        self.open.add(index)
        if tries is not None:
            self.bodies[index] = {'tries': tries, 'current': start, 'results': {}, 'started': {start}}
            # the tries an earlier build ran for this body (self.likely) go out at once beside the first, longest
            # first like every unit
            for number in range(start + 1, tries):
                if self.likely(try_name(name, number)):
                    self.bodies[index]['started'].add(number)
                    self._push(index, number)
        self._push(index, start if tries is not None else None)

    def take(self):
        """The next (index, try) to start, or None: a body's try in order first; then the longer of the next ready
        unit and the next try of a running body (one past its current try: a body's tries are the longest work of
        the step, so they go before the short units); deeper tries only when nothing else is ready."""
        while self.ready and self.ready[0][2] not in self.open:
            heapq.heappop(self.ready)
        if self.ready:
            guess = self._speculative(likely=True)
            if guess is None or self.ready[0][0] == float('-inf') or -self.ready[0][0] >= guess[0][1]:
                _, _, index, number = heapq.heappop(self.ready)
                self.running[(index, number)] = True
                return index, number
        else:
            guess = self._speculative()
        if guess is None:
            return None
        _, index, number = guess
        self.bodies[index]['started'].add(number)
        self.running[(index, number)] = True
        return index, number

    def _speculative(self, likely=False):
        """((-depth, seconds), index, try) of the try an idle worker would start next (LIKELY: only a try one past
        its body's current one that self.likely names), or None."""
        best = None
        for index, body in self.bodies.items():
            if index not in self.open:
                continue
            following = [k for k in range(body['current'] + 1, min(body['tries'], body['current'] + 1 + self.ahead))
                         if k not in body['started']]
            if likely:
                following = [k for k in following if self.likely(try_name(self.names[index], k))]
            if not following:
                continue
            # breadth first: the nearest try ahead of any body (the likeliest to be needed), then the body expected
            # to take longest
            rank = (-(following[0] - body['current']), self.cost(try_name(self.names[index], following[0])))
            if best is None or rank > best[0]:
                best = (rank, index, following[0])
        return best

    def done(self, index, number, result):
        """A unit or try came back. Returns ('kept', result, try) when the unit is decided with a result,
        ('failed', message, try) when it failed, ('try', message, try) when a body's try in order found no fit and the
        next one is under way, or None (a try out of order, or after its body was decided)."""
        self.running.pop((index, number), None)
        if index not in self.open:
            return None
        if number is None:
            self.open.discard(index)
            if isinstance(result, (Failed, NoFit)):
                return 'failed', result.message, None
            return 'kept', result, None
        body = self.bodies[index]
        body['results'][number] = result
        event = None
        while body['current'] in body['results']:
            found = body['results'][body['current']]
            if isinstance(found, NoFit):
                if body['current'] + 1 >= body['tries']:
                    self.open.discard(index)
                    return 'failed', 'ValueError: ' + found.message, body['current']
                event = ('try', found.message, body['current'])
                body['current'] += 1
                continue
            self.open.discard(index)
            if isinstance(found, Failed):
                return 'failed', found.message, body['current']
            return 'kept', found, body['current']
        if body['current'] not in body['started']:
            body['started'].add(body['current'])
            self._push(index, body['current'], first=True)
        return event

    def orphans(self):
        """Tries still running for bodies already decided (to be stopped), taken off the running list."""
        found = [key for key in self.running if key[0] not in self.open]
        for key in found:
            self.running.pop(key)
        return found

    def waiting(self):
        """A body's next try in order is waiting for a worker (a short unit waits for the next free one instead:
        stopping a long try for it loses more than it saves)."""
        return any(index in self.open and seconds == float('-inf') for seconds, _, index, _ in self.ready)

    def preempt(self):
        """With work waiting and every worker busy: the speculative try to stop for it (the one furthest past its
        body's current try), taken off the running list so it can start again later; None when there is none."""
        if not self.preempting or not self.waiting():
            return None
        victims = [(number - self.bodies[index]['current'], -self.cost(try_name(self.names[index], number)),
                    (index, number)) for index, number in self.running
                   if number is not None and index in self.open and number > self.bodies[index]['current']]
        if not victims:
            return None
        key = max(victims)[2]
        self.running.pop(key)
        self.bodies[key[0]]['started'].discard(key[1])
        return key


def fit_inputs(view, unit):
    """The unit-cache inputs under which a body's fitting try is kept: the body unit's inputs as a 'fit' entry."""
    inputs = dict(view.unit_inputs(unit))
    inputs['kind'] = 'fit'
    inputs['entry'] = {'name': 'fit ' + view.unit_name(unit)}
    return inputs


def known_try(view, cache, unit, tries):
    """The try known to fit this body (unit cache, same code and settings), or 0."""
    from pass_cache import forced
    if cache is None or forced(view.UNIT_CACHE, view.unit_name(unit)):
        return 0
    found = cache.load_unit(fit_inputs(view, unit))
    if found is None:
        return 0
    row = found[0]
    try:
        number = int(row['try'])
        if row['tries'] == [[list(pair) for pair in env] for env in tries] and 0 <= number < len(tries):
            return number
    except (KeyError, TypeError, ValueError):
        pass
    return 0


class _Here:
    """The executor of a unit run in this process (one worker: the serial path, as the pool maps run one)."""

    _processes = {}

    def shutdown(self, wait=True, cancel_futures=False):
        pass


def _start(work, serial=False):
    """bake_try(WORK) in a process of its own (the builder's spawn pool of one worker), so that a try no longer
    needed can be stopped without touching the other units (_end). Starting a process costs a few seconds next to
    units of 40 s to 80 min. SERIAL: in this process, done when this returns."""
    from concurrent.futures import Future
    if serial:
        future = Future()
        future.set_result(bake_try(work))
        future._aw_executor = _Here()
        return future
    from build_parallel import process_pool
    executor = process_pool(1)
    future = executor.submit(bake_try, work)
    future._aw_executor = executor
    return future


def _end(future):
    """Stop the process of a unit started by _start (its result is not needed)."""
    executor = future._aw_executor
    for process in list((getattr(executor, '_processes', None) or {}).values()):
        try:
            process.terminate()
        except (OSError, AttributeError):
            pass
    executor.shutdown(wait=False, cancel_futures=True)


def run_view(tasks, swim_tasks, cache, jobs, log=print):
    """The player view's units: the bodies, water bodies and inventory poses of TASKS, and each body's torch body the
    moment its body is done. Returns (results of the bodies + water + inventory units in that order, the torch
    results in body order, how many came from the unit cache). Every unit is kept in CACHE the moment it is back."""
    from concurrent.futures import FIRST_COMPLETED, wait
    import build_costs
    from build_jobs import resolve_jobs
    from build_parallel import _throttle, worker_environment
    import prepare_player_view as view
    count = len(tasks)
    units = [('body', t) for t in tasks] + [('swim', t) for t in swim_tasks] + [('inventory', t) for t in tasks]
    units += [None] * count                         # the torch units, made when their body is done
    results = [None] * len(units)
    history = build_costs.load(view.UNIT_COSTS)

    def cost(name):
        # a try not timed yet counts as long as its body's first try (before the split: the whole body)
        base = name.split(' try')[0]
        return history.get(name, history.get(base, view.UNIT_FALLBACK_SECONDS.get(base.split(' ', 1)[0], 30.0)))

    split = split_ok()
    tries = fit_tries() if split else None
    if not split:
        log('%s: the body fitting code changed since the try split was written (player_view_schedule.'
            'FIT_SOURCES_SHA256): every body runs whole' % LABEL, flush=True)
    # a try that ran in an earlier build (it is in the cost history) is likely needed again: it goes before the short
    # units; any other try only on a worker with nothing else to do
    size, limit = _throttle(max(1, resolve_jobs(jobs)))
    planner = Planner(cost, AHEAD if size > 1 else 0,
                      likely=lambda name: size > 1 and ' try' in name and name in history)
    reused, failed, seconds, finished = [0], [], {}, [0]
    total = len(units)

    def cached(index):
        from pass_cache import forced
        unit = units[index]
        if cache is None or forced(view.UNIT_CACHE, view.unit_name(unit)):
            return False
        found = cache.load_unit(view.unit_inputs(unit))
        if found is None:
            return False
        try:
            results[index] = view.unpack_result(*found)
        except (KeyError, TypeError, AttributeError):
            return False
        reused[0] += 1
        return True

    def keep(index, result):
        if cache is not None:
            packed = view.pack_result(result)
            if packed is not None:
                cache.store_files(view.unit_inputs(units[index]), *packed)
        results[index] = result

    def body_done(index):
        # the torch body of this race starts now (it reads the body row's model path and frame groups)
        row = {k: v for k, v in results[index][3].items() if k != '_item_tags'}
        data, palette, race, female = tasks[index]
        torch = 3 * count + index
        units[torch] = ('torch', (data, palette, race, female, row))
        if cached(torch):
            finished[0] += 1
        else:
            planner.add(torch, view.unit_name(units[torch]))

    for index in range(3 * count):
        if cached(index):
            continue
        if index < count and split:
            start = known_try(view, cache, units[index], tries)
            if start:
                log('%s: %s starts at fitting try %d of %d (the earlier ones are known not to fit)'
                    % (LABEL, view.unit_name(units[index]), start + 1, len(tries)), flush=True)
            planner.add(index, view.unit_name(units[index]), len(tries), start)
        else:
            planner.add(index, view.unit_name(units[index]))
    for index in range(count):
        if results[index] is not None:
            body_done(index)
    log('%s [%d/%d] cached, %d to make' % (LABEL, reused[0], total, total - reused[0]), flush=True)
    from unit_store import progress_line
    finished[0] = reused[0]
    if planner.open:
        log('%s: up to %d units and fitting tries at once, one process each (a try no longer needed is stopped '
            'at once)' % (LABEL, size), flush=True)
        with worker_environment():
            pending = {}
            try:
                while planner.open:
                    room = max(1, limit() if limit is not None else size)
                    while True:
                        if len(pending) >= room:
                            victim = planner.preempt()
                            if victim is None:
                                break
                            for future, key in list(pending.items()):
                                if key == victim:
                                    _end(future)
                                    pending.pop(future)
                        nxt = planner.take()
                        if nxt is None:
                            break
                        index, number = nxt
                        env = tries[number] if number is not None else ()
                        pending[_start((index, number, env, units[index]), size == 1)] = nxt
                        if size == 1:
                            break
                    if not pending:
                        break
                    done, _ = wait(list(pending), timeout=None if limit is None else 30,
                                   return_when=FIRST_COMPLETED)
                    for future in done:
                        index, number = pending.pop(future)
                        try:
                            _, _, took, result = future.result()
                        except Exception as error:      # the worker died (out of memory, say): this unit failed
                            took, result = 0.0, Failed('worker lost: %s: %s' % (type(error).__name__, error))
                        future._aw_executor.shutdown(wait=True)
                        name = view.unit_name(units[index])
                        if not isinstance(result, Failed):
                            seconds[try_name(name, number or 0)] = took
                        event = planner.done(index, number, result)
                        stopped = planner.orphans()
                        for future2, key in list(pending.items()):
                            if key in stopped:
                                _end(future2)
                                pending.pop(future2)
                        if stopped:
                            log('%s: %s decided: %d of its later fitting tries stopped' % (LABEL, name, len(stopped)),
                                flush=True)
                        if event is None:
                            continue
                        what, value, at = event
                        if what == 'try':
                            log('%s: %s fitting try %d of %d: no fit (%s); try %d next' % (
                                LABEL, name, at + 1, len(tries), ' '.join('%s=%s' % p for p in tries[at]) or
                                'the configured rules', at + 2), flush=True)
                            continue
                        finished[0] += 1
                        log(progress_line(LABEL, finished[0], total, name, took, what == 'failed'), flush=True)
                        if what == 'failed':
                            failed.append('%s: %s' % (name, value))
                            continue
                        keep(index, value)
                        if at is not None:
                            if at:
                                log('BAKE-FALLBACK: player body %s: fitted at try %d of %d (%s)' % (
                                    name, at + 1, len(tries), ' '.join('%s=%s' % p for p in tries[at])),
                                    flush=True)
                            if cache is not None:
                                cache.store_files(fit_inputs(view, units[index]),
                                                  {'try': at, 'tries': [[list(p) for p in env] for env in tries]},
                                                  {})
                        if index < count:
                            body_done(index)
            finally:
                for future in pending:
                    _end(future)
                build_costs.record(view.UNIT_COSTS, list(seconds), list(seconds.values()))
    if failed:
        raise ValueError('; '.join(failed) + ' (%d units failed; the finished ones are kept in the unit cache)'
                         % len(failed))
    return results[:3 * count], results[3 * count:], reused[0]


# ---------------------------------------------------------------- the schedule on recorded unit times (no bake)

def simulate(planner_units, workers, seconds, fits, ahead=AHEAD, likely=lambda name: False):
    """Run Planner as run_view does, on recorded times: PLANNER_UNITS [(index, name, tries or None, start, then)]
    (THEN: the index of a unit added when this one is kept, or None); SECONDS(name, try) -> seconds; FITS(index, try)
    -> True when that try fits. A try stopped (its body decided, or preempted) frees its worker at once. Returns
    (makespan seconds, busy core-seconds, [(time, busy workers)])."""
    by_index = {u[0]: u for u in planner_units}
    added = {u[4] for u in planner_units if u[4] is not None}
    planner = Planner(lambda name: seconds(name, None), ahead, likely)
    for index, name, tries, start, _ in planner_units:
        if index not in added:
            planner.add(index, name, tries, start)
    clock, busy, running, trace = 0.0, 0.0, {}, []
    simulate.decided = {}

    def stop(key):
        nonlocal busy
        started, _ = running.pop(key)
        busy += clock - started

    while True:
        while True:
            if len(running) >= workers:
                victim = planner.preempt()
                if victim is None:
                    break
                stop(victim)
            nxt = planner.take()
            if nxt is None:
                break
            running[nxt] = (clock, clock + seconds(by_index[nxt[0]][1], nxt[1]))
        trace.append((clock, len(running)))
        if not running or not planner.open:
            break
        key = min(running, key=lambda k: running[k][1])
        clock = running[key][1]
        stop(key)
        index, number = key
        result = object() if number is None or fits(index, number) else NoFit('no fit')
        event = planner.done(index, number, result)
        if event and event[0] != 'try':
            simulate.decided[by_index[index][1]] = clock
        for orphan in planner.orphans():
            stop(orphan)
        if event and event[0] == 'kept' and by_index[index][4] is not None:
            then = by_index[by_index[index][4]]
            planner.add(then[0], then[1], then[2], then[3])
    for key in list(running):
        stop(key)
    return clock, busy, trace


def simulate_maps(first, torch, workers):
    """The method before the flow: the bodies, water and inventory units [(name, seconds)] in one map longest first,
    then the torch bodies in a second map. Returns (makespan seconds, busy core-seconds)."""
    def one_map(items):
        free = [0.0] * workers
        for _, took in sorted(items, key=lambda item: -item[1]):
            start = heapq.heappop(free)
            heapq.heappush(free, start + took)
        return max(free)
    return one_map(first) + one_map(torch), sum(t for _, t in first) + sum(t for _, t in torch)
