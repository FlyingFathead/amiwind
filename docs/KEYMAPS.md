# Keyboard and command reference — v0.0.25-rc7

<!-- contents start -->
## Contents

- [v0.0.29 F/V regression gate](#v0029-fv-regression-gate)
- [Options > Controls](#options--controls)
- [Configurable gameplay bindings](#configurable-gameplay-bindings)
- [Reserved and contextual controls](#reserved-and-contextual-controls)
- [Photo mode and crosshair](#photo-mode-and-crosshair)
- [Console line editing](#console-line-editing)
- [Reconciled input and defaults](#reconciled-input-and-defaults)

<!-- contents end -->

## v0.0.29 F/V regression gate

The 4 October owner playtest reports F no longer raising hands and V printing
torch on/off without visible hands or a working torch, especially in debug play.
The cause is unconfirmed. Controls below remain the required behavior, not an
acceptance claim. See [TORCH-INPUT-29](journals/BUG_JOURNAL-v0.0.29.md#torch-input-29-f-cannot-raise-hands-and-v-only-reports-torch-state-open)
and the [full input/state/visibility/light matrix](TORCH.md#v0029-required-hands-and-light-acceptance-matrix).
Do not replace personal bindings or bypass intentional story restrictions to
hide the failure. Capture the active bindings and input destination first.

Maintain this list whenever a binding or reserved shortcut changes. The editable
source defaults live in [`config/keymaps.cfg`](../config/keymaps.cfg). The image
builder installs them as `id1/keymaps-default.cfg`. Personal bindings live in
**`id1/keymaps.cfg`**, separately from the settings in `id1/config.cfg`.

Startup reads defaults, legacy `config.cfg` and `keymap.cfg`, personal `keymaps.cfg`, then
`autoexec.cfg`. Legacy bindings remain readable for migration. Normal shutdown
writes the current bindings to `keymaps.cfg` and settings to `config.cfg`.
Edit the personal file while the game is closed; an active session saves its own
bindings when it exits. Keep the shipped defaults for recovery.

## Options > Controls

Options > Controls lists the gameplay actions with their current keys. Select an
action and press Enter or click, then press the new key; Escape cancels.
Delete or Backspace clears the action's keys. Each action holds up to two keys;
a third key replaces both. A key already used by another action moves to the
new action. Reset to defaults reloads the shipped `keymaps-default.cfg`.
Changes use the same bindings as `bind` and are saved to `keymaps.cfg` on exit.
F1-F12 and the console keys are handled before the menu and cannot be captured
there; bind them with the console.

Greyed rows are planned actions (inventory, quick keys, magic) with their
intended keys. They become selectable when the action exists. The action table
and the steps for adding one are documented in `engine/aga/src/aw_menu.c`.

## Configurable gameplay bindings

| Default key | Command | Action / condition |
| --- | --- | --- |
| W / S, Up / Down | `+forward` / `+back` | Forward / backward |
| A / D, Left / Right | `+moveleft` / `+moveright` | Strafe |
| (unbound) | `+left` / `+right` | Keyboard turn; mouse turns by default. Earlier saved key files keep Left / Right as turn. |
| Space | `+jump` | Jump |
| Shift | `+speed` | Run; faster noclip flight |
| Ctrl | `+aw_fastflight` | Debug noclip only: twice Shift flight speed |
| E | `+aw_use` | Use / interact; up in noclip |
| Q | `+movedown` | Down in noclip |
| Mouse 1 | `+attack` | Attack |
| Right mouse (Amiga sends it as `MOUSE3`) | `+aw_alt` | Context action: picks a companion in pick mode (`dbg companion pick`); in a fight it is kept for a block button (not built yet; the original blocks automatically). Older saved key files get it if `MOUSE3` is unbound. |
| F | `impulse 202` | Draw / lower hands |
| V | `aw_torch` | Toggle the placeholder torch while hands are raised |
| M | `aw_worldmap` | Open world map, including debug/noclip |
| J | `aw_journal` | Open journal |
| T | `aw_wait` | Wait panel |
| F1 | `aw_quick_help` | Quick help |
| F5 / F9 | `aw_quicksave` / `aw_quickload` | Quick save / load |
| F6 | `aw_music_next` | Next music track |
| F8 | `aw_music_mode` | Music mode |
| Alt+M | `aw_desktop` | Send game screen behind desktop; debug must be on |

Ctrl flight requires debug overlays enabled, noclip active, and gameplay input.
It applies to all flight directions, including E/Q. Ctrl+Shift does not multiply
the boost again. Releasing movement stops flight without inertia. Normal walking
and running retain their existing speeds.

`ALT+M` is an explicit supported chord name, not a general modifier-expression
parser. For example, `bind "ALT+M" aw_desktop` restores its default. `bind m`
reports M's assignment; `bind m aw_worldmap` restores it; `unbind m` removes it.
Use `bind`, `unbind` and `unbindall` with care: `unbindall` clears all configurable
gameplay assignments. Positive button commands have matching release commands
handled by the input system; do not bind their negative forms for ordinary use.

## Reserved and contextual controls

These controls are handled by their panel or by the input layer. They are not
all remappable through gameplay bindings.

| Context | Keys | Behavior |
| --- | --- | --- |
| Game / console | Key left of 1, F10 | Cycle half console, full console, closed |
| Game / console | Shift plus either console key | Toggle full-height console |
| Any panel / console | Escape | Close/back; ordinary gameplay opens menu |
| Console | M, N and other printable letters | Enter text; no desktop action |
| Console | PageUp / PageDown; Shift+Up / Down | Scroll text |
| Console | Shift+Home / Shift+End | Scroll to the oldest / newest text |
| Console | Left / Right, Home / End, Ctrl+A / Ctrl+E | Move the cursor without deleting |
| Console | Backspace / Del | Delete before / at the cursor |
| Console | Ctrl+U / Ctrl+K | Cut to the start / end of the line |
| Console | Up / Down | Previous / next command; Down past the newest returns the typed line |
| Console | Tab | Complete a command or variable name |
| Gameplay | Shift+V | Cycle requested draw distance |
| Photo mode | Ctrl+F | Fog on/off (the fog setting from before photo mode returns when it ends) |
| Photo mode | Ctrl+H | Debug HUD on/off, the same as `dbg hud on/off` |
| Gameplay | Shift+F5 / Shift+F6 | Previous / next music track |
| World map | M, Escape | Close map |
| World map | Wheel, +/- | Zoom |
| World map | Arrows, mouse drag | Pan |
| World map | P | Centre on current player |
| World map | Home / G | Fit island / toggle exterior-cell grid |
| Debug teleport map | Left click | Select target; click TELEPORT to confirm |
| Debug teleport map | Enter / Escape | Confirm selected target / cancel |
| Debug teleport map | Right drag / arrows | Pan without selecting a target |
| Journal | J, Escape | Close journal |
| Gallery | Wheel / middle mouse | Navigate model view / return to browser |
| Menus | Arrows, Enter, Escape | Select, activate, back |

While the game window is active, an input handler strips Amiga modifiers
from M/N before Intuition handles its system screen shortcuts. This protects map
access and console typing even if that modifier is held. Deliberate desktop access
is the debug-gated Alt+M binding. Once another window is active, normal Amiga
screen controls are available again. Other applications' input is not filtered.

For diagnostics, use `debug all on`, `debug noclip`, `debug pos`, and
`debug view x y z yaw pitch`; see [DEBUG_OVERLAYS.md](DEBUG_OVERLAYS.md).
`aw_input_trace 1` logs native raw-key/qualifier events; restore `0` after checking.
`aw_desktop` also works as an explicit console command when debug is enabled.
The compass is normal gameplay UI and does not require debug mode.

## Photo mode and crosshair

`dbg photomode` (also `dbg killhud`) toggles photo mode for clean screenshots;
`dbg photomode on` / `off` set it. Options > Photo mode does the same from the
pause menu (Leave photo mode while it is on). Photo mode hides everything drawn
over the view: the health/magicka/fatigue bars, the crosshair, the first-person
hands, weapon and torch (Quake's `r_drawviewmodel`; the torch light stays, so
the lighting does not change), door and pickup prompts, names, subtitles, the
compass, the gold frame, the `dbg hud` overlays (title, coordinates, FPS,
console notify lines), test-room and gallery text and the `dbg lightgallery`
strip (its keys keep working), and the 3D view uses the whole screen. By default it
also switches the fog off (`aw_photomode_nofog 1`) and gives a free noclip
camera (`aw_photomode_noclip 1`); set either to 0 to keep the fog or to stay on
foot. `aw_photomode_hands 1` keeps the hands in view (default 0: hidden).
A short notice in the game's message box says how to leave; it disappears
after a few seconds, so the following frames are clean.

While photo mode is on, Ctrl+F switches the fog and Ctrl+H the debug HUD
(`dbg hud`; its coordinate strip then spans the whole bottom edge, and an open
light gallery strip comes back with it), each with a
brief notice in the same box. Outside photo mode these keys keep their bindings (F raises the
hands, Ctrl is the noclip fast-flight key). F10 still opens the console, which
reminds you how to leave. Leaving photo mode restores every setting it changed
exactly as before (fog, debug HUD and the rest, whatever Ctrl+F/Ctrl+H did) and
puts the player back where photo mode started, standing, with no momentum.
Photo mode is not saved: game saves need the player on foot, and `config.cfg`
is written with the settings from before photo mode.

`dbg crosshair` (also `dbg crosshairs`) toggles the crosshair; `on` / `off` set
it. Options > Show crosshairs does the same. It is the player's preference,
saved in `config.cfg` (Quake's `crosshair` setting, default on). A change made
during photo mode applies when photo mode ends.

## Console line editing
Animation kit console commands (`dbg animkit`): [ANIMKIT.md](ANIMKIT.md#console-dbg-animkit).

The console edits its line like a terminal prompt (`aw_console_mode 1`, the
default): the cursor moves without deleting, typing inserts at the cursor, and
the keys are in the table above. Up and Down walk the last 31 commands; Up stops
at the oldest, each opening of the console starts from the newest, and Down past
the newest brings back the line you were typing. Empty lines and a command equal
to the previous one are not stored. The history is kept between sessions in
`console-history.txt` in the game folder, written at Exit game or with
`dbg savelogs` (with `dbg logs live on` it is rewritten whenever Enter stores a new
command, as before; BOOT-VOLUME-NOT-VALIDATED-33). Held Left, Right, Del and Backspace repeat.

`aw_console_mode 0` (or `false`) restores id's Quake line editor: Left deletes like
Backspace, Right does nothing, Home/End scroll the text, and nothing is saved.
The history walk is the same in both modes. The setting is saved in `config.cfg`.

Amiga keys: Del is the Amiga Del key. Home and End are the extended keys of
PC-style Amiga keyboards (raw 0x70/0x71); FS-UAE sends a PC keyboard's Home and
End as keypad `(` and Help, so the AmiWind FS-UAE presets map them to the unused
keys 0x6A/0x6C, which the game also reads as Home/End. Without such a key, use
Ctrl+A and Ctrl+E. The Amiga keypad has no cursor keys: keypad 8 and 2 type
digits. FS-UAE sends a PC keyboard's Insert as the key left of Return (raw 0x2B),
which the game reads as Enter.

If the arrows do nothing, `aw_input_trace 1` shows whether they arrive: Up is raw 76 and
Down raw 77. No line means the emulator or host kept them, for example a keyboard
joystick on the cursor keys; the AmiWind presets turn that off. The Amiga keypad has
no cursor keys, so keypad 8 and 2 always type digits.

## Reconciled input and defaults

Shift/Ctrl/Alt are refreshed from each native input qualifier, with Caps Lock
limited to letters and focus changes clearing held input. Legacy personal
keymap.cfg loads before keymaps.cfg. The maintained canonical reference is
KEYMAPS.md. Autosave default is five; aw_autosaves 0..16 remains an archived
setting in config.cfg and Options > Autosave history.


The compass/heading HUD defaults to hidden in rc6. Use `dbg compass on` or
`dbg compass off`; `1/0` and `true/false` are also accepted, case-insensitively.
`dbg compass` alone reports the current setting. It remains independent of
`dbg all`/`dbg hud`. The archived config variable is `aw_compass`, with shipped
`config/game.cfg` default `aw_compass 0`; saved user settings override that
default on startup. Invalid values leave the setting unchanged.
