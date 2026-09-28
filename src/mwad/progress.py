"""Plain-text progress that remains visible in terminals, tee logs and CI."""
from contextlib import contextmanager
from pathlib import Path
import os
import shlex
import shutil
import sys
import threading
import time


def section(title):
    """Use the terminal width even when stdout is piped through tee."""
    width = shutil.get_terminal_size((80, 24)).columns
    for stream in (sys.stdout, sys.stderr, sys.stdin):
        try:
            width = os.get_terminal_size(stream.fileno()).columns
            break
        except (OSError, ValueError, AttributeError):
            pass
    rule = '-' * max(1, width)
    print(f'\n{rule}\n{title}\n{rule}', flush=True)


def command_title(command):
    if 'apt-get' in command:
        return 'Refresh APT package lists' if 'update' in command else 'Install missing system packages'
    if 'venv' in command:
        return 'Create isolated Python environment'
    if 'pip' in command:
        return 'Install Python dependencies into the isolated environment'
    if any(str(item).endswith('fetch_toolchain.py') for item in command):
        return 'Download and verify Amiga SDK'
    if any(str(item).endswith('fetch_native.py') for item in command):
        return 'Download and verify ericw map tools' if 'ericw' in command else 'Download, build and test reference QuakeC compiler'
    return 'Run setup command'


@contextmanager
def setup_step(command, number, total):
    title = f'Setup [{number}/{total}]: {command_title(command)}'
    section(title)
    print('Command: ' + shlex.join(command), flush=True)
    interactive = 'sudo' in command or 'apt-get' in command
    if interactive:
        print('sudo/APT may ask for input below. Their output is live; status messages are paused to keep prompts clear.', flush=True)
    with Progress(title, interval=None if interactive else 15):
        yield


class Progress:
    """Report elapsed time even while the current operation is blocked."""
    def __init__(self, label, interval=15, notify=None):
        self.label = label
        self.interval = interval
        self.notify = notify or (lambda message: print(message, flush=True))
        self.detail = ''
        self.stop = threading.Event()

    def update(self, detail):
        self.detail = detail

    def bytes(self, count, total=None):
        elapsed = max(time.monotonic() - self.started, 0.001)
        amount = f'{count / 1048576:.1f} MiB'
        if total:
            amount += f' / {total / 1048576:.1f} MiB ({count * 100 / total:.0f}%)'
        self.update(f'{amount}; {count / 1048576 / elapsed:.2f} MiB/s average')

    def _watch(self):
        while not self.stop.wait(self.interval):
            self.notify(f'{self.label}: still running, {time.monotonic() - self.started:.0f}s elapsed'
                        + (f'; {self.detail}' if self.detail else ''))

    def __enter__(self):
        self.started = time.monotonic()
        self.notify(self.label + '...')
        self.thread = None
        if self.interval is not None:
            self.thread = threading.Thread(target=self._watch, daemon=True)
            self.thread.start()
        return self

    def __exit__(self, kind, value, traceback):
        self.stop.set()
        if self.thread is not None:
            self.thread.join()
        status = 'done' if kind is None else 'stopped'
        self.notify(f'{self.label}: {status} in {time.monotonic() - self.started:.1f}s'
                    + (f'; {self.detail}' if self.detail else ''))


@contextmanager
def live_log(path):
    """Follow a subprocess's log without a pipe that could block the subprocess."""
    stop = threading.Event()
    with Path(path).open(encoding='utf-8', errors='replace') as source:
        def drain():
            while True:
                text = source.read(65536)
                if not text:
                    break
                sys.stdout.write(text)
                sys.stdout.flush()

        def follow():
            while not stop.wait(0.2):
                drain()

        thread = threading.Thread(target=follow, daemon=True)
        thread.start()
        try:
            yield
        finally:
            stop.set()
            thread.join()
            drain()
