# TOOL-SIMPLIFY-MANIFOLD-32: Mesh reduction can return open or non-manifold meshes

## Status: 8 October 2026

Open. Found by the distant shell prototype; effect on current users not yet checked.

## Symptom

`fast_simplification` (quadric reduction) returned non-manifold or open meshes when
reducing a closed house shell to 48 triangles. The builder uses it for NPC models
(`npc_geometry.py`), `prepare_quake.py` and `static_lod.py`.

## Where

`fast-simplification` 0.2.0 as used by the tools above.

## How it happened

Aggressive targets on small closed meshes.

## Why it was not caught

The existing users do not check that output stays closed.

## Reproduction

Reduce a closed voxel house to 48 triangles.

## Repair

Not yet: check closedness after every reduction in the existing users and report or fall back;
the shell tool uses its own closed-mesh reducer.

## Verification

Pending.

## Prevention

A closed-mesh check after reduction in the builder.
