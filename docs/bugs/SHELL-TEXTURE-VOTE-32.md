# SHELL-TEXTURE-VOTE-32: Distant shells: door and grille textures win over large sealed areas

## Status: 8 October 2026

Open. Prototype only (tools/mold_shell.py, not in the game).

## Symptom

Each shell face takes the most common texture of nearby original faces; door and grille
textures win over large sealed areas, visibly in the day and night frames.

## Where

`tools/mold_shell.py` (texture vote).

## How it happened

The vote counts faces, not visible area.

## Why it was not caught

First prototype.

## Reproduction

Build shells for bm019 and compare the frames.

## Repair

Weight the vote by area and exclude door and opening textures from sealed areas.

## Verification

Pending.

## Prevention

Frame comparison in the shell tests.
