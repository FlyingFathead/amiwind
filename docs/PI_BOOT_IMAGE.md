# Your own AmiWind boot stick for the Raspberry Pi

_Last updated with AmiWind v0.0.56-dev1 (29 October 2026)._

A USB stick or SD card that starts a Raspberry Pi straight into AmiWind: power on, a short line saying
"Starting AmiWind v... on Amiberry ... on the Raspberry Pi ...", and you are on the prison ship. It is a plain
Raspberry Pi OS Lite underneath, with Amiberry and a service that starts it at boot; inside Amiberry your own
Kickstart boots your own AmiWind image. The settings are the ones we measured on a Pi 4B on 29 October 2026
([what each one gave](REAL_HARDWARE.md#raspberry-pi-with-amiberry)).

> ⚠️ **AmiWind is measured on a Pi 4 at 2.0 GHz, and the image runs a Pi 4 at 2.0 GHz by default.** The settings
> are `arm_freq=2000`, `over_voltage=6`, `gpu_freq=750` in the `[pi4]` section of `config.txt` (other models ignore
> them; never `force_turbo`). Overclocking is at your own risk: use it only with a heatsink **and** a fan, and check
> the temperature (`vcgencmd measure_temp`) and throttling (`vcgencmd get_throttled`, `0x0` = none) the first time.
> Our test Pi held 2.0 GHz at 43 to 46 C with both. Without a fan, make the image with `--no-overclock`: it runs at
> the stock 1.5 GHz, slower.

## What you need

- **A Raspberry Pi 4** (the one measured; a Pi 5 should be faster, a Pi 3 is too slow), a monitor or TV on HDMI, a
  keyboard and a mouse, and a USB stick or SD card of 16 GB or more.
- **Your own Kickstart 3.1 ROM** (A1200, 512 KB), legally from Cloanto's [Amiga Forever](https://www.amigaforever.com/)
  or read from an Amiga you own.
- **Your own AmiWind image** `AmiWind-v<version>.hdf`, built from your own copy of The Elder Scrolls III: Morrowind
  ([building](../README.md)). AmiWind needs 32 MB of Fast RAM; the image's preset gives it that.
- **A Linux machine with an arm64 processor to make the image on**, online, with `sudo`: the Pi itself running
  Raspberry Pi OS from another card works. The script runs the image's own programs in a chroot, so an x86 PC cannot
  make it.

## Make the image

On the arm64 Linux machine, in a copy of this repository:

```bash
sudo apt install curl xz-utils parted e2fsprogs exfatprogs python3
```

```bash
sudo tools/pi_image/make_pi_image.sh --kickstart /path/to/kick31.rom --hdf /path/to/AmiWind-v0.0.56-dev1.hdf
```

It downloads Raspberry Pi OS Lite (64-bit) and Amiberry, checks each against its published SHA-256, assembles the
system in `pi-image-out/work`, and writes `pi-image-out/AmiWind-Pi.img` with its SHA-256 beside it. Options:

| Option | Default | What it does |
| --- | --- | --- |
| `--kickstart FILE` | (needed) | your Kickstart 3.1 ROM, 524288 bytes |
| `--hdf FILE` | (needed) | your AmiWind image, named `AmiWind-v<version>.hdf` |
| `--no-overclock` | (overclock on) | keep a Pi 4 at its stock 1.5 GHz; without it a Pi 4 runs at 2.0 GHz (read the warning above) |
| `--fast-mb N` | 32 | Zorro III Fast RAM: 32, 64, 128 or 256 MB |
| `--video MODE` | `720x576@50` | the HDMI mode; 576p at 50 Hz matches the Amiga's PAL picture; if your monitor lacks it, try `1280x720@50` |
| `--amiberry VER` | `8.5.0` | the Amiberry release |
| `--ssh-key FILE` | none | your public SSH key: SSH on for the user `amiwind`, key only |
| `--out DIR` | `./pi-image-out` | where the work folder and the image go |

The image holds your Kickstart and your AmiWind image: never share it, only the steps.

## Flash it and start

Write `AmiWind-Pi.img` to the stick or card with [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
("Use custom") or `dd`. Imager may offer to customise the system: say no, the image is set up already. Put it in
the Pi and switch on. The first start takes a little longer. F12 opens Amiberry's settings; Ctrl+Alt+F2 gives a
console on the Pi (user `amiwind`) for fixing things.

## A new AmiWind version

The stick has a drive labelled **AMIWIND** that any PC opens (exFAT). It holds `kick.rom` and your
`AmiWind-v*.hdf`. Copy a newer `AmiWind-v<version>.hdf` onto it: at the next start the newest one is used, and the
start line names it. Remove the old one when you no longer need it. Your saved games are inside the AmiWind image,
so a new image starts without them.

## What is in it

What the first stick taught us, all built in:

- Amiberry with the EGL libraries its display needs (without them it quits silently at start).
- Every cycle-exact switch off: Amiberry's A1200 default is cycle-exact, which switches the JIT off.
- The JIT with the FPU, translation cache 16384 KB (the maximum: a larger number is read as 0, which switches the
  JIT off), memory access `direct`.
- `cpu_threaded=false`: the 68k CPU on its own thread was much faster in play but ended a load in an engine error
  ([SPRITE-BAD-TYPE-THREADED-56](bugs/SPRITE-BAD-TYPE-THREADED-56.md)); it stays off until that is settled.
- The screen at 576p 50 Hz instead of the monitor's own mode: no large scaling, and the refresh matches the Amiga's.
- A start line on the screen before Amiberry takes it, so a failed start never looks like a hang; a clear message
  if `kick.rom` or the AmiWind image is missing.
- The hardware watchdog (a hung Pi reboots by itself), a kept system journal, a console on tty2, a quiet boot.
- Sound to the 3.5 mm jack (Pi OS Lite's default). For HDMI sound, set the HDMI card as the default in
  `/etc/asound.conf`.

## When something goes wrong

- **A black screen with no start line:** the monitor may not take 576p50; make the image again with
  `--video 1280x720@50`, or edit `video=` in `cmdline.txt` on the boot partition from any PC.
- **The start line, then back to the console:** Amiberry's log is in the journal: on tty2,
  `journalctl -u amiwind -b`.
- **A load that never ends:** check `cpu_threaded=false` in `/home/amiwind/.config/amiberry/conf/default.uae`.
- **Slow in some places:** expected for now: rooms full of detailed objects (the prison ship's hold, Seyda Neen, the
  Dwemer ruins) are the slowest ([PRISON-SHIP-RENDER-COST-56](bugs/PRISON-SHIP-RENDER-COST-56.md)).
