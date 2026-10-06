# FS-UAE in a persistent Docker development container

This recipe runs FS-UAE in a private Xvfb display with Mesa software rendering. It requires Docker with Linux containers. The [probe script](../tools/fsuae_headless_probe.py) runs a ROM-only smoke check. Supply an A1200 Kickstart ROM you are entitled to use; ROMs and Amiga game data stay outside the image and build context.

The Dockerfile below is a clean-image reproduction recipe and remains unverified as a Docker build. An equivalent Ubuntu 24.04 / FS-UAE 3.1.66 stack was exercised in its deployed environment: llvmpipe, fresh full/cropped PNG captures, a visible Kickstart screen, PTY replies for registers/map/disassembly, a bounded guest-memory read, and synthetic audio capture were observed. Debugger commands synchronized on fresh PTY prompts. This verifies the equivalent runtime stack, not the clean Dockerfile recipe. No game disk, gameplay, game audio, stepping, breakpoints, watchpoint hit, memory writes, or game progress was verified.

## Build the image

Copy the probe script into a new, empty build folder, then create `Dockerfile` there with the contents below. Keep ROMs, disks, saves, work output and backups outside this folder.

Linux:

```sh
mkdir -p fsuae-container
cp tools/fsuae_headless_probe.py fsuae-container/fsuae_headless_probe.py
cd fsuae-container
```

PowerShell:

```powershell
New-Item -ItemType Directory -Force fsuae-container | Out-Null
Copy-Item tools/fsuae_headless_probe.py fsuae-container/fsuae_headless_probe.py
Set-Location fsuae-container
```

Create `Dockerfile` with:

```dockerfile
FROM ubuntu:24.04
ARG FS_UAE_VERSION=3.1.66-2build2
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    ca-certificates fs-uae=${FS_UAE_VERSION} libgl1-mesa-dri libglx-mesa0 mesa-utils \
    pulseaudio pulseaudio-utils python3 x11-utils xdotool xvfb \
    && rm -rf /var/lib/apt/lists/*
COPY fsuae_headless_probe.py /opt/fsuae_headless_probe.py
ENV HOME=/tmp/amiwind-home \
    XDG_RUNTIME_DIR=/tmp/amiwind-runtime \
    DISPLAY=:99 \
    LIBGL_ALWAYS_SOFTWARE=1 \
    SDL_VIDEODRIVER=x11 \
    ALSOFT_DRIVERS=pulse \
    PULSE_SERVER=unix:/tmp/amiwind-runtime/pulse.sock \
    PYTHONDONTWRITEBYTECODE=1
USER 1000:1000
WORKDIR /tmp
ENTRYPOINT ["python3", "/opt/fsuae_headless_probe.py"]
```

`COPY` includes only the public script. Ubuntu's package repositories change over time; save the resulting image ID and package versions with your notes. Build needs network access for Ubuntu packages. Runtime below uses the local image without pulling or networking.

```sh
docker build --platform linux/amd64 --tag amiwind-fsuae:3.1.66 .
docker image inspect amiwind-fsuae:3.1.66 --format '{{.Id}}'
```

## Create the persistent worker

Keep the container and active work files on a fast local SSD/NVMe. Move older, unnecessary archives to a larger secondary data disk to preserve free space on the fast disk. Keep verified backups on a separate physical drive. The worker starts as an idle `sleep` process, so it uses little memory until a probe runs. No host display, audio device, GPU, Docker socket or network is attached. The container has no automatic restart policy.

Linux example (replace these with absolute paths on the intended fast local disk):

```sh
mkdir -p /fast-local/amiwind-fsuae/private-input /fast-local/amiwind-fsuae/work/runs
# Put your own kickstart-3.1-a1200.rom in private-input.
docker create --init --name amiwind-fsuae-dev --restart=no \
  --platform linux/amd64 --network none --read-only --user 1000:1000 \
  --cap-drop ALL --security-opt no-new-privileges --memory 2g --cpus 4 \
  --shm-size 256m --tmpfs /tmp:rw,exec,size=536870912 \
  --mount type=bind,source=/fast-local/amiwind-fsuae/private-input,target=/input,readonly \
  --mount type=bind,source=/fast-local/amiwind-fsuae/work,target=/work \
  --entrypoint sleep amiwind-fsuae:3.1.66 infinity
docker start amiwind-fsuae-dev
docker inspect amiwind-fsuae-dev --format '{{.Id}}'
```

PowerShell example with Docker Desktop Linux containers (change the drive and folders to your fast local disk):

