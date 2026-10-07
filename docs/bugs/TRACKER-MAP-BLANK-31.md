# TRACKER-MAP-BLANK-31: world progress map vanished when the mouse moved over it

## Status: 7 October 2026

Fixed in source before the viewer was first committed; the owner confirmed the
fixed viewer. Never shipped.

## Symptom

The world progress map viewer (then `tools/world_progress.html`, now
`amiwind-toolkit/world-map.html`) drew the island and the cell overlay, then the map
area went blank (owner report, Firefox).

## Where

The viewer's hover tooltip handler (now `amiwind-toolkit/world-map.html`).

## How it happened

The shared `geometry()` helper both computed the cell layout and set the
canvas size. Setting a canvas's size clears it, and the hover handler called
`geometry()` on every mouse move without redrawing, so the first mouse move
over the map erased it. It happens in every browser.

## Why it was not caught

The first check was a screenshot without moving the mouse over the map.

## Reproduction

Load a status file and move the mouse over the map: it goes blank.

## Repair

`geometry()` only computes; `draw()` alone resizes the canvas, and only when
the size changes.

## Verification

Owner check in Firefox after the fix ("now it works"); local check with the
pointer moved over the map before the screenshot.

## Prevention

Viewer checks move the pointer across the map (hover, overlay switch) before
the screenshot, not only load it.
