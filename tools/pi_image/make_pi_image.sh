#!/bin/bash
# AmiWind Pi boot image: makes AmiWind-Pi.img, a Raspberry Pi OS Lite (64-bit) system that starts straight into
# Amiberry and AmiWind. Run it with sudo on a Raspberry Pi or another arm64 Linux machine, online (docs/PI_BOOT_IMAGE.md).
#
#   sudo tools/pi_image/make_pi_image.sh --kickstart KICK.ROM --hdf AmiWind-vX.hdf [--out DIR]
#        [--amiberry 8.5.0] [--video 720x576@50] [--ssh-key FILE] [--fast-mb 32] [--no-overclock]
#
# By default a Pi 4 runs at 2.0 GHz, the setting AmiWind is measured at (the [pi4] section of config.txt; other
# models ignore it). It needs a heatsink and a fan; --no-overclock keeps the stock clock.
#
# You bring the two things the project can never give you: your own Kickstart 3.1 ROM and the AmiWind image you built
# from your own copy of Morrowind. The script downloads Raspberry Pi OS Lite and Amiberry and checks both against their
# published SHA-256 sums, assembles the system in a work folder (a loop device and a chroot), and writes the finished
# image file. It never writes to a disk: flashing the stick or card is yours (Raspberry Pi Imager or dd).
#
# The image has a third partition, an exFAT drive labelled AMIWIND, that any PC opens: it holds kick.rom and the
# AmiWind image. At every start the newest AmiWind-v*.hdf on it is used, so a new AmiWind version is one file copy.
set -euo pipefail

KICK= HDF= OUT=$PWD/pi-image-out AMIBERRY=8.5.0 VIDEO=720x576@50 SSH_KEY= FAST_MB=32 OVERCLOCK=1
HERE=$(cd "$(dirname "$0")" && pwd)
die() { echo "make_pi_image: $*" >&2; exit 1; }
while [ $# -gt 0 ]; do
  case "$1" in
    --kickstart) KICK=$2; shift 2 ;;
    --hdf) HDF=$2; shift 2 ;;
    --out) OUT=$2; shift 2 ;;
    --amiberry) AMIBERRY=$2; shift 2 ;;
    --video) VIDEO=$2; shift 2 ;;
    --ssh-key) SSH_KEY=$2; shift 2 ;;
    --fast-mb) FAST_MB=$2; shift 2 ;;
    --no-overclock) OVERCLOCK=0; shift ;;
    -h|--help) sed -n '2,18p' "$0"; exit 0 ;;
    *) die "unknown option $1 (see --help)" ;;
  esac
done

# ---- checks first, before anything is downloaded or touched
[ "$(id -u)" = 0 ] || die "run it with sudo (it mounts the image through a loop device)"
[ "$(uname -m)" = aarch64 ] || die "run it on a Raspberry Pi or another arm64 Linux machine (the chroot runs the image's own programs)"
[ -f "$KICK" ] || die "--kickstart: no such file: $KICK"
[ -f "$HDF" ] || die "--hdf: no such file: $HDF"
case "$(basename "$HDF")" in AmiWind-v*.hdf) ;; *) die "--hdf: the file name must be AmiWind-v<version>.hdf (the start banner reads the version from it)" ;; esac
[ "$(stat -c %s "$KICK")" = 524288 ] || die "--kickstart: a Kickstart 3.1 ROM is 524288 bytes; $KICK is not"
case "$FAST_MB" in 32|64|128|256) ;; *) die "--fast-mb: 32, 64, 128 or 256 (32 MB of Fast RAM is AmiWind's minimum)" ;; esac
[ -z "$SSH_KEY" ] || [ -f "$SSH_KEY" ] || die "--ssh-key: no such file: $SSH_KEY"
for t in curl xz sha256sum parted losetup e2fsck resize2fs mkfs.exfat partprobe chroot python3; do
  command -v "$t" >/dev/null || die "missing tool: $t (on Raspberry Pi OS: sudo apt install curl xz-utils parted e2fsprogs exfatprogs python3)"
done