```powershell
New-Item -ItemType Directory -Force C:\fast-local\amiwind-fsuae\private-input,C:\fast-local\amiwind-fsuae\work\runs | Out-Null
# Put your own kickstart-3.1-a1200.rom in private-input.
docker create --init --name amiwind-fsuae-dev --restart=no `
  --platform linux/amd64 --network none --read-only --user 1000:1000 `
  --cap-drop ALL --security-opt no-new-privileges --memory 2g --cpus 4 `
  --shm-size 256m --tmpfs /tmp:rw,exec,size=536870912 `
  --mount type=bind,source=C:/fast-local/amiwind-fsuae/private-input,target=/input,readonly `
  --mount type=bind,source=C:/fast-local/amiwind-fsuae/work,target=/work `
  --entrypoint sleep amiwind-fsuae:3.1.66 infinity
docker start amiwind-fsuae-dev
docker inspect amiwind-fsuae-dev --format '{{.Id}}'
```

Keep `/input` read-only. The `/work` bind mount contains persistent run folders and receipts; give UID/GID 1000 write access inside the container. Do not mount a host tools socket or expose a port. Reuse the same named worker for later runs with `docker start amiwind-fsuae-dev`; its configuration and bind-mounted work files persist. `docker stop amiwind-fsuae-dev` pauses the worker cleanly. The probe starts and cleans up only its own Xvfb, PulseAudio, recorder and FS-UAE child processes.

## Run a fresh probe

Each invocation must use a new directory directly under `/work/runs`. The probe checks the ROM exists and is at least 256 KiB before launching FS-UAE. It rejects a reused output directory.

Linux:

```sh
RUN_ID="probe-$(date -u +%Y%m%dT%H%M%SZ)"
docker exec amiwind-fsuae-dev python3 /opt/fsuae_headless_probe.py --output "/work/runs/$RUN_ID"
```

PowerShell:

```powershell
$runId = 'probe-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
docker exec amiwind-fsuae-dev python3 /opt/fsuae_headless_probe.py --output "/work/runs/$runId"
```

The probe verifies llvmpipe, creates fresh full and cropped FS-UAE PNGs, and enters the console debugger using PTY input after the guest display is ready. The official FS-UAE option page documents F12+D from the emulator window; the probe uses the default Alt+D modifier path. It waits for a fresh debugger prompt before each command and synchronizes `r` (registers), `dm` (memory map), and `d` (disassembly) replies. A separate verified run also completed a bounded memory-read command. The probe captures a synthetic tone through the PulseAudio monitor. Missing screenshots, debugger responses, renderer or nonzero synthetic audio evidence produce a nonzero exit and a JSON failure receipt. Each run keeps its JSON report, PTY log, captures and audio files under its unique work directory.

The audio check only verifies the virtual sink/monitor path. It does not validate FS-UAE guest sound; an earlier run logged dropped emulator audio buffers. The demonstrated environment used Kickstart only and mounted no game disk. It did not establish gameplay, guest audio, memory editing, execution stepping, a breakpoint or watchpoint hit, or game progress after `g`. A running emulator process is not proof that the emulated guest advanced. The stock console debugger pauses emulation while inspecting; it is not a non-pausing live-memory API. Exact command syntax and a diagnostic JIT-off profile are described in [FS-UAE development access](FS-UAE-DEVELOPMENT.md).

For game work, mount your own separate disposable disk copy in a later reviewed configuration. Keep the original read-only and never use the only copy of a save. Captures, logs, dumps and states remain on the host work disk and can contain user-owned game data.

## Persist and back up

Before a Docker Desktop update, save the built image to a backup disk and record its checksum. Example PowerShell (choose a backup disk separate from active work storage):

```powershell
New-Item -ItemType Directory -Force H:\fsuae-backups | Out-Null
docker image save amiwind-fsuae:3.1.66 -o H:\fsuae-backups\amiwind-fsuae-3.1.66.tar
Get-FileHash H:\fsuae-backups\amiwind-fsuae-3.1.66.tar -Algorithm SHA256
```

An image archive saves the image layers only. It does not contain the worker's `/work` bind-mounted runs or `/input`; back those host folders up separately. Save run data to the separate backup disk as well if it must survive a local disk failure. To restore the image archive, use `docker image load -i <backup-file>` and recreate the named worker with the same mounts and options. Do not create the worker with `--rm`; remove it only when you intentionally retire its persistent configuration.

For interactive FS-UAE debugger, serial and save-state workflows, see [FS-UAE development access](FS-UAE-DEVELOPMENT.md). For proposed headless automation and throughput measurement, see [FS-UAE headless development throughput](FS-UAE-HEADLESS-THROUGHPUT.md). For a proposed OpenMW reference-side setup and repeatable matched-view A/B procedure, see [OpenMW headless reference testing](OPENMW-HEADLESS-REFERENCE.md).
