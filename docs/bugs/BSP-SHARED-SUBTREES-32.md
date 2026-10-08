# BSP-SHARED-SUBTREES-32: Converted maps share node subtrees between submodels; naive tree walks explode

## Status: 8 October 2026

Open. Found by the world streamer measurement (Balmora's 64 shipped maps,
extrapolated to the island).

## Symptom

The converter's submodel node trees share subtrees. A tool that walks them without tracking
visited nodes repeats work exponentially (a measurement script was killed for running out of
memory).

## Where

Converter output (submodel node trees); any tool walking them.

## How it happened

Subtree sharing saves space.

## Why it was not caught

Not documented.

## Reproduction

Walk every submodel tree of a converted map without a visited set.

## Repair

Document it; tools that walk node trees track visited nodes.

## Verification

Pending.

## Prevention

A test map with shared subtrees for tree-walking tools.
