# BUILD-XDFTOOL-ARGMAX-32: the image step fails at the end: xdftool argument list too long

## Status: 8 October 2026

Open; fix written on the image parallelization branch. Found while profiling the v0.0.32-dev1 image
step on a copy of its inputs.

## Symptom

The image step ends with "Error: [Errno 7] Argument list too long: xdftool" after about 30 minutes of
work. The boot partition is written with ONE xdftool command that lists every boot file: with trees
and grass the boot payload has 15,747 files (about 5,000 flora sprites more than before), about 2 MB of
arguments, over the Linux limit (ARG_MAX 2,097,152).

## Where

`tools/build_aga.py` `finalize_image` (Linux path: one unbatched call); `tools/world_volumes.py`.
The Windows path already batched (`tools/build_windows_xdftool.py`).

## How it happened

The Linux path never had to write this many files: earlier images were patched rather than built, and
flora was opt-in (BUILD-FLORA-OPTIN-32).

## Why it was not caught

No test with a realistic file count; the step fails only at its very end.

## Reproduction

Image step with world flora on the full boot payload.

## Repair

Batch the xdftool operations on every platform (256 KiB of arguments per call, same operation order),
shared by the boot partition and the world volumes.

## Verification

Commit 1f301c4: `tests/test_build_windows_xdftool.py` builds an 18,000-file queue (above 2 MiB),
checks every call stays at or below 256 KiB, keeps the order and creates the image only once; both
packers use the runner. Full suite green on that commit. The dev1 image rebuilt with the fix:
pending.

## Prevention

A test that builds a command list for 20,000 synthetic files and checks every call stays under the limit.
