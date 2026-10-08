# WORLD-THIRD-PARTITION-32: The world image now needs a fourth partition (DW2); launchers were only used with three

## Status: 8 October 2026

Open. Found in the v0.0.32-dev1 image build.

## Symptom

With trees and grass the world payload needs a fourth partition, DW2, on the second world drive (v0.0.31 used DH0,
DW0, DW1). The launchers and emulator setups have only been used with the old layout.

## Where

`tools/world_volumes.py`; launcher and emulator configs.

## How it happened

Flora adds about 5,000 sprites and map size.

## Why it was not caught

First from-scratch build with flora.

## Reproduction

dev1 image build.

dev1 smoke test (8 October 2026): the launchers add the world disk with every partition and the
game runs in FS-UAE; WinUAE mounting of DW2 is untested. The static emulator templates list no
world disk at all ([EMULATOR-TEMPLATES-WORLD-32](EMULATOR-TEMPLATES-WORLD-32.md)), and the world
disk image is now slightly over 2 GiB ([WORLD-HDF-OVER-2GIB-32](WORLD-HDF-OVER-2GIB-32.md)).

## Repair

Not yet: smoke-test that DW2 mounts in FS-UAE and WinUAE with the shipped launchers; record the layout.

## Verification

Pending (dev1 smoke test).

## Prevention

The smoke test checks every partition is mounted.

## Outlook

The need for more than one world partition is an early-development scaling problem, and it is being
worked on. Today's world is stored as thousands of overlapping region maps, and every exterior object is
duplicated into each region that can see it, so the converted world outgrows one partition.

The world streamer (the CHIM engine, from v0.0.33) stores every model, texture and placement once and loads
the world in small chunks. On the first converted town it needs about an eighth of the disk space of the
region maps. The goal for the whole game is a single hard file, so additional partitions beyond one should
stop being an issue as the engine changes. Until then, the launchers and the partition check must handle
however many world partitions a build produces.
