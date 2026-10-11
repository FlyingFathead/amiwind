# SPDX-License-Identifier: GPL-3.0-only
"""One form for every counted progress line of the builder.

    [done/total work | done/total containers] <stage>: <unit>: <result>

The counters come first so a log reads at a glance how far a stage is. The first counter counts the real work
units (stairs walked, maps optimized, sounds imported); a second one, when there is one, counts what holds them
(frames, maps). Each counter may name its unit: [12034/15415 stairs | 246/273 frames]. Unit and result are optional:
[251/9000 meshes] Mesh census.

Standard library only: every stage may import it.
"""


def counter_text(counter):
    """'done/total' or 'done/total label' of one counter: (done, total) or (done, total, label)."""
    done, total = counter[0], counter[1]
    label = counter[2] if len(counter) > 2 else None
    return '%s/%s%s' % (done, total, ' ' + label if label else '')


def line(stage, unit=None, result=None, *counters):
    """The progress line: [counters] stage[: unit][: result]."""
    text = stage
    if unit is not None:
        text += ': %s' % unit
    if result is not None:
        text += ': %s' % result
    if counters:
        text = '[%s] %s' % (' | '.join(counter_text(c) for c in counters), text)
    return text


def emit(stage, unit=None, result=None, *counters, stream=None):
    """Print the progress line at once (flush: build logs are followed live)."""
    print(line(stage, unit, result, *counters), file=stream, flush=True)
