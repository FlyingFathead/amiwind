# Fatal error reports

When an engine error reaches `Sys_Error`, AmiWind attempts to save `ERROR.TXT`
in its current AmigaDOS launch directory. It verifies the file by reading its
complete contents back before reporting success. After closing the game screen,
the AmigaDOS output has this form:

```text
------------------------------------------------------
AmiWind v0.0.28 crashed!
Crash details: <the engine error>
Crash log is at <resolved AmigaDOS path>/ERROR.TXT
------------------------------------------------------
To restart AmiWind, try typing: amiwind
```

The actual path uses AmigaDOS syntax: for example, `AmiWind:ERROR.TXT` when
launched from that volume's root. A diagnostic run can use a different current
directory. If path resolution fails, the message identifies `ERROR.TXT` in the
launch directory. If writing or complete readback fails, AmiWind says that the
log could not be verified and asks you to copy the displayed details instead.

A normal `quit` prints the restart reminder and does not create a crash report.
`ERROR.TXT` contains the supplied error text, not a memory dump. Hardware CPU
exceptions, emulator termination, and failures before the fatal handler or during
shutdown can prevent the report from appearing. The Linux fixture checks handler
ordering and successful, partial, corrupted and failed DOS operations; it does
not establish visibility on a real Amiga screen.

The current v0.0.28 handler and its Linux DOS-operation fixture passed the
combined source/build gates. Actual AmigaDOS fatal-banner appearance and the
reported file path still require the controlled native check. A normal planned
quit, successful startup or emulator window closing does not satisfy that check.
