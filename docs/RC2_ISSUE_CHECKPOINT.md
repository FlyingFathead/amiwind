# RC2 issue checkpoint: implemented repairs and remaining work

## HARVEST-BITTERCOAST-29: one of three nearby mushrooms usable, 6 October 2026

Open RC2 playtest report in **Bitter Coast**: only one of three nearby mushrooms
could be eaten. The player tentatively identifies them as Luminous Russula but
also asks whether the other two are different types. Species and interaction
stage are unverified; do not assume that picking, harvesting and inventory
consumption are the same failure.

The original screenshot shows v0.0.29-rc2, global XYZ approximately
**-15287 -59485 735**, game time **02:39**. Obtain map and original reference IDs,
identify all three objects, and replay both pickup and inventory use. The cause
and fixed version are unknown. [Issue and reproduction](bugs/HARVEST-BITTERCOAST-29.md).

## Latest scoped RC2 playtest confirmations: 6 October 2026

The RC2 playtest was released on 6 October. Its source and executable remain
the exact tested snapshot; later full-release preparation is tracked separately.

- **CENSUS-DOOR-STUCK-29:** the player confirms the Census door no longer traps
  them in the reported case and displays the obstruction message. This accepts
  that reproduction in RC2; other occupied/clear positions, save/reload, return
  paths and long-term door behavior remain to be exercised.
- **LIGHT-EXTERIOR-JUMP-29:** the player confirms the reported sudden brightness
  increase near the Seyda Neen shack is gone in RC2. The original reproduction
  and coordinates remain recorded. This does not establish all-world coverage.
- **HAND-PUNCH-COVERAGE-29:** a High Elf punch playtest reports no exposed gaps.
  Sex was not specified. This supports the maximum-extension aperture repair
  in that sampled appearance; brief idle-to-punch disappearance remains open.
- **Torch appearance:** the player reports that the torch is very good at the
  default settings. This does not close outdoor tuning, style-3 embers, dark-room
  floor, unlit/fuel-state or broader actor-lighting coverage.
- **INTERIOR-LIGHT-29:** the player describes the game's luminance as much more
  tolerable. Their exact factors were not supplied. Do not infer an exterior
  brightness change: defaults remain interior 1.2x and exterior 1.0x. Static-NPC
  sampling and broader performance checks remain separate.

WinUAE guard-follow, race-selection and heavy-load music continuity remain open,
including the reopened appearance-entry report below. Temple holes remain open.

## Latest v0.0.29-rc2 playtest report: 6 October 2026

- **AUDIO-APPEARANCE-29 is reopened:** the current WinUAE playtest reports
  background-music pauses on entering the rotating character race-selection
  screen. The earlier RC1 report that this entry was fixed remains historical
  evidence; it does not establish the current build's continuity.
- **AUDIO-ENTER-29 / AUDIO-LOAD-29 remain open:** the current WinUAE playtest
  still reports music crackle and pauses, including Enter to follow the guard.
  Heavy-load continuity also remains unresolved. Nonzero FS-UAE audio and
  synthetic streaming checks do not prove WinUAE continuity at these events.
- **INTERIOR-LIGHT-29:** the player reports that luma is much more tolerable
  with the current settings. The exact factor was not supplied. This is a
  subjective visual improvement, not a new default selection or a resolution
  of static-NPC sampling, broader performance, or Temple geometry. Defaults
  remain interior 1.2x and exterior 1.0x.

These reports supersede conflicting current-status claims below while retaining
their dated history. No audio repair or full-release readiness is claimed.

Recorded 2026-10-06T19:08:08+00:00. Target **v0.0.29-rc2**, **Let There Be (Just a Bit More) Light**.
The executable passed source preflight, 1,057 tests (zero failures/errors,
four documented skips), and the Amiga target build. Its fresh disks passed
complete reopened readback. The later scoped release and playtest confirmations above supersede the
original pending-delivery status of this checkpoint.

## Repairs included in the RC2 candidate

