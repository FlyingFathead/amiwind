# GATE-SUITE-WRITABLE-32: The test suite needs a writable source copy and an executable /tmp; the documented command does not say so

## Status: 8 October 2026

Open. Found by the CHIM format and builder defaults jobs.

## Symptom

Run on a read-only source mount with a noexec tmpfs, the suite shows 198 errors, then 1; green once
both are fixed. The gate runner copies the source, but the documented command does not say why.

## Where

Test suite instructions (docs/DEVELOPMENT.md and the gate runner).

## How it happened

Some tests write next to the source or execute from /tmp.

## Why it was not caught

The gate runner hides it by copying the source.

## Reproduction

Run the suite with the source mounted read-only and /tmp noexec.

## Repair

Not yet: tests use their own temp dirs; the parallel test runner and the docs state the requirement.

## Verification

Pending.

## Prevention

A test that runs a sample with a read-only source mount.
