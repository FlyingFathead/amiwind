# Local source checkpoint: v0.0.25-rc7

Apply the complete update to the published rc6 source after any active build has
finished. The updater checks overlapping edits, backs up changed files and
verifies the installed source against the full public-source archive. No rc4/rc5
patches or loose feature files are needed. Source archives and tags are immutable.

Keep the original rc3 run with its passed world-terrain receipt. Use the supplied
RECOVER-IMAGE.sh with that run, the same game inputs, external tools directory
and workspace. It rebuilds only the versioned engine and final image, preserving
the retained scene, music and terrain. Add `--plan` for the two-command preview
or `--check` for prerequisite and retained-content checks. Output goes to a new
run; the old build and private-test HDF remain untouched.

The source handoff includes one publication script that validates the archive,
commits/pushes main, waits for the exact commit's source-check workflow to pass,
and only then tags and creates the source prerelease. It verifies downloaded
release assets against their checksums. The owner runs it. Local checks do not
claim that GitHub CI or a private game-image build has passed.

See [release notes](RELEASE-v0.0.25-rc7.md), [image recovery](IMAGE_RECOVERY.md),
[torch controls](TORCH.md), [map controls](WORLD_MAP_AND_JOURNAL.md), and
[character state limits](CHARACTER_STATES.md).
