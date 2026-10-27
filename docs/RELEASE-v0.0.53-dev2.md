# AmiWind v0.0.53-dev2 (in development)

Development snapshot, 26 October 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.53-dev1](RELEASE-v0.0.53-dev1.md). Previous release: [v0.0.52](RELEASE-v0.0.52.md).

The second snapshot of v0.0.53 (in development).

## New since v0.0.53-dev1

- **A script's Activate on a load door uses the current frame's own doors after a walk across a frame border.** Before
  this, a script could open the start frame's doors from the new frame
  ([DOOR-BANK-STREAMED-FRAME-51](bugs/DOOR-BANK-STREAMED-FRAME-51.md)).
- **The hinged doors were checked.** They were already correct after a crossing, and a test now keeps them so.
- **The GitHub checks run in parallel jobs.** The public tools are kept between runs (bootstrapped again from nothing
  whenever the installer changes, on every tag and every week), the test suite runs in six shards side by side, and
  the dry-run image is built after the tests. Before, one job did all of it in a row; the v0.0.52 run was cancelled at
  its time limit (CI-SOURCE-JOB-TIMEOUT-52, [CI_DRY_RUN.md](CI_DRY_RUN.md)).

## Known in this build

- Some large interiors, in Vivec above all, are still loading in when you are already there
  ([CHIM-ROOM-POPIN-51](bugs/CHIM-ROOM-POPIN-51.md)).
- The doors have not yet been audited in game across a crossing; that is still to do.
- Everything else is in the [bug register](BUGS.md).
