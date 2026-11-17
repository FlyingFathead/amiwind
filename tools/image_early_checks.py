#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""The image step's actor frames check, run on the room batches' own output before the image step
(BUILD-IMAGE-CHECKS-EARLY-66): entries of the builder's early checks (tools/build_preflight.py EARLY_CHECKS).

The image step's payload pre-flight checks every placed actor model's frame layout (tools/actor_frames.py
audit_payload); in v0.0.66-dev2 it stopped the image, at the end of a full build, on Dagoth Ur's idle span in a room
(DAGOTH-IDLE-BASE-CHECK-66). The room batches stage's own output (RUN/chim-room-batches/id1: the room maps and their
resident models, 1,909 models in the v0.0.66 release build) is a payload of its own the same check reads in seconds:

- room_actor_frames (phase stored): the stage is taken from an earlier run: its stored output, before the first stage;
- room_actor_frames_after (phase after:chim-room-batches): the stage is made by this build: its output, the moment it
  has passed (tools/build_preflight.py after_stage_problems, called by the stage scheduler), before the stages after it.

Not run early (measured on the v0.0.66 release build, 17 November 2026): the image's checks on the payload a finished
run keeps (RUN/image/boot/id1) are not the image's own view, as the image step re-encodes models and moves files after
them (163 room models missing there, 3 layouts without a model, 2,473 models in a form the ground check does not
read); and the actor ground check on a stage's own output reports every room resident, as the converted standing hull
is declared by the image step's scene (2,164 of them), after it fits the residents on their room collision again.
"""
from pathlib import Path

ROOM_ACTOR_STAGES = ('chim-room-batches',)   # stages whose own id1 holds room maps with their resident models
MAX_TEXT = 1500


def _short(text):
    text = ' '.join(str(text).split())
    return text if len(text) <= MAX_TEXT else text[:MAX_TEXT] + ' ...'


def audit_output(stage_folder):
    """None when STAGE_FOLDER has no id1/maps, [] when its actor frames pass, else [the check's message]."""
    id1 = Path(stage_folder) / 'id1'
    if not (id1 / 'maps').is_dir():
        return None
    from actor_frames import audit_payload
    try:
        audit_payload(id1, ())
    except ValueError as exc:
        return [_short(exc)]
    return []


def room_actor_frames(context):
    """Phase stored: the room stages this build takes from an earlier run, checked on their stored output."""
    problems = []
    for stage in ROOM_ACTOR_STAGES:
        if stage not in context.steps:
            continue
        source = context.reused.get(stage)
        if source is None:
            context.log('  %s: made by this build; its actor frames are checked the moment it has passed' % stage)
            continue
        found = audit_output(Path(source) / stage)
        if found is None:
            context.log('  %s: %s keeps no output to check' % (stage, Path(source).name))
        elif found:
            problems.append('the image step\'s actor frames check (tools/actor_frames.py) fails on the output of %s '
                            'this build takes from %s: %s' % (stage, Path(source).name, found[0]))
        else:
            context.log('  %s: the actor frames of its output (from %s) pass' % (stage, Path(source).name))
    return problems


def room_actor_frames_after(context):
    """Phase after:STAGE: the room stage this build has just made, checked on its output in the run folder."""
    stage = context.phase.split(':', 1)[1]
    found = audit_output(Path(context.run) / stage)
    if found:
        return ['the image step\'s actor frames check (tools/actor_frames.py) fails on the output of %s: %s'
                % (stage, found[0])]
    if found is not None:
        context.log('  %s: the actor frames of its output pass' % stage)
    return []