| Issue | Repair and evidence | Remaining acceptance |
| --- | --- | --- |
| AUDIO-EFFECTS-DEFAULT-29 | Effects default 75%, preserving the other mixer defaults; eight focused checks. | Existing saved preferences override defaults; owner mixing playtest. |
| UI-OPTIONS-WRAP-29 | Options selection clamps at the ends instead of wrapping; seven checks. | Full native endpoint/reverse-scroll playtest. |
| CONSOLE-WHEEL-29 | Console consumes wheel events at scroll boundaries instead of falling through to unbound-key feedback; five checks. | Native long-scrollback/endpoints. Disk-backed scrollback is future work. |
| CENSUS-DOOR-STUCK-29 | Opening door collision hull could rotate onto local XYZ 65 52 65; occupied-door guard and five regression checks. | Reported trap accepted by the RC2 playtester; broader positions, save/reload and return cases remain. |
| LIGHT-EXTERIOR-JUMP-29 | Empty versus unused lighting lumps selected inconsistent exterior ambient paths; six checks and scoped native arrival views. | Reported Seyda shack brightness-jump reproduction accepted by the RC2 playtester; wider traversal coverage remains. |
| HAND-PUNCH-COVERAGE-29 | Maximum-extension near-plane aperture repaired; default and Argonian Female sampled native punches no longer show that opening; the RC2 High Elf playtest also reports no gaps. | Full race/pose coverage. Separate idle-to-punch disappearance stays open. |
| DEBUG-GALLERY-TIMING-29 | Combat/torch test timing and explicit-test input gates repaired. Later native run demonstrated punch, torch off/on/off after appearance choice and return to ordinary state. | Preserve normal story restrictions. Earlier failed torch-V observation is superseded for this narrow test case. |
| Torch visuals and controls | Flame style 2 and configurable strength included. Owner approved latest native torch off/on/off visuals 5/5; silent GIF retained. | Outdoor-area strength, missing style-3 embers, gray dark-room floor, unlit/fuel state remain separate. |
| INTERIOR-LIGHT-29 | Interior default 1.2, exterior 1.0, saved six-step Graphics sliders, console commands and compile-out flags. Exact RC2 native slider/save/readback passed. | Three-pair Census renderer sample measured +1.199%, about +0.110 ms/render. Broader gameplay, night, enabled/disabled, RAM and real-hardware performance remain open. |

These rows describe implemented or demonstrated repairs, not blanket owner
acceptance. First delivered fixed version is v0.0.29-rc2 for these included repairs;
open acceptance limits remain listed individually. [Lighting measurement and method](bugs/INTERIOR-LIGHT-29.md).

## Still open

- **BALMORA-TEMPLE-GEOMETRY-29, major:** partial lower-room wall/floor/ceiling
  loss, thin horizontal remnants and collision holes. Upper rooms and stairs
  are intact controls. Reported poses include local 1063 1048 3700 and
  931 1052 3701. The source-to-plane audit found and corrected a numerical
  export defect in a Temple-only path, but the diagnostic rebuild still had
  the large holes. It is not a proven cause or repair of those visible gaps.
  Faces reach the early drawing stages; edge/raster tracing remains next.
  RC2 preserves the original Temple map. No changes to other maps are approved.
- **AUDIO-APPEARANCE-29 / AUDIO-ENTER-29 / AUDIO-LOAD-29:** the current
  WinUAE playtest still reports crackle and pauses, including guard Enter and
  entry to rotating character race selection. Appearance entry is reopened
  after the earlier RC1 acceptance; heavy-load audio also remains unresolved.
  Bounded-read servicing, nonzero FS-UAE music capture and synthetic load
  tests do not establish WinUAE continuity repair.
- **HAND-PUNCH-TRANSITION-29:** brief hand disappearance from idle into punch.
  Alternating left/right punches and original punch sound/event coverage
  (**PUNCH-AUDIO-COVERAGE-29**) remain follow-up work.
- **INTERIOR-NPC-LIGHT-29:** brightness includes NPC static-light scaling;
  whether Census actors sample the appropriate room surfaces still needs
  a separate fixed-pose static/torch comparison.
- **TORCHTEST-DARKNESS-29 / TORCH-FUEL-29:** dim gray floor at zero light and
  missing compact unlit/burn-out state; outdoor strength needs tuning evidence.
- **Memory and coverage:** 2,724 maps passed the hard allocation ceiling.
  The same 44 modeled reserve-warning maps remain; no new warning maps.
  This does not constitute physical-Amiga RAM acceptance. Broader world,
  interior, quest and Windows-launch coverage remains incomplete.
- **Future optimization:** investigate Seyda Neen subdivision/loading density
  versus the smoother open-country and Balmora routes. Do not conflate this
  with the lighting-discontinuity fix or change other regions speculatively.

## Preserved RC1 positives

The earlier RC1 playtest reported appearance-selection entry music no longer
jumped; that audio issue is reopened by the later RC2 WinUAE report above.
Go back/Choose button borders worked, fists looked substantially better,
torch-to-NPC illumination improved, and traversal outside Seyda Neen was
smoother without the observed brightness jumps. These confirmations are scoped
and do not close the separate outstanding reports above.

[Bug register](BUGS.md) | [Playtest ledger](RC1_PLAYTEST_LEDGER.md) |
[Temple issue](bugs/BALMORA-TEMPLE-GEOMETRY-29.md) | [Roadmap](ROADMAP.md)
