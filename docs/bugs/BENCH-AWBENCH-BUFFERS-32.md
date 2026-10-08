# BENCH-AWBENCH-BUFFERS-32: awbench reported the stale buffer count after AddBuffers

## Status: 8 October 2026

Open: fixed on the CHIM branch (v0.0.33-chim-format, commit 66d316b), not merged into the v0.0.32
development line.

## Symptom

The first `awbench buffers` read the buffer count from the drive's mount entry, which AmigaDOS
`AddBuffers` does not update, so it reported the old value after a change.

## Where

`engine/aga/bench/awbench.c`, `buffers` mode.

## How it happened

The mount entry holds the boot-time value; the file system keeps the live count itself.

## Why it was not caught

First use of `awbench buffers`.

## Reproduction

`awbench buffers DW1: 100`, then compare the reported `after=` value with the count the file system
uses.

## Repair

On the CHIM branch (66d316b): `awbench buffers` reports the count returned by `AddBuffers` itself.

## Verification

FFS sweep on the CHIM branch (30, 50 and 100 buffers in one session).

## Prevention

Merge with the CHIM branch; the benchmark output records `before`, `want`, `result` and `after`.
