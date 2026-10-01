# Keyboard and command reference — v0.0.25-rc2

Maintain this list whenever a binding or reserved shortcut changes. The editable
source defaults live in [`config/keymaps.cfg`](../config/keymaps.cfg). The image
builder installs them as `id1/keymaps-default.cfg`. Personal bindings live in
**`id1/keymaps.cfg`**, separately from the settings in `id1/config.cfg`.

Startup reads defaults, legacy `config.cfg` and `keymap.cfg`, personal `keymaps.cfg`, then
`autoexec.cfg`. Legacy bindings remain readable for migration. Normal shutdown
writes the current bindings to `keymaps.cfg` and settings to `config.cfg`.
Edit the personal file while the game is closed; an active session saves its own
bindings when it exits. Keep the shipped defaults for recovery.

## Configurable gameplay bindings

| Default key | Command | Action / condition |
| --- | --- | --- |
| W / S | `+forward` / `+back` | Forward / backward |
| A / D | `+moveleft` / `+moveright` | Strafe |
| Left / Right | `+left` / `+right` | Turn |
| Space | `+jump` | Jump |
| Shift | `+speed` | Run; faster noclip flight |
| Ctrl | `+aw_fastflight` | Debug noclip only: twice Shift flight speed |
| E | `+aw_use` | Use / interact; up in noclip |
| Q | `+movedown` | Down in noclip |
| Mouse 1 | `+attack` | Attack |
| F | `impulse 202` | Draw / lower hands |
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
| Gameplay | Shift+V | Cycle requested draw distance |
| Gameplay | Shift+F5 / Shift+F6 | Previous / next music track |
| World map | M, Escape | Close map |
| World map | Wheel, +/- | Zoom |
| World map | Arrows, mouse drag | Pan |
| World map | P | Centre on current player |
| World map | Home / G | Fit island / toggle exterior-cell grid |
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

## Reconciled input and defaults

Shift/Ctrl/Alt are refreshed from each native input qualifier, with Caps Lock
limited to letters and focus changes clearing held input. Legacy personal
keymap.cfg loads before keymaps.cfg. The maintained canonical reference is
KEYMAPS.md. Autosave default is five; aw_autosaves 0..16 remains an archived
setting in config.cfg and Options > Autosave history.
