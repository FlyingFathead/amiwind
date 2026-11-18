# SPDX-License-Identifier: GPL-3.0-only
"""The placed containers that open, for Seyda Neen's CHIM frame (SEYDA-CONTAINERS-NOT-DRAWN-67).

Seyda Neen's frame takes its placements from the town scene's scenery selection (tools/scenery_selection.py
select_source_refs: statics and doors, and named groups), which left every container out: the crates and barrels by the
census office, the chests and sacks on the shore were never drawn, so none could be opened. Every other town and region
of the CHIM world draws its containers. The frame (tools/chim/seyda.py open_container_refs) adds the containers that
open: a CONT record with a name that is not organic (an organic one, a plant, stays with the harvest,
tools/prepare_harvest.py). Its own module, so the stages that read scenery_selection.py or prepare_scenery.py (the
residents' bake among them) keep their keys.
"""
import struct

CONT_ORGANIC = 1     # the CONT record's FLAG bit 0 (tools/prepare_focus.py CONT_ORGANIC)


def open_container_ids(raw):
    """{folded record id} of every live CONT record of the master RAW (merged or not) that has a name and is not
    organic."""
    from mwad.esm import records, subrecords, string, first
    out = set()
    for tag, flags, payload in records(raw):
        if tag != 'CONT' or flags & 0x20:
            continue
        fields = list(subrecords(payload))
        if any(k == 'DELE' for k, _ in fields):
            continue
        name = first(fields, 'FNAM')
        flag = first(fields, 'FLAG')
        if not name or not string(name, 'FNAM', errors='replace').strip():
            continue
        if len(flag) >= 4 and struct.unpack_from('<I', flag)[0] & CONT_ORGANIC:
            continue
        out.add(string(first(fields, 'NAME'), 'NAME', errors='replace').casefold())
    return frozenset(out)


def data_open_container_ids(data_files):
    """open_container_ids of the game data's master (mwad.masters.master_path: the merged master when the expansions
    are selected). Record ids only: the models are read through the layered archives (prepare_scenery.export_refs)."""
    from mwad.masters import master_path
    return open_container_ids(master_path(data_files).read_bytes())
