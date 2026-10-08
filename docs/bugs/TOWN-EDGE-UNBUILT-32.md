# TOWN-EDGE-UNBUILT-32: Leaving a town into an unbuilt neighbour drops the player into a bare world map

## Status: 8 October 2026

Open. Found by the Vivec cantons import.

## Symptom

Walking off a canton bridge into a neighbour that is not installed drops the player into an
open-world terrain map without the Vivec structures; doors into towns that are blocked or not
opted in say "Interior not found" (no crash).

## Where

Town handoff (`aw_world.c`) and door targets.

## How it happened

Partial town sets were never installed together before.

## Why it was not caught

First multi-town city.

## Reproduction

Install one canton and walk off a bridge.

## Repair

Not yet: block or warn at frame edges toward uninstalled towns, or install cantons as a set.

## Verification

Pending.

## Prevention

Builder check of town sets with shared edges.
