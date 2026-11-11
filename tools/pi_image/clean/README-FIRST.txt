AmiWind for the Raspberry Pi 4B: ready-to-write drive image
============================================================

1. Write the .img file in this ZIP to a USB stick or SD card of 16 GB or more (Raspberry Pi Imager: "Use custom";
   or dd on Linux). Do not apply any of the Imager's settings (user, wifi, SSH): the image needs none.
2. Copy your own Kickstart 3.1 ROM (A1200, 524288 bytes) onto the drive called AMIWIND as kick.rom. Any PC opens
   that drive. The image holds no Kickstart; you supply it, as with the playtest launcher.
3. Boot the Pi 4B from it. The FIRST start installs Amiberry from the image (about two minutes, no network needed)
   and restarts once. Then every start goes straight into AmiWind.

- AmiWind needs 32 MB of Fast RAM; the preset gives it 32 MB, the JIT and a 68040 with FPU.
- A newer AmiWind: copy its AmiWind-v<version>.hdf onto the AMIWIND drive; the newest one is used. Saved games live
  inside each .hdf.
- The image has no password, no SSH, no wifi and no network accounts. A console for fixing things is on Ctrl+Alt+F2
  (user amiwind, no administrator rights).
- The Pi runs at its stock clock. More speed: in config.txt on the boot drive, add under [pi4]: arm_freq=2000,
  over_voltage=6, gpu_freq=750 (needs a heatsink and a fan; AmiWind's own measurements are taken at 2.0 GHz).
- Sound goes to the 3.5 mm jack by default.
