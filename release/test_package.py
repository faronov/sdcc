# SPDX-License-Identifier: GPL-2.0-or-later
import json
from pathlib import Path
import tempfile
import unittest

from build import manifest
from self_test import BINS, LIBS, check_manifest, check_trace


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for path in ([self.root / "bin" / name for name in BINS] +
                     [self.root / "share/sdcc/lib/large" / name for name in LIBS]):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"synthetic fixture, never executed")
        manifest(self.root)

    def test_manifest_rejects_missing_modified_mode_and_symlinked_files(self):
        path = self.root / "bin/sdcc"
        check_manifest(self.root)
        for mutation in ("missing", "content", "mode", "symlink"):
            with self.subTest(mutation=mutation):
                original = path.read_bytes()
                if mutation == "missing":
                    path.unlink()
                elif mutation == "content":
                    path.write_bytes(b"wrong executable, same advertised version")
                elif mutation == "mode":
                    path.chmod(0o644)
                else:
                    path.unlink()
                    path.symlink_to("/usr/bin/false")
                with self.assertRaises(ValueError):
                    check_manifest(self.root)
                if path.is_symlink():
                    path.unlink()
                path.write_bytes(original)
                path.chmod(0o755)

    def test_missing_runtime_and_unsupported_manifest(self):
        path = self.root / "share/sdcc/lib/large/libsdcc.lib"
        path.unlink()
        with self.assertRaises(ValueError):
            check_manifest(self.root)
        manifest(self.root)
        with self.assertRaisesRegex(ValueError, "Missing runtime"):
            check_manifest(self.root)
        path = self.root / "MANIFEST.json"
        value = json.loads(path.read_bytes())
        for version in (True, 2, "1"):
            path.write_text(json.dumps(dict(value, version=version)))
            with self.assertRaisesRegex(ValueError, "Unsupported"):
                check_manifest(self.root)

    def test_trace_requires_successful_packaged_executions_and_opens(self):
        invocations = [f'execve("{self.root}/bin/{n}", [], []) = 0' for n in BINS[:4]]
        files = [self.root / "bin/../share/sdcc/lib/large" / n for n in LIBS]
        files += [self.root / "bin/../share/sdcc/include" / n
                  for n in ("stdint.h", "string.h", "mcs51/8051.h")]
        opens = [f'openat(AT_FDCWD, "{path}", O_RDONLY) = 3' for path in files]
        trace = "\n".join(invocations + opens)
        check_trace(trace, self.root)
        for line in invocations + opens:
            with self.subTest(line=line), self.assertRaises(ValueError):
                check_trace(trace.replace(line, line.replace("= 0", "= -1").replace("= 3", "= -1")),
                            self.root)
        for foreign in ('execve("/usr/bin/sdcpp", [], []) = 0',
                        'openat(AT_FDCWD, "/usr/share/sdcc/include/stdint.h", O_RDONLY) = 3'):
            with self.assertRaisesRegex(ValueError, "System SDCC"):
                check_trace(trace + "\n" + foreign, self.root)


if __name__ == "__main__":
    unittest.main()
