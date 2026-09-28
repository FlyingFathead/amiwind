# AmiWind v0.0.17 validation

## Observed results

- Owner test-004: all 12 conversion, engine and HDF stages completed using the
  owner's Morrowind installation. The SDK/map-tool downloads matched their pins;
  the pinned reference QuakeC compiler compiled the supplied game logic.
- Owner test-006: the owner reported "it works now" after the requested rebuild
  with FS-UAE autorun and default town-center/track-04 startup, and requested
  publication. This is owner-reported acceptance, not an independent exhaustive
  gameplay or performance test.
- Test-006 native 68040 engine and boot checker compiled successfully.
  29 targeted build, scene/spawn and music tests passed, including production
  music code with synthetic input, history and missing-track fallback.
- Final launcher: 14 tests passed, covering early emulator/ROM failures,
  direct files, renamed checksum-matching directory entries, duplicate copies,
  missing-match prompts, nonrecursive selection, paths with spaces, config
  preservation and actual invocation of a harmless emulator stub.
- Final public source ZIP and cumulative incremental are checked against the
  source allowlist and per-file SHA-256 manifest. Applying the incremental over
  the original owner snapshot and each test-001..006 source reproduces the
  complete final archive. No proprietary inputs or playable image are included.

## Limits

The final ROM-directory helper and documentation follow the owner's test-006
confirmation; they do not change the tested engine. No further full conversion
or emulator run is claimed for that host-side addition. Earlier setup attempts
installed tools reused in the successful build, so this is not proof of one
uninterrupted clean-machine run after every fix.

Hosted CI status belongs to the pushed release commit; no hosted pass is claimed
before it runs. The workflow installs public tools and builds an asset-free
notice image. It never obtains Morrowind files or a Kickstart ROM.

Windows/WSL, physical Amiga performance and exhaustive gameplay remain untested.
Native warnings, including possible uninitialized values and legacy array/path
handling, remain for review; successful compilation does not make them harmless.
