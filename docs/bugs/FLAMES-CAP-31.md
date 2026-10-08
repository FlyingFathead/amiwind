# FLAMES-CAP-31: Static flames above 128 per map are silently dropped

## Status: 8 October 2026

Open. Found by the whole-world measurement (every object placed, estimated per map, checked on 30 converted maps).

## Symptom

The static flame list holds 128 flames; extra flames are ignored without a message. 12
Vvardenfell and 3 Bloodmoon interiors exceed it (Falasmaryon Upper Level 285, Telasero
Upper Level 263, Yakin 243, Ainab 191, Subdun 188).

## Where

`engine/aga/src/aw_guard_torch.c` (static flame list).

## How it happened

A fixed list size.

## Why it was not caught

No converted map reached it.

## Reproduction

Count flame sources in Falasmaryon Upper Level.

## Repair

Not yet: keep the nearest flames, or raise the cap within the heap budget, and report drops.

## Verification

Pending.

## Prevention

The builder reports flames per map against the cap.
