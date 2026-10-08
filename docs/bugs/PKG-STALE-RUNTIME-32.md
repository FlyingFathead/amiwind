# PKG-STALE-RUNTIME-32: The sealed v0.0.31 playtest contains a stale launcher preset folder

## Status: 8 October 2026

Open. Found by the first from-scratch build with the repository builder (v0.0.32-dev1 attempt). The sealed package stays as it is (sealed artifacts are never changed).

## Symptom

The v0.0.31 private playtest ZIP contains `.runtime/495c1b3686118b12/`, a launcher preset
folder left from an earlier extraction, and lists it in PLAYTEST-MANIFEST.json.

## Where

The playtest packaging scripts (copying the previous package folder).

## How it happened

The package was assembled from an extracted earlier package.

## Why it was not caught

The manifest check compares listed files, not whether they belong.

## Reproduction

List the v0.0.31 playtest ZIP.

## Repair

Packaging starts from a clean folder and refuses `.runtime/` contents.

## Verification

Pending.

## Prevention

Package gate rejecting runtime folders.