W=$OUT/work; R=$W/root; mkdir -p "$W/dl" "$R"
LOOP=
cleanup() {
  for m in dev/pts dev proc sys etc/resolv.conf boot/firmware; do umount "$R/$m" 2>/dev/null || true; done
  umount "$R" 2>/dev/null || true
  [ -z "$LOOP" ] || losetup -d "$LOOP" 2>/dev/null || true
}
trap cleanup EXIT

# ---- Raspberry Pi OS Lite 64-bit: the "latest" link names the dated image; its .sha256 sits beside it
URL=$(curl -fsSLI -o /dev/null -w '%{url_effective}' https://downloads.raspberrypi.com/raspios_lite_arm64_latest)
XZ=$W/dl/$(basename "$URL")
[ -f "$XZ" ] || curl -fL --progress-bar -o "$XZ" "$URL"
want=$(curl -fsSL "$URL.sha256" | cut -d' ' -f1)
got=$(sha256sum "$XZ" | cut -d' ' -f1)
[ "$got" = "$want" ] || die "Raspberry Pi OS: SHA-256 $got, published $want"
echo "Raspberry Pi OS Lite: $(basename "$XZ"), SHA-256 OK"

# ---- Amiberry for Debian trixie arm64 from its GitHub release, checked against the release's SHA256SUMS
REL=https://github.com/BlitterStudio/amiberry/releases/download/v$AMIBERRY
ZIP=amiberry-v$AMIBERRY-debian-trixie-arm64.zip
[ -f "$W/dl/$ZIP" ] || curl -fL --progress-bar -o "$W/dl/$ZIP" "$REL/$ZIP"
curl -fsSL -o "$W/dl/SHA256SUMS" "$REL/SHA256SUMS"
want=$(awk -v n="$ZIP" '{f=$2; sub(/^\*/,"",f)} f==n{print $1}' "$W/dl/SHA256SUMS")
got=$(sha256sum "$W/dl/$ZIP" | cut -d' ' -f1)
[ -n "$want" ] && [ "$got" = "$want" ] || die "Amiberry: SHA-256 $got, SHA256SUMS ${want:-has no line for $ZIP}"
rm -rf "$W/dl/amiberry"; python3 -m zipfile -e "$W/dl/$ZIP" "$W/dl/amiberry"
DEB=$(find "$W/dl/amiberry" -name 'amiberry_*_arm64.deb' | head -n 1)
[ -n "$DEB" ] || die "Amiberry: no amiberry_*_arm64.deb in $ZIP"
echo "Amiberry $AMIBERRY: $(basename "$DEB"), SHA-256 OK"

# ---- the image: root grown by 2 GiB, then the AMIWIND data partition (the AmiWind image plus 512 MiB)
IMG=$OUT/AmiWind-Pi.img
echo "decompressing to $IMG"; xz -dc "$XZ" > "$IMG"
end2=$(parted -sm "$IMG" unit MiB print | awk -F: '$1==2{sub(/MiB/,"",$3); print int($3)}')
data=$(( $(stat -c %s "$HDF") / 1048576 + 512 ))
truncate -s $(( (end2 + 2048 + data + 8) * 1048576 )) "$IMG"
parted -s "$IMG" resizepart 2 $(( end2 + 2048 ))MiB
parted -s "$IMG" mkpart primary $(( end2 + 2048 ))MiB 100%
LOOP=$(losetup -fP --show "$IMG"); partprobe "$LOOP" 2>/dev/null || true
e2fsck -pf "${LOOP}p2" || [ $? -le 1 ]
resize2fs "${LOOP}p2"
mkfs.exfat -L AMIWIND "${LOOP}p3" >/dev/null
mount "${LOOP}p2" "$R"; mount "${LOOP}p1" "$R/boot/firmware"
for m in dev dev/pts proc sys; do mount --bind "/$m" "$R/$m"; done
mount --bind /etc/resolv.conf "$R/etc/resolv.conf"

# ---- Amiberry and the EGL libraries SDL3's KMSDRM loads by itself at run time (without them it quits with status 0)
install -d "$R/var/cache/amiwind"; cp "$DEB" "$R/var/cache/amiwind/amiberry.deb"
chroot "$R" /bin/sh -c 'apt-get update -q && DEBIAN_FRONTEND=noninteractive apt-get install -y -q /var/cache/amiwind/amiberry.deb libegl1 libegl-mesa0 libgles2 exfatprogs'
rm -rf "$R/var/cache/amiwind"
chroot "$R" dpkg -s amiberry | grep -E '^(Package|Version):'

# ---- the amiwind user (by name: Pi OS keeps a disabled pi user as uid 1000), no first-boot wizard, no cloud-init
chroot "$R" id amiwind >/dev/null 2>&1 || chroot "$R" useradd -m -s /bin/bash -G video,render,input,audio,plugdev amiwind
chroot "$R" passwd -l amiwind >/dev/null
chroot "$R" systemctl disable userconfig.service >/dev/null 2>&1 || true
[ -d "$R/etc/cloud" ] && touch "$R/etc/cloud/cloud-init.disabled"
if [ -n "$SSH_KEY" ]; then
  install -d -m 700 "$R/home/amiwind/.ssh"; install -m 600 "$SSH_KEY" "$R/home/amiwind/.ssh/authorized_keys"
  printf 'PasswordAuthentication no\nKbdInteractiveAuthentication no\n' > "$R/etc/ssh/sshd_config.d/10-amiwind.conf"
  chroot "$R" systemctl enable ssh.service >/dev/null 2>&1 || true
  echo "SSH: on, key only, user amiwind"
fi
UID_AW=$(chroot "$R" id -u amiwind); GID_AW=$(chroot "$R" id -g amiwind)

# ---- the AMIWIND drive: mounted at /opt/amiwind/data, owned by amiwind; the Kickstart and the AmiWind image on it
install -d "$R/opt/amiwind/data"
echo "LABEL=AMIWIND /opt/amiwind/data exfat defaults,nofail,uid=$UID_AW,gid=$GID_AW,umask=022 0 0" >> "$R/etc/fstab"
mount "${LOOP}p3" "$R/opt/amiwind/data"
cp "$KICK" "$R/opt/amiwind/data/kick.rom"
cp "$HDF" "$R/opt/amiwind/data/"
cmp -s "$HDF" "$R/opt/amiwind/data/$(basename "$HDF")" || die "the AmiWind image did not copy intact"
umount "$R/opt/amiwind/data"

# ---- the preset (Amiberry's default configuration), with the Fast RAM asked for
install -d "$R/home/amiwind/.config/amiberry/conf"
sed "s/^z3mem_size=.*/z3mem_size=$FAST_MB/" "$HERE/amiwind.uae" > "$R/home/amiwind/.config/amiberry/conf/default.uae"
chroot "$R" chown -R amiwind:amiwind /home/amiwind

# ---- the start: pick the newest AmiWind image, show the banner, then Amiberry on tty1 through KMSDRM
cat > "$R/usr/local/bin/amiwind-start" <<'EOF'
#!/bin/bash
# Before Amiberry takes the screen: link the newest AmiWind-v*.hdf on the AMIWIND drive, check the Kickstart, and show
# "Starting AmiWind v<version> on Amiberry <version> on the Raspberry Pi <model>" on tty1 (a failed start never looks
# like a hang).
T=/dev/tty1; D=/opt/amiwind/data
cols=$(stty size < "$T" 2>/dev/null | cut -d' ' -f2); line=$(printf '%*s' "${cols:-80}" '' | tr ' ' '-')
say() { printf '\033[2J\033[H\n%s\n  %s\n%s\n' "$line" "$1" "$line" > "$T"; }
hdf=$(ls "$D"/AmiWind-v*.hdf 2>/dev/null | sort -V | tail -n 1)
[ -n "$hdf" ] || { say "No AmiWind-v*.hdf on the AMIWIND drive: copy your AmiWind image onto it."; sleep 30; exit 1; }
[ -f "$D/kick.rom" ] || { say "No kick.rom on the AMIWIND drive: copy your Kickstart 3.1 ROM onto it as kick.rom."; sleep 30; exit 1; }
ln -sfn "$hdf" /opt/amiwind/current.hdf
aw=$(basename "$hdf" .hdf); aw=${aw#AmiWind-v}
ab=$(dpkg-query -W -f='${Version}' amiberry 2>/dev/null | cut -d+ -f1)
pi=$(tr -d '\0' < /proc/device-tree/model 2>/dev/null | sed 's/^Raspberry Pi //')
say "Starting AmiWind v$aw on Amiberry $ab on the Raspberry Pi $pi"
sleep 2
EOF
chmod 755 "$R/usr/local/bin/amiwind-start"
cat > "$R/etc/systemd/system/amiwind.service" <<'EOF'
[Unit]
Description=AmiWind on Amiberry (straight to the Amiga at boot)
After=systemd-user-sessions.service sound.target opt-amiwind-data.mount
Conflicts=getty@tty1.service
StartLimitIntervalSec=120
StartLimitBurst=3

[Service]
User=amiwind
Group=amiwind
SupplementaryGroups=video render input audio
PAMName=login
TTYPath=/dev/tty1
StandardInput=tty
StandardOutput=journal
Environment=SDL_VIDEODRIVER=kmsdrm
WorkingDirectory=/home/amiwind
ExecStartPre=+/usr/local/bin/amiwind-start
ExecStart=/usr/bin/amiberry -G -f /home/amiwind/.config/amiberry/conf/default.uae
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
chroot "$R" systemctl enable amiwind.service >/dev/null
chroot "$R" systemctl disable getty@tty1.service >/dev/null 2>&1 || true

# ---- a console on tty2 (Ctrl+Alt+F2) for fixing things at the Pi itself; the hardware watchdog; a kept journal
install -d "$R/etc/systemd/system/getty@tty2.service.d"
printf '[Service]\nExecStart=\nExecStart=-/sbin/agetty --autologin amiwind --noclear %%I $TERM\n' > "$R/etc/systemd/system/getty@tty2.service.d/autologin.conf"
chroot "$R" systemctl enable getty@tty2.service >/dev/null 2>&1 || true
install -d "$R/etc/systemd/system.conf.d"
printf '[Manager]\nRuntimeWatchdogSec=15s\nRebootWatchdogSec=2min\n' > "$R/etc/systemd/system.conf.d/10-watchdog.conf"
install -d "$R/var/log/journal"

# ---- a quiet boot, and the screen at 576p 50 Hz (the Amiga's PAL rate, not the monitor's own mode)
C=$R/boot/firmware/cmdline.txt
for w in quiet loglevel=3 logo.nologo vt.global_cursor_default=0 "video=HDMI-A-1:$VIDEO"; do
  grep -qw -- "$w" "$C" || sed -i "1 s|\$| $w|" "$C"
done
grep -q '^disable_splash=1' "$R/boot/firmware/config.txt" || echo 'disable_splash=1' >> "$R/boot/firmware/config.txt"
grep -q '^dtparam=watchdog=on' "$R/boot/firmware/config.txt" || echo 'dtparam=watchdog=on' >> "$R/boot/firmware/config.txt"
# the default (--no-overclock turns it off): a Pi 4 at 2.0 GHz, the setting AmiWind is measured at; needs a heatsink
# and a fan; never force_turbo
if [ "$OVERCLOCK" = 1 ] && ! grep -q '^# AmiWind overclock' "$R/boot/firmware/config.txt"; then
  printf '\n# AmiWind overclock (Pi 4 only; needs a heatsink and a fan)\n[pi4]\narm_freq=2000\nover_voltage=6\ngpu_freq=750\n[all]\n' >> "$R/boot/firmware/config.txt"
  echo "overclock: Pi 4 at 2.0 GHz written to config.txt"
fi
chroot "$R" /usr/bin/amiberry --dump-config -f /home/amiwind/.config/amiberry/conf/default.uae 2>/dev/null \
  | grep -E '^(cachesize|cpu_threaded|z3mem_size|cycle_exact)=' || true

sync; cleanup; trap - EXIT
sha256sum "$IMG" > "$IMG.sha256"
echo
echo "done: $IMG ($(du -h "$IMG" | cut -f1)), SHA-256 in $IMG.sha256"
echo "Flash it to a USB stick or SD card (Raspberry Pi Imager: Use custom; or dd), then boot the Pi from it."
echo "Never share this image: it holds your Kickstart and your AmiWind image."
