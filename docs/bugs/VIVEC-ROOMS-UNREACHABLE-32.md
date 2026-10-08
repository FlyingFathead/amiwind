# VIVEC-ROOMS-UNREACHABLE-32: Excluded Vivec hub rooms leave converted rooms unreachable

## Status: 8 October 2026

Open. Found by the Vivec cantons import.

## Symptom

Where a hub room (for example a Waistworks level) is excluded for its limits, converted rooms
behind it cannot be reached: 5 of 18 in the Foreign Quarter, 5 of 14 in Redoran, 12 of 15 in
Telvanni.

## Where

Town interior import (door links).

## How it happened

Rooms are converted independently of reachability.

## Why it was not caught

First multi-room canton import.

## Reproduction

Import the cantons with the current exclusions.

## Repair

Not yet: report reachability per room in the import; fix the hubs (220-model limit, heap)
first.

## Verification

Pending.

## Prevention

Import report lists unreachable rooms.
