# CHIM-ANIM-TEXTURES-33: Animated shared textures in CHIM show only their first frame

## Status: 8 October 2026

Open. Found by the first CHIM engine slice (branch v0.0.33-chim-engine).

## Symptom

Animated (`+`) textures in the shared CHIM texture pool are not linked into sequences, so they show their
first frame only.

## Where

CHIM texture loading.

## How it happened

Sequence linking happens per model in `Mod_LoadTextures`.

## Why it was not caught

First CHIM engine slice; host tests only, no emulator run yet.

## Reproduction

A placement with an animated texture.

## Repair

Not yet: link sequences across the shared pool.

## Verification

Pending.

## Prevention

A host test with an animated texture.
