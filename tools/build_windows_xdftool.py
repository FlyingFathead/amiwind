"""Run xdftool command queues within Windows' CreateProcess argument limit."""
import subprocess

# The Windows limit is 32767 UTF-16 units including the terminating NUL.
# Leave room for launcher overhead rather than operating at that boundary.
MAX_COMMAND_UNITS = 24000


def command_units(command):
    return len(subprocess.list2cmdline(command).encode('utf-16-le')) // 2 + 1


def batches(command, limit=MAX_COMMAND_UNITS):
    """Split only between complete '+'-delimited xdftool operations."""
    command = list(map(str, command))
    if len(command) < 3:
        raise ValueError('Expected xdftool executable, image and commands')
    if command_units(command) <= limit:
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
        if command_units(prefix + group) > limit:
            raise ValueError('One xdftool operation exceeds the Windows command limit')
    batch = prefix[:]
    for group in groups:
        candidate = batch + (['+'] if len(batch) > 2 else []) + group
        if command_units(candidate) > limit:
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
