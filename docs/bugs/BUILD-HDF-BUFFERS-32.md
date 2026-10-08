# BUILD-HDF-BUFFERS-32: Hard disk buffer and MaxTransfer defaults depend on the disk type

## Status: 8 October 2026

Open. Found by the CHIM world-format follow-up (FFS sweep, branch v0.0.33-chim-format).

## Symptom

The same file system gets different defaults depending on how the hard file is made: partitions in
an RDB disk written with rdbtool get 30 buffers and MaxTransfer 0xffffff; a plain partition hard
file mounted by FS-UAE gets 50 buffers and MaxTransfer 0x7fffffff. Benchmarks and players can
therefore run with different settings without knowing it.

## Where

Disk images written by the builder (`tools/build_aga.py`, rdbtool partitions); FS-UAE hard file
settings.

## How it happened

Neither the builder nor the benchmark profiles set the buffer count or MaxTransfer; each tool used
its own default.

## Why it was not caught

`awbench disk` started reporting buffers and MaxTransfer only with the CHIM benchmark work.

## Reproduction

`awbench disk` on an RDB world disk and on a plain partition hard file: compare `buffers=` and
`maxtransfer=`.

## Repair

Not yet: the builder sets buffers (and MaxTransfer) explicitly on every partition it writes and
records them in the build receipt. In the FFS sweep, 30, 50 and 100 buffers stayed within the drift
of the control run for seeks, so the value is a consistency question first.

## Verification

Pending.

## Prevention

A builder test that every partition carries the configured buffer count and MaxTransfer.
