# BOOT-68060-FPU-FAIL-32: On a 68060 with Kickstart 3.1 and no 68060.library the boot check fails the FPU line and stops

## Status: 8 October 2026

Open. Found by the FPU support library work (FS-UAE, Kickstart 3.1, JIT off).

## Symptom

Kickstart 3.1 reports a 68060 without FPU flags (AttnFlags $000F) until a 68060.library is
loaded, so the boot check prints "required internal FPU absent [!] FAIL" and the startup
sequence stops, although the CPU has an FPU.

## Where

`engine/aga/boot/bootcheck.asm` (FPU test from AttnFlags).

## How it happened

The FPU test relies on flags that Kickstart 3.1 sets only for 68040s.

## Why it was not caught

Only 68040 profiles were tested.

## Reproduction

Boot the image in FS-UAE as a 68060 without a support library.

## Repair

Not yet: detect the FPU directly (probe an FPU register under a temporary trap vector, as the
loader already does for the 68060 PCR), and keep the support library as the WARN line.

## Verification

Pending.

## Prevention

A 68060 profile in the boot tests.
