# Balmora fixes and dev4 follow-up

Work in progress, 30 September 2026. Delivered dev4 archives are immutable.
Results below distinguish owner reports, inspected causes and validation.

## Guard chest armor

At Balmora (862,-502,58), yaw290/pitch13, the Hlaalu guard has the correct
bonemold cuirass equipped and all source chest submeshes are assembled. Material
alpha is 1.0. Reduction gives its main front panel only 17 requested triangles;
16 remain, reducing surface area from 130.51 to 37.32 square runtime units.
The apparent transparency is missing geometry, not an unequipped chest slot.

The converter retries large torso panels with larger quotas if area falls below
80% or any extent below 70% of the source. Other shapes retain their existing
quotas; the final native alias limit remains enforced. The inspected guard rises
from 511 to 586 triangles (1,758 vertices). Native same-camera capture shows the
solid chest restored. This does not certify every armor combination.

## Small gold font

Owner screenshots of “your” and lowercase s confirm missing upper strokes.
The shipped magic14.awf already lacks the stroke: the native UI drawer is not
clipping it. Direct 14px TrueType hinting leaves the top of o at alpha 30–32,
which rounds to zero in the four-level AWF ink encoding.

Rasterize the source outline at 4x on the host, average coverage and then quantize.
Retain native-size advances so menu wrapping is unchanged. Native preview shows
closed o and readable upper s strokes. No runtime rasterization or glyph-specific
pixel painting is added. Bitmap fallback and the debug console atlas are separate.

## Stairs

The b04, b13, b15 and dsteps03 candidates use the shared thin-shell conversion
for authored collision, preserving recesses that convex unions close. Player hull,
race/sex eye height and 90-degree FOV are unchanged. b17's dev4 fix remains.

Initial native routes improve access. Full ascent/descent acceptance is still in
progress: two b04 routes reached the lower flight but stopped near its entry arch.
Repeating with settled aim did not remove the blockage. A centred route passes
one b04 placement, but rotated placements still stop against sloped arch planes.
Investigate the standing-box expansion: face and axial support planes omit edge
bevels and can create false solid wedges beside oblique shell edges. An exact
convex-sum candidate is being tested; do not count noclip as walking.

The original source mesh and prepared visual polygons render cleanly in a separate
depth-buffered study. Native stairs and arches still show dark jagged strips.
Changing the depth tolerance or sampling position did not resolve them. Splitting
intersecting source surfaces also did not resolve the inspected native view and
adds excessive faces; that experiment is not an accepted fix. A requested native
polygon-drawing diagnostic was ineffective (unregistered command; the driver only
supports spans), so it is not evidence of a second native rendering path.

## Paving

The east-bank report at (455,-699,61), yaw1/pitch16, is an isolated source
material-0 tile at source cell (-3,-2), material tile (12,3). Its eight neighbours
are WG_road (34). An explicit checked repair continues that road texture; other
default-material tiles remain untouched. Separately, the old quad loop selected
material from its final northern height corner, shifting texture rows. Material
is now sampled inside each quad. Full region regeneration is complete; native
seam/floor and packaged-build acceptance remain pending.

## Additional owner reports against dev4 (18:16 Helsinki)

- Debug HUD: retain the current banner as `dbg hud type 1`; default type 2 uses
  the small diagnostic-console font so long version/location text fits.
- Fog controls: owner confirmed Shift+V works at 18:20 Helsinki and requested
  moving on. The missing-shortcut report is resolved; retain the existing binding.
- Prison ship: low FPS persists. Inspect/profile the guard's lower walkway and
  compare a simpler flat collision surface before attributing render cost to it.
- Census: Ganciele's adjacent door has an overly small interaction target even
  after papers. Reported camera (41,41,65), yaw55/pitch14. Authored door open/close
  sounds are absent; resolve source sound records and add a default-on setting.
- Census courtyard: transparent wall, floating window and jagged plank at
  (104,-80,57), yaw305/pitch-26; (125,-91,55), yaw328/pitch-20; and
  (99,-141,61), yaw345/pitch-23. Reproduce in the courtyard sub-cell.
