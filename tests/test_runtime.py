import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mwad.audit import terrain_packet


class RuntimePacket(unittest.TestCase):
    def test_c_reader_against_python_packets(self):
        cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
        if not cc:
            self.skipTest("C compiler unavailable; install GCC or Clang to check the C reader")
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            exe = tmp / ("packet-test.exe" if os.name == "nt" else "packet-test")
            subprocess.run([cc, "-std=c99", "-Wall", "-Wextra", "-Werror",
                            "-I", str(ROOT / "runtime/include"), str(ROOT / "runtime/src/terrain_packet.c"),
                            str(ROOT / "tests/runtime_packet_test.c"), "-o", str(exe)], check=True, capture_output=True)
            land = {"heights": [[(y-x)*8 for x in range(65)] for y in range(65)],
                    "materials": [[7]*16 for _ in range(16)]}
            for stride in (1, 2, 4, 8):
                packet = tmp / f"stride-{stride}.mwt"
                packet.write_bytes(terrain_packet(land, -2, -9, 0, 0, stride))
                subprocess.run([str(exe), str(packet)], check=True, capture_output=True)
