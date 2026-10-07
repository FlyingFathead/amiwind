# BUILD-WINDOWS-DOCKER-SLOW-31: Docker steps on Windows folders are slow

## Status: 7 October 2026

Open (workflow). Measured; mitigation in use for new builds.

## Symptom

On a Windows host, building a playtest image or making capture copies inside
Docker takes many minutes: every multi-gigabyte disk image written or read
inside the container through a Windows folder moves at hard-disk speed.

## Where

Docker Desktop on WSL2, with the work folder bind-mounted from the Windows
filesystem (NTFS) into the Linux container.

## How it happened

WSL2 and Hyper-V add little overhead for CPU, memory and files kept on the
Linux side. Files on the Windows side are served to Linux over a file-sharing
bridge between the two systems, and that bridge is slow for large writes.
Measured on the development machine: 1 GiB written from the container to the
Windows folder at 225 MB/s; the same kind of disk image copied natively on
Windows at about 1.9 GB/s. A playtest build moves three to five 5.6 GB disk
images (image, staging, archive, extraction).

## Why it was not caught

Builds were judged by total time; the time per step was not measured until a
screenshot round took about 30 minutes.

## Reproduction

Inside a Docker container on Windows, `dd if=/dev/zero of=<bind-mounted
Windows folder>/test bs=4M count=256 conv=fsync`; compare with a native
Windows copy of a file of the same size.

## Repair

Keep large files on one side of the bridge: copy whole disk images with the
host's own copy, and keep container scratch work (images, play copies,
archives) on a Docker volume, which lives on the Linux side; only the
finished archive crosses to Windows once. Installing Linux on the host is not
needed.

## Verification

Pending: build and capture timings before and after.

## Prevention

Time every step of a build; any step that moves a whole disk image through a
Windows folder from a container is a defect.
