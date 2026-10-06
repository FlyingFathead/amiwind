# FS-UAE development access

For the persistent headless Linux setup, see [FS-UAE in Docker](FS-UAE-DOCKER.md). For proposed headless automation and throughput measurement, see [FS-UAE headless development throughput](FS-UAE-HEADLESS-THROUGHPUT.md).
A ROM-only Ubuntu 24.04 / FS-UAE 3.1.66 session produced fresh full/cropped
frames, a visibly booted Kickstart screen, prompt-synchronized PTY replies for
registers, memory map and disassembly, and one bounded guest-memory read. A
synthetic audio route also passed; that does not verify Amiga game audio. This
is emulator-level evidence. Later separate headless runs have booted the
AmiWind development package, reached gameplay, observed a restored building
and quit cleanly. Those scene checks do not add stepping/watchpoint or complete
game-audio acceptance to the original debugger probe.

FS-UAE can expose the emulated Amiga through its UAE console debugger and its
serial interface. These are useful starting points for inspecting state and
driving repeatable development sessions with fewer desktop interactions.

This guide records documentation and source findings checked on 5 October 2026.
The debugger command reference below is anchored to upstream **v3.1.66**, an
earlier AmiWind validation baseline; it does not claim that version is latest.
Upstream's current main branch describes an in-development FS-UAE 5, so treat
the versioned commands as a compatibility baseline rather than a universal API.
See the [current upstream README](https://github.com/FrodeSolheim/fs-uae/blob/main/od-fs/README.md).
The existing automated probe has been exercised against the equivalent Ubuntu
24.04 / FS-UAE 3.1.66 runtime stack. The clean Dockerfile recipe remains
unverified as a build. The PTY smoke verified `r`, `dm`, `d`, fresh display
captures and one bounded memory-read command. It did not exercise stepping,
breakpoints, a watchpoint hit, memory writes, game progress or game audio.
See [playtesting](FS-UAE-PLAYTESTING.md) for the complete machine/disk setup.

## Which interface does what?

| Interface | Useful work | Evidence and limits |
| --- | --- | --- |
| UAE console debugger | Guest CPU registers, memory, disassembly, breakpoints and watchpoints | Stock documented facility; command availability depends on build |
| Emulated serial port | Logs and, with the guest AUX driver, an AmigaDOS shell in a host terminal | Stock documented transport; it does not itself provide a memory RPC API |
| Save states | Return to a prepared point within the same build | Documented slots and startup loading; validate CPU/JIT/disk compatibility |
| Frame screenshots | Save full or cropped Amiga frames | Documented capture; unattended triggering is a separate integration task |
| Lua remote shell / remote debugger forks | Potential scripted control and memory access | Optional version-specific extensions; do not assume stock support |

The debugger addresses **guest 68k memory**. A guest address is not a pointer
into the host process. Reading guest RAM through an emulator is also distinct
from programming the Amiga's hardware DMA channels.

## Start with an isolated development configuration

Copy a complete, working configuration and its writable disks. Keep the normal
playtest configuration available. Use explicit output directories and record
the emulator version, machine settings, engine checksum and all disk hashes.
Do not edit a filesystem from the host while the guest may cache or write it.
The [FS-UAE hard-drive guide](https://fs-uae.net/docs/hard-drives/) explains the
mounted-directory caching issue.

Merge this fragment into that development configuration; it is not a complete
boot configuration and supplies neither ROM nor disk paths:

```ini
console_debugger = 1
initial_input_grab = 0
automatic_input_grab = 0
fullscreen = 0
screenshots_output_mask = 3
```

On a Linux terminal, start the existing emulator with the copied configuration:

```sh
fs-uae --stdout /absolute/path/AmiWind-debug.fs-uae
```

Keep the terminal attached. The official console-debugger option documents
F12+D in the emulator window; enter debugger commands and read their output in
the attached terminal. The emulator pauses while the debugger is active. Use the
actual debugger prompt as the synchronization boundary for a PTY controller,
not a fixed delay. Disabling input grab avoids capturing mouse/keyboard; it does
not promise that launching a window cannot receive focus. Hidden-window or
virtual-display execution needs its own capture/control verification.
Sources: [console option](https://fs-uae.net/docs/options/console_debugger/),
[debugging and input grab](https://fs-uae.net/docs/debugging/),
[keyboard shortcuts](https://fs-uae.net/docs/keyboard-shortcuts/).

## Inspect guest state before automating mutations

The v3.1.66 [debugger help and implementation](https://github.com/FrodeSolheim/fs-uae/blob/v3.1.66/src/debug.cpp)
provide these commands. Upper/lower case matters; replace placeholders with
addresses resolved for the current loaded program. Start with a small RAM range.

| Command | Purpose |
| --- | --- |
| `r` | CPU register state |
| `dm` | Guest address-space map |
| `m ADDRESS [LINES]` | Memory inspection |
| `d ADDRESS [LINES]` | Instruction disassembly |
| `f ADDRESS`, `fl` | Toggle a breakpoint; list breakpoints |
| `t [INSTRUCTIONS]`, `z` | Step one or more instructions; step over |
| `w SLOT ADDRESS LENGTH W` | Watch writes to a range |
| `S FILE ADDRESS LENGTH` | Export a memory block |
| `W ADDRESS VALUES` | Change guest memory; use only in a disposable experiment |
| `g [ADDRESS]` | Resume at the current program counter or start at the supplied address |
| `q` | Quit FS-UAE; use `g` to resume a paused inspection |

In that parser, `$` selects hexadecimal and `!` decimal; `m` and `d` counts
otherwise use hexadecimal. For example, use `!4` for four lines. The `S` filename
cannot contain whitespace. These are parser findings, not an exercised session.

These commands are source-confirmed for v3.1.66, not all runtime-verified. The exercised PTY smoke returned `r`, `dm`, `d` and one bounded `m` read; stepping, breakpoints and a known-write watchpoint remain pending. Entering the debugger pauses emulation while inspection runs; `g` resumes execution. This is a pause/inspect/resume loop, not a non-pausing live-memory API.

For stepping and write-watchpoint experiments, use a separate diagnostic profile
with JIT disabled and compare it with the ordinary profile. The JIT-off test
is recommended but has not been run; do not treat its timing as gameplay
performance. This debugger session does not identify C variables by itself:
resolve runtime addresses against the loaded segment map and matching build
symbols/debug information, and rediscover addresses after loading a new build.

For RAM interpretation, use 68k byte order and the exact target structure layout.
AmigaOS relocates loaded segments, and map changes rebuild pointers: rediscover
addresses after loading rather than retaining raw addresses across sessions.
Restrict early probes to verified RAM, avoiding memory-mapped device registers.
If a write is necessary to isolate a cause, record original bytes and discard
the experiment afterwards. The lasting correction belongs in source and tests.

A debugger stop pauses the emulated CPU and disrupts normal audio/timing. It
cannot establish soundtrack continuity or release frame rate. Test those during
ordinary execution; AmiWind's modal world-freeze deliberately keeps music live.

## Catching a bad write: next diagnostic acceptance

Use a small synthetic guest program with a known changing value and matching
build information. Resolve its current RAM address, capture `r` and a bounded
`m` read, set a narrow write watchpoint, then resume with `g`. At the hit, retain
the accessed address, PC, registers and nearby disassembly. Step the known write,
read the value again, remove the test watchpoint and verify execution resumes.
Synchronize every operation with the real PTY prompt. The command forms are
defined by the pinned [v3.1.66 debugger source](https://github.com/FrodeSolheim/fs-uae/blob/v3.1.66/src/debug.cpp).

Run this in a separate JIT-off diagnostic profile. This **known-write test is
still pending**; existing memory reads do not certify it. Once accepted, the
same method can watch an allocation guard or suspect field using that build's
actual pointers and structure layout. A debugger stop changes timing, so validate
the eventual fix during normal execution too. No cartridge ROM or remote service
is required for the built-in console route; keep all guest dumps private.

## Symbols and loaded segments

The v3.1.66 source conditionally provides SegmentTracker commands:
`Z` for status, `Ze 1` to enable, `Zl` for loaded segments,
`Zf 'hostfile'` for debug information, `Zy 'symbol'` and `Zc 'file' LINE`
for symbol/source lookup. Check for `WITH_SEGTRACKER` support in the actual
binary and verify the target debug-file format before relying on these.
`Zf` expects a matching tracked segment and HUNK debug information; this
version's string parser lowercases its path, so use a lowercase diagnostic
pathname on a case-sensitive filesystem. The
[SegmentTracker author's setup notes](https://lallafa.de/blog/2013/06/added-segtracker-in-fs-uaes-debugger/)
describe enabling tracking before reboot and its Kickstart limitations. Their
2013 fork-only description predates its presence in the upstream tag above.

AmiWind's [engine Makefile](../engine/aga/Makefile) currently links with `-s`.
Preserve a separate unstripped diagnostic build and matching linker map/object
files when pursuing symbolic debugging; do not expect names in the stripped
playtest executable. Keep the target's existing optimization workaround and
compare behavior before using diagnostic timings. This guide adds no debug-build
switch and does not claim our present compiler's debug format has been accepted
by SegmentTracker. Running host `gdb` on FS-UAE debugs the emulator itself;
guest C debugging requires guest symbols, relocation and a compatible interface.

## A terminal route through the guest serial port

FS-UAE documents this loopback example:

```ini
serial_port = tcp://127.0.0.1:1234
```

Connect a terminal or a bounded host client to that local endpoint. The optional
`/wait` suffix holds boot until a client connects; omit it for unattended runs
unless the harness guarantees a connection. With an available AmigaOS AUX
driver, the guest command `newshell aux:` can expose an AmigaDOS prompt.
Minimal boot images may lack that driver. Follow the
[official serial guide](https://fs-uae.net/docs/serial-port/) for setup.

An AmigaDOS shell can help launch programs and collect guest logs. It is not
AmiWind's F10 console, and sending `dbg` text to serial will not automatically
invoke game commands. A game-command/telemetry bridge would need explicit
implementation and tests. Likewise, bind only to loopback for a local harness;
there is no reason for this development endpoint to be publicly reachable.

## Repeated scenes, snapshots and frame capture

For a **newly compiled engine**, recreate the scene through
[`dbg tpscene headselection`](DEBUG_OVERLAYS.md#named-debug-scenes-and-character-ui-versions-v0029-candidate).
It starts a disposable character-creation session and resets unsaved progress;
it does not provide a general checkpoint loader. More named scenes can be added
with explicit prerequisites and acceptance checks.

For repeated observations of the **same engine**, FS-UAE can start from slots
1-9 using `load_state = N`. Keep each state with its exact disk snapshot and
emulator/configuration identity. Restoring state restores the old executable
in RAM; replacing the disk executable does not turn that state into a new-build
test. Do not restore an old state against disks modified since capture. State
support is configuration-dependent and the launcher can disable it for known
unsupported cases. Sources: [startup loading](https://fs-uae.net/docs/options/load_state/),
[save-state availability](https://fs-uae.net/docs/options/save_states/).

`screenshots_output_mask = 3` requests full and cropped frame files without the
OpenGL screenshot variant. Set `screenshots_output_dir` to an existing directory.
The documented capture shortcut is Mod+S or Print Screen. This saves the Amiga
frame directly, but a shortcut alone is not a focus-free automation API.
Sources: [capture modes](https://fs-uae.net/docs/options/screenshots_output_mask/),
[output directory](https://fs-uae.net/docs/options/screenshots_output_dir/).

## Optional remote interfaces

The author of the 2015
[Lua-shell extension](https://lallafa.de/blog/2015/04/a-lua-shell-for-fs-uae/)
describes a patched build with `--enable-lua`, `lua_shell = 1`, and a localhost
shell. That is evidence for an extension, not proof that stock FS-UAE exports
that interface. Built-in Lua hooks and a remotely accessible Lua shell are
different capabilities. Remote GDB/HTTP examples from other forks likewise need
their exact source/version and protocol reviewed. No remote service is enabled
by this guide, and none is required for ordinary AmiWind playtesting.
For a concrete optional alternative, [UAE-DAP's own documentation](https://github.com/grahambates/uae-dap)
requires patched emulator binaries; its remote interface is not a stock FS-UAE
service. This study has not installed or validated that backend.

## Proposed AmiWind development loop

1. Keep build/tests reproducible in the isolated Linux build environment; retain
   the matching engine, symbols when available, configuration and content hashes.
2. Launch an owned development instance on a separate display/terminal, then
   reach the scene through game-level setup or a same-build snapshot.
3. Read a small, structured record around the event: region, position/yaw,
   equipment state and timer age, torch light admission, and voice-tail count.
   Resolve fields from symbols or explicit diagnostics, never guessed offsets.
4. Pair that record with frame captures before/after the event. Preserve camera,
   clock and input sequence so comparisons isolate the change.
5. Fix source, rebuild and recreate the scene. Verify at normal speed and on
   the intended emulator/hardware configuration before accepting a regression.

A future automation adapter should identify its backend/version, use bounded
requests and timeouts, distinguish pause/read/step/write operations, and return
capture files plus state receipts. A console adapter must synchronize with the
actual debugger prompt; a serial adapter must speak to an implemented guest
endpoint. Successful TCP connection alone proves neither protocol nor test
completion. These adapters and the telemetry record above are proposals, not
implemented AmiWind features.

Emulator snapshots, RAM dumps, writable disks and captures can contain owned
game content or ROM data. Keep them outside the distributable source archive;
share asset-free scripts and small synthetic regression fixtures instead.
