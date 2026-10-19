# SPDX-License-Identifier: GPL-3.0-only
"""Morrowind editor markers: what the game never draws (COLLISION-NC-FLAGS-32).

The one rule every converter path uses, so an editor marker is filtered out at
the builder input, before any mesh is converted or drawn. Decided for the
project, 18 October 2026: editor markers are ignored by default wherever they
are placed; the object itself (a sound or effect emitter) stays as an invisible
record, only its marker shape and that shape's collision go.

The rules follow OpenMW 0.51 (learned from its behaviour, our own code):

- rule from OpenMW components/misc/resourcehelpers.cpp (isHiddenMarker), used by
  apps/openmw/mwworld/scene.cpp (getModel) and mwrender/objectpaging.cpp: the
  placed objects prisonmarker, divinemarker, templemarker and northmarker get no
  model at all; they are positions for game logic only;
- rule from OpenMW components/nifosg/nifloader.cpp (handleNode): a root node
  NiStringExtraData "MRK" marks the model; its geometry whose name starts with
  "tri editormarker" (any case) is not drawn;
- rule from OpenMW components/nifbullet/bulletnifloader.cpp (handleRoot,
  handleGeometry): the same root "MRK" removes geometry named "Tri EditorMarker"
  from collision too; other collision (a RootCollisionNode) stays.

In the base game the MRK models are editormarker.nif (the sound and script
activators), the invisible collision boxes editormarker_box_01/02 and five
particle effects (waterfall mist, Ghostgate particles, volcano steam, Mournhold
water spray, poison steam): their only drawn shape is the marker.

TravelMarker and DoorMarker are editor objects that are never placed in the
masters: door and travel destinations live in the doors' own records.
"""

# rule from OpenMW components/misc/resourcehelpers.cpp isHiddenMarker
HIDDEN_MARKER_IDS = frozenset(('prisonmarker', 'divinemarker', 'templemarker', 'northmarker'))

# The root string that marks an editor-marker model, and the shape-name prefix it hides.
MARKER_STRING = 'MRK'
MARKER_SHAPE_PREFIX = 'tri editormarker'

# A NiStringExtraData stores its string as a 32-bit length and the bytes: a model
# without this byte run cannot carry the MRK flag (a quick test before parsing).
MARKER_BYTES = b'\x03\x00\x00\x00MRK'

# The kinds of invisible marker placements (tools/editor_markers.py marker_kind).
MARKER_KINDS = ('sound emitter', 'effect emitter', 'collision marker', 'script marker', 'marker object', 'hidden marker')


def is_hidden_marker(object_id):
    """True for the placed objects OpenMW never gives a model (isHiddenMarker)."""
    return (object_id or '').casefold() in HIDDEN_MARKER_IDS


def may_carry_marker(raw):
    """False when the NIF bytes cannot hold a root "MRK" string (no parse needed)."""
    return MARKER_BYTES in raw


def is_marker_shape(name, root_marked):
    """True for geometry the game hides: a "Tri EditorMarker..." shape of an MRK model."""
    return bool(root_marked) and (name or '').casefold().startswith(MARKER_SHAPE_PREFIX)


def root_strings(root, string_type):
    """The NiStringExtraData strings on one NIF root node (a PyFFI block)."""
    out = []
    get = getattr(root, 'get_extra_datas', None)
    for extra in (get() if get else []):
        if isinstance(extra, string_type):
            out.append(bytes(extra.string_data).decode('ascii', errors='replace'))
    return out


def root_marked(roots, string_type):
    """True when a root node carries the exact string "MRK" (OpenMW compares it exactly).

    string_type None (a reader without string extra data) means no root strings."""
    if string_type is None:
        return False
    return any(s == MARKER_STRING for root in roots for s in root_strings(root, string_type))
