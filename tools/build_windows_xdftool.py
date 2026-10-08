"""Run xdftool command queues within the operating system's argument limit.

Windows: CreateProcess (32767 UTF-16 units). POSIX: execve's ARG_MAX (2 MiB on
Linux, environment included); one image with every boot file in a single command
exceeded it once the world flora sprites were staged.
"""
import os
import subprocess

# The Windows limit is 32767 UTF-16 units including the terminating NUL.
# Leave room for launcher overhead rather than operating at that boundary.
MAX_COMMAND_UNITS = 24000
# POSIX: argument bytes (with NUL terminators) per invocation, far below ARG_MAX.
MAX_POSIX_BYTES = 256 * 1024


def command_units(command):
    return len(subprocess.list2cmdline(command).encode('utf-16-le')) // 2 + 1


def posix_bytes(command):
    return sum(len(os.fsencode(str(argument))) + 1 for argument in command)


def batches(command, limit=MAX_COMMAND_UNITS, measure=command_units):
    """Split only between complete '+'-delimited xdftool operations.

    Every batch after the first reopens the same image and continues the queue
    in order, so the image holds the same operations as one long command."""
    command = list(map(str, command))
    if len(command) < 3:
        raise ValueError('Expected xdftool executable, image and commands')
    if measure(command) <= limit:
        yield command
        return
    prefix, tail = command[:2], command[2:]
    groups, current = [], []
    for argument in tail:
        if argument == '+':
            if not current:
                raise ValueError('Empty xdftool command')
            groups.append(current)
            current = []
        else:
            current.append(argument)
    if not current:
        raise ValueError('Empty trailing xdftool command')
    groups.append(current)
    # Validate every operation before modifying the image.
    for group in groups:
        if measure(prefix + group) > limit:
            raise ValueError('One xdftool operation exceeds the Windows command limit'
                             if measure is command_units else 'One xdftool operation exceeds the argument limit')
    batch = prefix[:]
    for group in groups:
        candidate = batch + (['+'] if len(batch) > 2 else []) + group
        if measure(candidate) > limit:
            yield batch
            batch = prefix + group
        else:
            batch = candidate
    if len(batch) > 2:
        yield batch


def run(command):
    """Keep command order and fail immediately if any batch fails."""
    for batch in batches(command):
        subprocess.run(batch, check=True)


def run_any(command):
    """The builder's xdftool runner on every host: bounded batches, in order."""
    if os.name == 'nt':
        return run(command)
    for batch in batches(command, MAX_POSIX_BYTES, posix_bytes):
        subprocess.run(batch, check=True)
