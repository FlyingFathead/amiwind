# NIGHT-0400-DARK-31: exterior suddenly much darker around 04:00

## Status: 7 October 2026

Open. Owner report on v0.0.31-dev4; cause unknown.

## Symptom

Walking through Balmora at night, the scene suddenly turns much darker at
about 04:00 in-game.

## Where

Unknown. Candidates: the night lamps' on/off rule (`engine/aga/src/aw_lamps.c`,
`lamp_night`), the guard torch night (06:00 end), or a step in the day/night
light tables (`engine/aga/src/r_sky.c`).

## How it happened

Unknown.

## Why it was not caught

The night captures used fixed times (21:38, 22:21, 23:18, 01:19); no sweep over
the pre-dawn hours.

## Reproduction

v0.0.31-dev4, Balmora exterior, from 03:30 to 04:30 in-game.

## Repair

Not yet. Measuring first: same pose every 10 minutes from 03:30 to 04:30 on
dev4 and the dev5 engine, with `dbg lamps` at each step.

## Verification

Pending.

## Prevention

Time sweeps across dusk and dawn in the night capture set.
