# TOOLING-HEADLESS-BROWSER-31: No headless browser in the Docker images: Toolkit screenshots cannot be made in Docker

## Status: 8 October 2026

Open. Found by the Toolkit map metrics layer work.

## Symptom

Evidence frames of the Toolkit (map layers, 3D inspector) have to be taken by hand or in a
small desktop browser pane; no gate or job can render them.

## Where

The Docker images used by the gate and jobs.

## How it happened

The images were built for the converter and engine only.

## Why it was not caught

Toolkit evidence was always taken interactively.

## Reproduction

Look for chromium or firefox in the images.

## Repair

Not yet: a separate image with a headless browser (built with network, run offline) for Toolkit screenshots and page tests.

## Verification

Pending.

## Prevention

Toolkit page checks run in the gate with that image.
