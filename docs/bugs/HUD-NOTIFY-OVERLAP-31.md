# HUD-NOTIFY-OVERLAP-31: console messages print over the location title

## Status: 7 October 2026

Open. Cause read in source; no repair yet.

## Symptom

With the debug overlay on, a console message such as the heap audit line
("Heap maps/bm026.bsp first-presented: ...") appears at the top of the screen
on top of the "AmiWind v... Vvardenfell / ..." title; both become unreadable
for a few seconds (owner screenshot, Balmora, 17:15).

Seen again in v0.0.31-dev3 with the autosave message ("Saved Autosave 2 ...")
over the title in Seyda Neen.

## Where

Quake's console notify lines (recent `Con_Printf` output shown at the top of the
view for a few seconds) and the AmiWind debug title (`aw_hud.c`, drawn at the
top-left). The heap audit message comes from `aw_stream.c` on the first frame
of a new map.

## How it happened

Both draw in the same rows at the top of the screen; neither knows about the
other.

## Why it was not caught

The heap audit message appears only on the first frame of a map, and captures
are usually taken later.

## Reproduction

Debug overlay on; cross into a new region map and look at the top of the screen.

## Repair

Not done: move the notify lines below the title while the overlay is on, or
send debug-only messages to the console without the on-screen notify.

## Verification

Pending.

## Prevention

Pending.
