#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Test an extracted, relocated toolchain; forbid host SDCC/tool/library fallback."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

BINS = ("sdcc", "sdcpp", "sdas8051", "sdld", "sdar")
LIBS = ("mcs51.lib", "libsdcc.lib", "libint.lib", "liblong.lib", "liblonglong.lib", "libfloat.lib")
ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_manifest(package):
    manifest = json.loads((package / "MANIFEST.json").read_bytes())
    require(type(manifest["version"]) is int and manifest["version"] == 1, "Unsupported package manifest")
    actual = {}
    for path in sorted(package.rglob("*")):
        require(not path.is_symlink(), "Symlink in toolchain package")
        if path.is_file() and path.name != "MANIFEST.json":
            actual[str(path.relative_to(package))] = {
                "sha256": sha(path), "mode": path.stat().st_mode & 0o777}
    require(actual == manifest["files"], "Extracted toolchain content/mode mismatch")
    for name in BINS:
        require((package / "bin" / name).is_file() and os.access(package / "bin" / name, os.X_OK),
                "Missing tool: " + name)
    for name in LIBS:
        require((package / "share/sdcc/lib/large" / name).is_file(), "Missing runtime: " + name)
    return manifest


def environment(package, home):
    return {"PATH": str(package / "bin") + ":/usr/bin:/bin",
            "HOME": str(home), "LC_ALL": "C", "TZ": "UTC"}


def run(command, cwd, env):
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, timeout=120)
    require(result.returncode == 0, f"Package command failed: {command!r}\n{result.stdout}\n{result.stderr}")
    return result.stdout + result.stderr


def check_trace(trace, package):
    require(not re.search(r'"/(?:usr|usr/local)/(?:bin/(?:sdcc|sdcpp|sdas8051|sdld|sdar)|share/sdcc)', trace),
            "System SDCC component accessed")
    invoked = set(re.findall(r'execve\("([^"]+)"', trace))
    expected = {str(package / "bin" / name) for name in BINS[:4]}
    require(expected <= invoked, "Packaged compiler/preprocessor/assembler/linker not all exercised")
    require(all(not re.search(r"/(?:sdcc|sdcpp|sdas8051|sdld|sdar)$", path) or
                path.startswith(str(package / "bin") + "/") for path in invoked),
            "Foreign supporting binary invoked")
    for name in LIBS:
        require(str(package / "bin/../share/sdcc/lib/large" / name) in trace or
                str(package / "share/sdcc/lib/large" / name) in trace,
                "Packaged runtime lookup not observed: " + name)
    require("stdint.h" in trace and "string.h" in trace and "8051.h" in trace,
            "Representative packaged headers not exercised")


def test(package):
    package = package.resolve()
    manifest = check_manifest(package)
    with tempfile.TemporaryDirectory(prefix="sdcc-package-probe-") as temporary:
        root = Path(temporary)
        env = environment(package, root)
        compiler = str(package / "bin/sdcc")
        version = run([compiler, "--version"], root, env)
        require("4.2.0 #13081" in version and "mcs51" in version, "Wrong compiler version/backend")
        artifacts, traces = [], []
        for enabled in (False, True):
            work = root / ("on" if enabled else "off")
            work.mkdir()
            shutil.copyfile(ROOT / "release/probe.c", work / "probe.c")
            command = [compiler, "-mmcs51", "--model-large", "--debug",
                       *(["--xdata-ownership"] if enabled else []), "probe.c"]
            run(["strace", "-f", "-qq", "-e", "trace=file,process", "-o", "trace.txt", *command], work, env)
            traces.append((work / "trace.txt").read_text())
            sidecar = work / "probe.xdata.json"
            require(sidecar.exists() == enabled, "Option-off/on sidecar presence differs")
            if enabled:
                data = json.loads(sidecar.read_bytes())
                require(type(data["version"]) is int and data["version"] == 1
                        and data["module"] == "probe", "Unsupported ownership schema/module")
                classes = {row["class"] for row in data["objects"]}
                require({"GLOBAL", "FILE_STATIC", "LOCAL", "FIRST_ARGUMENT_HOME",
                         "PARAM_CALLER_WRITTEN"} <= classes, "Ownership behavior probe lacks required classes")
            artifacts.append({suffix: sha(work / ("probe." + suffix))
                              for suffix in ("asm", "rel", "adb", "lst", "sym", "ihx", "cdb", "mem")})
        require(artifacts[0] == artifacts[1], "Metadata option changed ordinary compiler/linker output")
        check_trace("\n".join(traces), package)
        archive = root / "probe.lib"
        run([str(package / "bin/sdar"), "-rcD", str(archive), str(root / "on/probe.rel")], root, env)
        members = run([str(package / "bin/sdar"), "-t", str(archive)], root, env)
        require("probe.rel" in members, "Packaged archiver did not preserve the object")
    return dict(result="PASS", extracted_package=True, schema=1, option_off_on_identical=True,
                host_sdcc_access=False, binaries={n: manifest["files"]["bin/" + n]["sha256"] for n in BINS})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = test(args.package)
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="ascii")
    print(text, end="")


if __name__ == "__main__":
    main()
