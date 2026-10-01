# Local source checkpoint: v0.0.25-rc8

Apply this complete source update to the published rc7 checkout after any build
finishes. APPLY.sh verifies checksums, backs up replacements, rejects conflicting
edits and validates the installed source against the full archive.

RECOVER-IMAGE.sh takes the checkout and the ORIGINAL failed rc3 run with passed
world-terrain, exactly as for rc7. It rebuilds the versioned engine and image into
a new run, retaining terrain and music and keeping strict actor validation.
It does not accept the successful rc7 recovery run as its input baseline.

Retest F then V in the emulator before publishing this correction. PUBLISH.sh
with --publish commits/pushes main, waits for successful exact-commit CI, then
tags and publishes the source prerelease and verifies downloaded checksums.
Its default --check performs only local candidate checks. The owner runs all
remote publication commands. Published rc7 tags and archives stay unchanged.
