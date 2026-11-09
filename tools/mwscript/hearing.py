# SPDX-License-Identifier: GPL-3.0-only
"""A sound's hearing distances from the game settings (gamedata.GameData.sound_range and the voice table's SOUN rows).

Its own small module (BUILD-TABLE-UNITS-REBAKE-63): the voice table (tools/greeting_lut.py) reads only this rule of the
script compiler's game data, and the unit cache keys it on the code it reaches; through gamedata.py every change to
the scripts' game data (a new add-on placement field, say) re-keyed the voice table's unit although its bytes did not
change.
"""


def sound_range(gmst, soun):
    """(min, max) hearing distance of a SOUN record in game units: its bytes times the game settings
    fAudioMinDistanceMult/fAudioMaxDistanceMult, the defaults when both are 0 (rule from OpenMW
    apps/openmw/mwsound/soundbuffer.cpp; the values are the game data's own GMSTs, GMST: {folded name: value})."""
    g = gmst
    lo, hi = (soun['min'], soun['max']) if soun else (0, 0)
    if lo == 0 and hi == 0:
        lo, hi = g.get('faudiodefaultmindistance', 5.0), g.get('faudiodefaultmaxdistance', 40.0)
    lo *= g.get('faudiomindistancemult', 20.0)
    hi *= g.get('faudiomaxdistancemult', 50.0)
    return int(round(lo)), int(round(max(lo, hi)))
