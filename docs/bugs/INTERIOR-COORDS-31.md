# INTERIOR-COORDS-31: Some interiors place objects beyond the +/-4096 coordinate range

## Status: 8 October 2026

Open. Found by the whole-world measurement (every object placed, estimated per map, checked on 30 converted maps). In-game effect untested.

## Symptom

The converter keeps each room at its cell origin, so 8 Vvardenfell interiors reach past
Quake's +/-4096 network coordinate range (Arena Waistworks 4,628; Kogoruhn Dome of
Pollock's Eve 4,352; three Tel Vos rooms; Vivec Redoran Temple Shrine; a Molag Mar trader;
Dren's Villa), and Bloodmoon's Gyldenhul Barrow reaches 8,586. The converter does not check.

## Where

The interior converter (room placement); coordinates are sent as 16-bit values x8.

## How it happened

Rooms are not recentred.

## Why it was not caught

No range check in the converter.

## Reproduction

Convert Arena Waistworks and print the extreme coordinates.

## Repair

Not yet: recentre each room on its own bounds; add a range check.

## Verification

Pending.

## Prevention

The builder fails on coordinates outside the range.
