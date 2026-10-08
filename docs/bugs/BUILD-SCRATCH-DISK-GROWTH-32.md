# BUILD-SCRATCH-DISK-GROWTH-32: Build scratch volumes grow the container disk image on the system drive

## Status: 8 October 2026

Open (infrastructure). Found while running parallel build jobs on the development host.

## Symptom

Build scratch volumes grow the container disk image on the system drive; space freed inside
volumes is reused but never returned. During parallel jobs the container disk image grew about
63 GiB in 40 minutes: one build's scratch volume reached about 151 GB and another job's about
131 GB. Moving 64.6 GiB of other data off the system drive left its free space unchanged at about
50 GiB, because the disk image took the space.

## Where

Docker Desktop on Windows (WSL2): container volumes live in one virtual disk file on the system
drive. Affects full builds, image steps and any job that copies build trees into scratch volumes.

## How it happened

Each job copied its inputs and outputs into its own scratch volume, and earlier image attempts
were moved aside instead of removed. The virtual disk grows on demand and never shrinks: space
freed inside it is reused by later writes but returned to the system drive only by compaction,
which needs Docker stopped (an owner decision on this host).

## Why it was not caught

Free space was watched on the system drive, not the size of each job's scratch volume, and no job
had a scratch budget.

## Reproduction

Run two full build jobs in parallel with separate scratch volumes; compare the container disk
image size and the system drive's free space before and after, and after deleting files inside a
volume.

## Repair

Not yet: per-job scratch budgets; reuse of one scratch tree instead of new copies; cleanup of
moved-aside image attempts after delivery; compaction of the disk image only when the owner stops
Docker for it.

## Verification

Pending.

## Prevention

Each job declares a scratch budget and reports its volume size; the disk watch includes the
container disk image size and alerts on growth rate, not only on free space.
