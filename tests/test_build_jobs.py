import unittest
from pathlib import Path
from unittest.mock import patch
import build
from build_jobs import auto_jobs, available_memory

class JobTests(unittest.TestCase):
    def test_auto_honours_affinity_and_container_quota(self):
        with patch('build_jobs.os.cpu_count', return_value=32), \
             patch('build_jobs.os.sched_getaffinity', return_value={0, 1, 2, 3}), \
             patch.object(Path, 'read_text', return_value='200000 100000'):
            self.assertEqual(auto_jobs(), 2)
        with patch('build_jobs.os.cpu_count', return_value=None), \
             patch('build_jobs.os.sched_getaffinity', side_effect=OSError), \
             patch.object(Path, 'read_text', side_effect=OSError):
            self.assertEqual(auto_jobs(), 1)

    def test_single_and_explicit_jobs_reach_compilers(self):
        for option in (['-j', '1'], ['-j1'], ['--jobs', '1'], ['--j', '1'], ['--single-thread']):
            args = build.parser().parse_args(option)
            args.data_files=Path('/owned');args.sdk=Path('/sdk')
            tools={n:'/tools/'+n for n in ('qbsp','vis','light','qcc','ffmpeg','xdftool','rdbtool')}
            for name, command in build.commands(args, tools, Path('/out')):
                if name in ('engine','interior','bsp','scenery','scene','census','intro','character','music'):
                    self.assertEqual(command[command.index('--jobs')+1], '1')
            engine=dict(build.dry_run_commands(args,Path('/out')))['engine']
            self.assertEqual(engine[engine.index('--jobs')+1], '1')
        with self.assertRaises(SystemExit):build.parser().parse_args(['-j','0'])

    def test_process_cpu_count_error_uses_remaining_limits(self):
        with patch('build_jobs.os.cpu_count', return_value=8), \
             patch('build_jobs.os.process_cpu_count', side_effect=OSError, create=True), \
             patch('build_jobs.os.sched_getaffinity', return_value={0, 1}, create=True), \
             patch.object(Path, 'read_text', side_effect=OSError):
            self.assertEqual(auto_jobs(), 2)

    def test_auto_limits_workers_for_memory_and_keeps_one_fallback(self):
        with patch('build_jobs.os.cpu_count',return_value=32), \
             patch('build_jobs.os.sched_getaffinity',return_value=set(range(32))), \
             patch.object(Path,'read_text',side_effect=OSError):
            with patch('build_jobs.available_memory',return_value=4*1024**3):
                self.assertEqual(auto_jobs(),6)
            with patch('build_jobs.available_memory',return_value=128*1024**2):
                self.assertEqual(auto_jobs(),1)

    def test_memory_uses_tighter_container_limit(self):
        values={'/proc/meminfo':'MemAvailable: 8388608 kB\n',
                '/sys/fs/cgroup/memory.max':str(4*1024**3),
                '/sys/fs/cgroup/memory.current':str(3*1024**3)}
        def read(path):
            if str(path) not in values:raise OSError
            return values[str(path)]
        with patch.object(Path,'read_text',read):
            self.assertEqual(available_memory(),1024**3)