- Seyda residency: keep the town centre together; owner suggests the bridge at
  (-30,474,70), yaw79/pitch2, as a transition boundary toward outskirts.
- Additional Balmora blocked stair: (597,-21,58), yaw337/pitch-5. Map and test it.

## Accepted constraints

Keep the dev3 Balmora Strider geometry/profile and frozen-frame Loading... box.
Whole-map polygon-density analysis remains future roadmap work. No FOV change.

## Subsequent reports and current candidates (18:43 Helsinki)

- Owner confirms dev4 Shift+V and Nord temple passage work. Preserve both.
- New public stairs: (-323,226,138), yaw260/pitch0 (bridge06 ref32699);
  (-527,187,143), yaw274/pitch-3 (bridge05 ref32722); and
  (-297,-1180,138), yaw85/pitch1 (another b04 placement).
- Subsequent report (18:46 Helsinki): (549,-739,58), yaw1/pitch-5. Nearby
  source placements include b02 ref6853 and dsteps03 ref41162. Add b02 to the
  inspected open-shell candidates; this report reinforces the shared conversion
  problem rather than an isolated coordinate repair.
- Hors preset requested: `dbg aw hors 0`, Nord / Barbarian / The Steed, after
  Census, starting at Seyda Neen square. Candidate native invocation creates
  Hors and reaches town at (0,0,57); subsequent Balmora teleport succeeds.
- Compact default HUD banner is visible in the native candidate; type 1 retains
  the original large banner. Numeric fog binds remain untouched after acceptance.
- Appearance entry must select Race. Zero mouse movement no longer overwrites
  keyboard focus; cursor begins over Race. Add clickable gold left/right arrows
  to Race/Sex/Face/Hair. The confirmation still defaults to Choose.
- Birthsign arrow-key report: owner sees cursor movement instead of selection,
  while WASD works. Host input tests pass both arrow directions and WASD; raw
  Amiga key translation maps both correctly. Exact native/emulator trigger is
  not yet reproduced. Optional `dbg input trace on` distinguishes received raw
  keys from mouse events; do not claim a proven fix from host tests alone.
- New interval-based span ordering removes the inspected dark stair/arch strips
  and restores courtyard wall continuity at the recorded cameras. It preserves
  world BSP keys and checks where mesh surfaces exchange depth within a span.
  `aw_surface_order 1` keeps the original algorithm; default 2 is the candidate.
  Initial matched-view timing samples show no obvious increase, but the final
  packaged-build performance route remains required.

## Final collision and door findings

The b04 obstruction persisted after camera settling: it was not a test-angle
issue. Complete standing-box bevels remove the false wedges beside the authored
arch. With normal movement type 3, the native candidate walks these routes:

| Approach | Upper endpoint | Return endpoint |
| --- | --- | --- |
| 1180,-155,119 (reported 1182,-141) | 1180,10,206 | 1181,-176,119 |
| -296,-1180,138 | -296,-994,224 | -296,-1199,137 |
| 549,-739,58 | 706,-744,134 | 520,-749,58 |
| -519,207,142 (reported -527,187) | -519,82,213 | -514,207,140 |

The bridge06 route also reaches the upper walkway. Player hull, step/slope rules
and eye heights are not changed. All 64 Balmora region reports are regenerated;
the highest clip-node count is 60,211, below the native 65,520 bound. The focused
four-route run has no surface/edge overflow. Citywide walking remains wider than
these measured routes; final HDF evidence records the packaged route separately.

The Census hall-door miss had another bounds detail: a rotated brush's broad
radius box can contain the player's eye. Clamping to that box returns the eye
itself, so the proximity selector rejects it. Use the door model's local bounds,
transform the eye into that frame, clamp, then transform back. Retain facing,
range and occlusion. At the reported (41,41), yaw55/pitch14 view, the native
candidate now advertises Hall door / Open: E and changes hall_open from 0 to 1.
Its authored opening WAV loads. The normal courtyard exit subsequently loads its
open sample, reaches Seyda Neen and loads its close sample. The scripted QA
build prepends scene commands to its queued test script; public interactive
queue behavior is unchanged and delay/duplicate-use/close-once are host-tested.
Offscreen null-audio tests verify sample selection and triggering, not listening.

