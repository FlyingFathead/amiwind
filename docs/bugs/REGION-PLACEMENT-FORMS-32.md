# REGION-PLACEMENT-FORMS-32: The same placement is stored in different forms from region to region

## Status: 8 October 2026

Open. Found by the world streamer measurement (Balmora's 64 shipped maps,
extrapolated to the island).

## Symptom

One object can appear as render-only in one region map, as collision only (no faces) in
another, or with its collision clipped to the core plus margin in a third.

## Where

The region converters (overlap handling).

## How it happened

Each region decides its own overlap treatment.

## Why it was not caught

Regions are checked one at a time.

## Reproduction

Compare one placement across the 64 Balmora maps.

## Repair

Superseded by the world streamer (each placement stored once); document for the transition.

## Verification

Pending.

## Prevention

A placement consistency check across regions.
