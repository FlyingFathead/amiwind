# OpenMW headless reference testing in Docker

Suggested repository location: docs/OPENMW-HEADLESS-REFERENCE.md.

<!-- contents start -->
## Contents

- [1. Can OpenMW run headless?](#1-can-openmw-run-headless)
- [2. Docker launch example](#2-docker-launch-example)
- [3. Automation building blocks](#3-automation-building-blocks)
- [4. Proposed AmiWind comparison workflow](#4-proposed-amiwind-comparison-workflow)
- [5. Direct upstream links](#5-direct-upstream-links)

<!-- contents end -->

Source links checked: 5 October 2026. This is a source-based setup and workflow reference, not a report of a successful OpenMW run in any particular AmiWind environment. Launch commands below are examples requiring a prepared local configuration. OpenMW is an open-source reimplementation of the Morrowind engine, not the original game executable; it still requires game data supplied by the user. OpenMW and AmiWind are independent renderers, so matching a scene does not imply pixel-identical output. Original game data, saves, and captured reference images remain private and are never part of this public source package. The proposed comparison workflow is not yet claimed implemented.
## 1. Can OpenMW run headless?

**Yes: OpenMW can run unattended without a physical screen, using a virtual
display.** Its upstream CI runs integration tests through `xvfb-run`.

Source: [OpenMW CI integration-test launcher](https://raw.githubusercontent.com/OpenMW/openmw/master/CI/run_integration_tests.sh).

**Headless does not automatically mean rendering-free.**

| Mode | What the examined upstream code supports |
| --- | --- |
| No visible human desktop or physical monitor | Run OpenMW on an Xvfb virtual display and control the test programmatically. |
| Simulation only, without graphics initialization or rendering | Not the ordinary engine path examined here. The engine creates an SDL/OpenGL window and graphics context. The examined command-line definitions do not provide a stock `--headless` or `--no-render` switch. |

Sources: [engine initialization and frame loop](https://raw.githubusercontent.com/OpenMW/openmw/master/apps/openmw/engine.cpp), [engine command-line options](https://raw.githubusercontent.com/OpenMW/openmw/master/apps/openmw/options.cpp), and [shared configuration/options implementation](https://raw.githubusercontent.com/OpenMW/openmw/master/components/files/configurationmanager.cpp).

The virtual display removes the need for a real desktop, not the work involved
in rendering the world. Do not present this approach as a zero-render-cost
simulation service.

## 2. Docker launch example

Use a separate OpenMW reference-testing profile with the same **type** of
virtual-display infrastructure used for FS-UAE. Do not assume that a successful
FS-UAE launch already proves OpenMW works.

The following example assumes OpenMW and `xvfb-run` are installed, the virtual
display has a working OpenGL implementation, and
`/work/openmw-reference/config/` contains a prepared configuration pointing to
a privately mounted Morrowind installation.

```bash
xvfb-run -a -s "-screen 0 800x600x24" \
  openmw \
    --replace config \
    --config /work/openmw-reference/config \
    --no-sound \
    --no-grab \
    --skip-menu \
    --start "Seyda Neen"
```

`--config` selects a configuration directory. The `--replace config` mechanism
controls configuration layering; it does not generate a complete Morrowind
configuration for an empty directory. Retain the installation's required
resources and prepare the reference profile before launching.

Sources: [configuration implementation](https://raw.githubusercontent.com/OpenMW/openmw/master/components/files/configurationmanager.cpp) and [official configuration paths and layering documentation](https://openmw.readthedocs.io/en/latest/reference/modding/paths.html).

The startup options disable sound, avoid grabbing the mouse, skip the main menu,
and select an initial cell. This is a **launch example**, not a completed test
harness. A run using `--no-sound` cannot establish audio correctness.

Source: [OpenMW command-line option definitions](https://raw.githubusercontent.com/OpenMW/openmw/master/apps/openmw/options.cpp).

### Keep the window visible inside the virtual display

**Do not minimize or hide the window as a substitute for headless operation.**
The examined engine frame loop returns before the game-state updates when the
window is considered not visible. Leave the window normally visible inside
Xvfb, even though no human monitor displays it.

Source: [engine.cpp, visibility check in `OMW::Engine::frame`](https://raw.githubusercontent.com/OpenMW/openmw/master/apps/openmw/engine.cpp).

## 3. Automation building blocks

OpenMW provides useful startup controls:

| Option | Purpose |
| --- | --- |
| `--script-run /path/to/commands.txt` | Execute a file containing console commands at startup. This is a console-command file, not a Python script or a generic Lua entry point. |
| `--load-savegame /path/to/reference.omwsave` | Load a prepared saved game at startup. |
| `--random-seed 12345` | Specify the initial random seed. A fixed seed alone does not prove fully deterministic execution. |

Source: [OpenMW command-line option definitions](https://raw.githubusercontent.com/OpenMW/openmw/master/apps/openmw/options.cpp).

### Start from the upstream integration-test runner

OpenMW's Python test runner is a useful model for unattended control. It launches
the engine, reads Lua-generated test markers from stdout, distinguishes test
success from failures and unexpected termination, and retains logs and rendering
statistics.

Read these together:

- [Python integration-test runner](https://raw.githubusercontent.com/OpenMW/openmw/master/scripts/integration_tests.py).
- [CI wrapper that runs it through Xvfb](https://raw.githubusercontent.com/OpenMW/openmw/master/CI/run_integration_tests.sh).

The CI example uses an upstream example-suite and test fixtures. It is evidence
for the unattended workflow, not an already configured AmiWind/Morrowind
reference test. Adapt the runner and scenario definitions deliberately rather
than treating the CI command as a drop-in test of your game installation.

## 4. Proposed AmiWind comparison workflow

**Proposal:** use OpenMW as the reference side and FS-UAE as the Amiga side.

```text
Defined test scenario
        |
        +-- OpenMW + original data
        |     Reference screenshots and game-state observations
        |
        +-- FS-UAE + AmiWind
              Converted-game screenshots, state and Amiga diagnostics
```

Inspect the same doorway, NPC placement, terrain crossing, or sky orientation
under deliberately matched conditions. Prefer structured state reports where
possible and screenshots when appearance is the subject of the test.

### Repeatable matched-view protocol

For every A/B capture, record the same named cell or scene and exact global position. OpenMW 0.48's console Help command prints the engine version and available commands. Use these commands to reach and inspect the pose:

| Purpose | Console command | Notes |
| --- | --- | --- |
| Set XYZ and heading in the current cell | player->Position x y z zrot | OpenMW 0.48 interprets the Position rotation argument in degrees. Verify the resulting angle because reported values can wrap. |
| Place in a named cell | player->PositionCell x, y, z, zrot, "Cell Name" | Check the observed angle after placement; an OpenMW issue discusses legacy angle conversion behavior. |
| Center on a named cell | COC, "Cell Name" | Coarse placement; an exterior name can match more than one cell. |
| Center on an exterior grid | COE, gridX, gridY | Coarse placement; set exact XYZ and heading afterward. |
| Read position components | player->GetPos x | Record X, Y, and Z separately after gravity and cell loading settle. Repeat with y and z. |
| Read heading | player->GetAngle z | Normalize wrapped values before comparing. |
| Set the in-game hour | set gamehour to N | Use the same hour in both runs and record the date as well. |
| Set the game time scale | set timescale to N | Use the same factor in both runs; note the observed game-time progression. |
| Set a region's weather | ChangeWeather "Region Name" weatherId | Verify the region and weather ID with the installed command list, then wait for transitions to settle. |

The command examples above are for OpenMW 0.48.0. The Ubuntu package build used for the reference setup is 0.48.0-1ubuntu5; its upstream version tag is openmw-0.48.0. In 0.48, Help prints the engine version and available commands ([official release notes](https://openmw.org/2023/openmw-0-48-0-released/)). The 0.48 MWScript compiler source registers Position, PositionCell, GetPos, and GetAngle ([extensions0.cpp at the upstream 0.48 tag](https://gitlab.com/OpenMW/openmw/-/blob/openmw-0.48.0/components/compiler/extensions0.cpp)). OpenMW's issue tracker shows the console assignment forms set gamehour to X and set timescale to X ([issue 5165](https://gitlab.com/OpenMW/openmw/-/issues/5165)); it also documents ChangeWeather with the region name and weather ID ([issue 6168](https://gitlab.com/OpenMW/openmw/-/issues/6168)). A misspelled/nonexistent weather region can fail silently, so check the region name carefully ([issue 6358](https://gitlab.com/OpenMW/openmw/-/issues/6358)). The Position and PositionCell rotation caveat is tracked separately ([issue 9247](https://gitlab.com/OpenMW/openmw/-/work_items/9247)); verify the actual resulting angle for the selected command and installed package.


For scene alignment, record the player's actor-origin/feet position, the camera eye-height offset, and the corresponding AmiWind model/bounds or view reference separately. Derive the vertical conversion between those reference points before comparing Z; raw player Z and Amiga model or camera Z may describe different points. The [OpenMW issue discussing Position and PositionCell angle conversion](https://gitlab.com/OpenMW/openmw/-/work_items/9247) is a reminder to validate against the installed build.
Set and record the same in-game date and hour, weather and transition state, and time scale on both runs. Confirm the installed build's time and weather commands before using them; if weather cannot be set deterministically, wait for and record a stable state rather than comparing different transitions. Record camera heading and pitch, field of view, resolution and aspect ratio, view distance, fog/visibility, lighting and shader settings, and whether weapons, spells, shield, torch, or other equipment are visible. Keep the same first-person/third-person view and idle pose. Allow cell streaming, animations, and weather effects to settle before capture; capture multiple frames if the scene contains blinking or other periodic animation, and compare equivalent points in its cycle.

Useful visual pairs include a doorway and adjoining interior, an NPC at a fixed location, a terrain or shoreline crossing, and a horizon at a recorded time. Compare the scene and behavior separately from renderer-specific effects such as anti-aliasing, color grading, fog implementation, and pixel layout. A muted `--no-sound` run can support visual inspection but does not test audio and cannot pass an audio acceptance check.
This is a comparison design, not a claim that OpenMW reproduces every original
Morrowind quirk or that OpenMW and AmiWind should produce identical pixels.
It also does not replace testing AmiWind's actual Amiga memory use, machine code,
or performance in FS-UAE.

Keep rendering enabled for visual checks, automate the scenarios, and compare
recorded results rather than manually operating two desktops.

Keep original game data, local saves, and private reference captures outside the
public source package. This document contains only guidance and public source
links, not game assets.

## 5. Direct upstream links

All four source URLs cited in the original explanation are included below as
ordinary Markdown links, usable as direct Markdown links.

| Reference | Direct link | What to inspect |
| --- | --- | --- |
| CI virtual-display launch | [CI/run_integration_tests.sh](https://raw.githubusercontent.com/OpenMW/openmw/master/CI/run_integration_tests.sh) | `xvfb-run`, runner invocation, and fixture configuration. |
| Engine startup options | [apps/openmw/options.cpp](https://raw.githubusercontent.com/OpenMW/openmw/master/apps/openmw/options.cpp) | Startup cell, menu bypass, sound, command-file execution, saved games, and random seed. |
| Graphics and game loop | [apps/openmw/engine.cpp](https://raw.githubusercontent.com/OpenMW/openmw/master/apps/openmw/engine.cpp) | SDL/OpenGL setup, window visibility, and frame processing. |
| Automated test runner | [scripts/integration_tests.py](https://raw.githubusercontent.com/OpenMW/openmw/master/scripts/integration_tests.py) | Process control, Lua test markers, failure handling, and evidence collection. |

Additional configuration references:

- [Shared configuration implementation](https://raw.githubusercontent.com/OpenMW/openmw/master/components/files/configurationmanager.cpp).
- [Official paths and configuration-layering documentation](https://openmw.readthedocs.io/en/latest/reference/modding/paths.html).

The `master` and `latest` URLs are moving references. Before implementing the
runner, record the installed OpenMW version and consult the corresponding
release or source revision. Do not assume that every distribution package has
exactly the same options or test infrastructure as upstream `master`.

**Acceptance remains local:** an upstream CI example establishes the approach;
it does not establish that the local container has loaded the intended game,
advanced the scenario, captured the correct view, or completed the comparison.

Version-specific references: [OpenMW 0.48.0 release notes](https://openmw.org/2023/openmw-0-48-0-released/), [0.48 Lua core reference](https://openmw.readthedocs.io/en/openmw-0.48.0/reference/lua-scripting/openmw_core.html), and [0.48 Lua world reference](https://openmw.readthedocs.io/en/openmw-0.48.0/reference/lua-scripting/openmw_world.html).