## Prison ship performance

The shell (placed reference391417) contains 1,205 convex collision pieces. Each
trace searched a long union chain. A balanced bounds index now skips distant
pieces while retaining their original planes and solid leaves. The host checks
6,000 sampled point/player classifications, and the synthetic regression checks
solid pieces, empty gaps and the native first-node contract. No walkway flattening
or visible ship geometry change is needed for this measured improvement.

The first indexing trial exposed Quake's rule that visited nodes cannot precede
firstclipnode. Retaining the entry at its original lowest index fixes that format
violation; the failed trial is not counted as acceptance. New bounds nodes add
3,060 point nodes, 3,060 clip nodes and 1,056 planes to this ship BSP. Visual,
texture, lighting and entity sections remain byte-identical to dev4.

Matched lower-cabin view, reference accelerated FS-UAE 68040/FPU/JIT configuration:
medians of 16 samples per corrected-renderer case, after initial frames:

| Ship collision | Total frame | World rendering | Server |
| --- | --- | --- | --- |
| Original linear chain | 76.62 ms | 32.39 ms | 34.33 ms |
| Bounds index | 35.40 ms | 32.81 ms | 1.00 ms |

That is approximately 13 to 28 FPS at this view on this host. The unchanged world
cost and much smaller server cost support the collision-search diagnosis.
Legacy renderer comparison also improves from 87.24 to 43.47 ms. This does not
predict the owner's weaker machine or every view. Full natural escort acceptance
remains a separate playtest. The renderer itself remains the largest measured
cost after indexing; future work should profile before further visual reduction.

## Renderer cost and acceptance limits

With identical corrected geometry, the legacy/new span modes measure 56.23 /
55.31 ms at (613,-125), and 64.84 / 63.64 ms at the guard view (862,-502).
These short samples show no measured regression at those views; they are not a
whole-city FPS claim. Recorded native images show clean arch/stair boundaries
and continuous Census courtyard walls. Raw input birthsign reproduction remains
open despite passing native normal-key dispatch and host arrow/WASD tests.

The first combined final-image script exceeded Quake's 8,192-byte command buffer
and never started its route. Short final-binary/ship checks pass. Split the
script into bounded files; this harness failure is not a playable-build result.

## Packaged dev5 acceptance

The final executable is SHA256
`a805a28d931432854161f4aa95bdc3dd7a827e3d66a23f424076b104b27a05d6`.
A diagnostic copy of the final HDF completes 1,378 gameplay frames and 17
captures, then quits without ERROR.TXT. The shipped HDF remains unchanged.
All 712 payload files were independently read back and hashed before playtesting.

Nine normal-walking stair approaches reach upper landings and descend: both
original b04 approaches, b15, b13, the new -297,-1180 b04 placement, new
549,-739 b02/dsteps03, bridge05, bridge06 and the previously accepted b17
925,-290 approach. Recorded upper origins include b15 (1078,118,129), b13
(-818,126,330), bridge06 (-323,79,213) and b17 (1077,-290,144). These are focused
routes, not every possible lateral approach or the whole city's collision.

Seyda positions (0,0), (250,250), (-30,460) and (-30,560) retain sn012. Moving
beyond the core's hysteresis to (-30,600) loads sn017, and returning to
(-30,350) restores sn012. Frozen and black methods both complete. Sampled
Seyda replacements take 413–459 ms on this host. Intro-specific pier/courtyard
rules remain separate. Both HUD types, Hors creation, teleport and final guard/
road/arch views are captured. The prison loads the indexed hull successfully.

No surface/edge overflows occur. Peaks are 8,983 surfaces and 15,607 edges;
peak sampled hunk use is 10,926,416 bytes within 11,534,336 reserved bytes.
Audio reports only its startup warmup event. Offscreen/null-audio acceptance does
not certify subjective sound quality, the owner's hardware, every scene or the
complete natural opening. 291 host tests pass without skips. Compiler diagnostics
remain the same 82 warnings as dev4. Source allowlist/whitespace checks pass for
675 files. No publishing or Git actions are performed.
