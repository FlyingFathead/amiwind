"""Linux-only real mixer and Paula-driver clock checks with synthetic devices."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get('AMIWIND_RUNTIME_SOURCE', str(ROOT/'engine/aga')))/'src'
FLAGS = ['-std=gnu89', '-fsanitize=undefined,float-cast-overflow',
         '-fno-sanitize-recover=all', '-ffunction-sections', '-fdata-sections']


@unittest.skipIf(os.name == 'nt', 'native fixtures run in the Linux Docker gate')
@unittest.skipUnless(shutil.which('cc'), 'a Linux C compiler is required')
class AudioClockTests(unittest.TestCase):
    def checked(self, args):
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        return result.stdout

    def test_slow_asset_reads_preserve_loading_music_and_ordinary_read_size(self):
        with tempfile.TemporaryDirectory() as scratch:
            directory = Path(scratch)
            objects = []
            for name, source, defines in (
                    ('fixture', ROOT/'tests/aga_load_music_io_test.c', []),
                    ('common', ROOT/'tests/aga_load_music_common.c', []),
                    ('scheduler', SOURCE/'snd_dma.c', ['-DAMIGA']),
                    ('mixer', SOURCE/'snd_mix.c', []),
                    ('music', SOURCE/'aw_music.c', [])):
                obj = directory/(name+'.o')
                self.checked(['cc', *FLAGS, *defines, '-I'+str(SOURCE), '-c', str(source), '-o', str(obj)])
                objects.append(str(obj))
            exe = str(directory/'load-music-check')
            self.checked(['cc', *FLAGS, '-Wl,--gc-sections', '-Wl,--wrap=fread',
                          *objects, '-lm', '-o', exe])
            for reader in ('model', 'common'):
                for rate, mode in ((32768, 'loading'), (102400, 'loading'), (32768, 'ordinary')):
                    with self.subTest(reader=reader, rate=rate, mode=mode):
                        run = directory/(reader+'-'+str(rate)+'-'+mode)
                        run.mkdir()
                        result = subprocess.run([exe, str(rate), reader, mode, '4096'], cwd=run,
                                                capture_output=True, text=True)
                        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)

    def test_absolute_clock_recovers_actual_mixer_after_stalls_and_reset(self):
        with tempfile.TemporaryDirectory() as scratch:
            directory = Path(scratch)
            objects = []
            for name, source, defines in (
                    ('fixture', ROOT/'tests/aga_audio_clock_mixer_test.c', ['-DAMIGA']),
                    ('scheduler', SOURCE/'snd_dma.c', ['-DAMIGA']),
                    ('mixer', SOURCE/'snd_mix.c', [])):
                obj = directory/(name+'.o')
                self.checked(['cc', *FLAGS, *defines, '-I'+str(SOURCE), '-c', str(source), '-o', str(obj)])
                objects.append(str(obj))
            exe = str(directory/'mixer-check')
            self.checked(['cc', *FLAGS, '-Wl,--gc-sections', '-Wl,--wrap=S_CancelSceneVoice',
                          *objects, '-lm', '-o', exe])
            for case in ('551', '1323', '16584', '32968', '55125', 'reset', 'epoch'):
                with self.subTest(case=case):
                    self.checked([exe, case])

    def test_actual_driver_clock_follows_elapsed_time_without_polling(self):
        with tempfile.TemporaryDirectory() as scratch:
            directory = Path(scratch)
            for name in ('proto/exec.h', 'proto/graphics.h', 'graphics/gfxbase.h', 'devices/audio.h'):
                target = directory/name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('/* Declarations supplied by synthetic fixture header. */\n')
            exe = str(directory/'device-check')
            self.checked(['cc', *FLAGS, '-DAMIGA', '-I'+str(directory), '-I'+str(SOURCE),
                          '-include', str(ROOT/'tests/aga_audio_device_stub.h'),
                          str(ROOT/'tests/aga_audio_device_clock_test.c'), '-lm', '-o', exe])
            self.checked([exe])
