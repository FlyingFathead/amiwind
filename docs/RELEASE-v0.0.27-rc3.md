# AmiWind v0.0.27-rc3 - Rocks, Mushrooms, and Then Some

**Not release-ready:** owner playtesting exposed sn012 heap exhaustion during
Hors restart from Jiub name entry. Direct visibility/lighting/entity loading
avoids the duplicate input buffer; its host regression and Amiga compile pass.
The heap-headroom gate and repaired target playtest remain required. See
[CRASH-01](BUG_JOURNAL.md) and [heap allowance policy](CELL_CHANGING.md).

Rc3 carries the rc2 mushroom seam correction, accepted by the owner in WinUAE,
and adds the Seyda Neen terrain handoff and held-input corrections.

The town retains its handoff and FPS subdivision cores. A 768-unit authored
LAND apron supplies ground beyond the boundary; shared world sampling,
triangulation and material selection align the overlap outside the detailed
port approach. The sky enclosure covers the measured surrounding hills.
Superseded stock Quake world collision hulls are removed before grafting the
source-sized standing player hull, following the streamed-world policy.

Automatic cell/sub-cell loads retain held movement buttons, Shift and Ctrl.
Door transitions, explicit teleports and focus-loss handling keep their input
clearing policy. The real transition harness passes in both variants, checking
health, raised hands, torch, noclip, position/view and velocity. It does not
implement weapon gameplay, NPC pursuit or combat. See [cell changing](CELL_CHANGING.md).

Terrain overlap regressions and source packaging checks passed locally.
The rc3 native engine and full image assembly passed. Strict packaged actor
contact passed with zero unresolved cases; the gallery contains 2,935 records
and 3,551 models. Both filesystem readbacks, independent HDF hashes, both
emulator disk lists and the actual 25-region runtime directory passed.
HDF capacities are 4,026,564,608 and 1,207,992,320 bytes, with every filesystem
partition below 2 GiB and each disk below 4 GiB. The focused Python suite passed
36 tests; both real scene-transition harness variants passed.

Owner terrain/input playtest, fresh Linux/Docker validation, hosted CI and
publication remain pending. Native Windows remains experimental. Further
size/runtime optimization follows the measured baseline; see the [roadmap](ROADMAP.md).

See [rc2 screenshots and scope](RELEASE-v0.0.27-rc2.md), the
[bug journal](BUG_JOURNAL.md) and [What are rocks?](WHAT_ARE_ROCKS.md).
Distribution remains source/tools plus explicitly selected documentation media;
users supply game data and ROMs. No playable HDFs or proprietary runtime assets
are public release inputs.

## Playtest expectations

Heavy world-content development is in progress. Unexpected performance drops,
loading pauses and stability issues may still occur. The aim is to assemble the
intended content, measure the full workload, then optimize it. Please be patient
and include the build identifier, location and reproduction steps with reports.
This experimental status does not waive known crash fixes or required heap
headroom; the confirmed rc3 loading defect remains a publication blocker.
