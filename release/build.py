#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Build exact Git source into a minimal mcs51/model-large relocatable package."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile

from self_test import BINS, LIBS, check_manifest, environment, require, sha, test

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="ascii")


def source_tree(revision, destination):
    destination.mkdir(parents=True)
    raw = subprocess.check_output(["git", "-C", str(ROOT), "archive", "--format=tar", revision])
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        entries = archive.getmembers()
        require(all((entry.isfile() or entry.isdir()) and not Path(entry.name).is_absolute()
                    and ".." not in Path(entry.name).parts for entry in entries),
                "Source archive contains non-regular or escaping entries")
        archive.extractall(destination, filter="data")


def execute(command, source, env, log):
    subprocess.run(command, cwd=source, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)


def manifest(package):
    result = {"version": 1, "files": {}}
    for path in sorted(package.rglob("*")):
        require(not path.is_symlink(), "Unexpected package symlink")
        if path.is_file() and path.name != "MANIFEST.json":
            path.chmod(0o755 if path.parent == package / "bin" else 0o644)
            result["files"][str(path.relative_to(package))] = {
                "sha256": sha(path), "mode": path.stat().st_mode & 0o777}
    write_json(package / "MANIFEST.json", result)
    return result


def compile_toolchain(output, revision, config, epoch):
    source, package = output / "source", output / "toolchain"
    source_tree(revision, source)
    env = dict(os.environ, LC_ALL="C", TZ="UTC", SOURCE_DATE_EPOCH=str(epoch),
               CFLAGS="-O2 -ffile-prefix-map=" + str(source) + "=/usr/src/sdcc",
               CXXFLAGS="-O2 -ffile-prefix-map=" + str(source) + "=/usr/src/sdcc")
    for key in ("SDCC_HOME", "SDCC_INCLUDE", "SDCC_LIB", "SDCC_ASM", "CPATH", "C_INCLUDE_PATH",
                "LIBRARY_PATH", "GCC_EXEC_PREFIX", "COMPILER_PATH", "MAKEFLAGS", "MFLAGS"):
        env.pop(key, None)
    with (output / "build.log").open("w") as log:
        execute(["./configure", *config["configure"]], source, env, log)
        execute(["make", "-s", "-j2", "sdcc-cc", "sdcc-as", "sdcc-ld"], source, env, log)
        execute(["make", "-s", "-j2", "-C", "device/lib", "models", "MODELS=large"], source, env, log)
    require((source / "ports.build").read_text().split() == ["mcs51"], "Unexpected compiled backend")
    (package / "bin").mkdir(parents=True)
    for name in BINS:
        shutil.copyfile(source / "bin" / name, package / "bin" / name)
        subprocess.run(["strip", str(package / "bin" / name)], check=True)
    headers = package / "share/sdcc/include"
    headers.mkdir(parents=True)
    for path in sorted((source / "device/include").glob("*.h")):
        shutil.copyfile(path, headers / path.name)
    shutil.copytree(source / "device/include/mcs51", headers / "mcs51",
                    ignore=shutil.ignore_patterns("Makefile*", "README"))
    libraries = package / "share/sdcc/lib/large"
    libraries.mkdir(parents=True)
    for name in LIBS:
        shutil.copyfile(source / "device/lib/build/large" / name, libraries / name)
    for name, origin in (
            ("COPYING", "COPYING"), ("COPYING3", "sdas/COPYING3"),
            ("SDCC-SUITE-NOTICES.txt", "doc/README.txt"),
            ("SDAS-COPYING3", "sdas/COPYING3"),
            ("BINUTILS-COPYING3", "support/sdbinutils/COPYING3")):
        shutil.copyfile(source / origin, package / name)
    shutil.copyfile("/usr/share/doc/libboost-dev/copyright", package / "BOOST-COPYRIGHT")
    manifest(package)
    return source, package


def package_archive(package, output, name, epoch):
    archive_path = output / (name + ".tar.xz")
    with tarfile.open(archive_path, "w:xz", format=tarfile.PAX_FORMAT, preset=6) as archive:
        for path in (package, *sorted(package.rglob("*"))):
            entry = archive.gettarinfo(path, arcname=str(Path(name) / path.relative_to(package)))
            entry.uid = entry.gid = 0
            entry.uname = entry.gname = ""
            entry.mtime = epoch
            entry.pax_headers = {}
            entry.mode = 0o755 if path.is_dir() else path.stat().st_mode & 0o777
            if path.is_file():
                with path.open("rb") as stream:
                    archive.addfile(entry, stream)
            else:
                archive.addfile(entry)
    return archive_path


def build(output, config, reproduce):
    require(platform.system() == "Linux" and platform.machine() == "x86_64", "Only Linux x86_64 is released")
    require(not output.exists(), "Use a new output directory; existing builds are preserved")
    require(not git("status", "--porcelain"), "Commit source/build inputs before a provenance-bound build")
    revision = git("rev-parse", "HEAD")
    epoch = int(git("show", "-s", "--format=%ct", "HEAD"))
    for name in ("gcc", "g++", "make", "bison", "flex", "m4", "strace", "strip"):
        require(shutil.which(name), "Missing declared build dependency: " + name)
    output.mkdir(parents=True)
    _, control = compile_toolchain(output / "control", config["base_source_commit"], config, epoch)
    base_env = environment(control, output)
    help_text = subprocess.check_output([str(control / "bin/sdcc"), "--help"], env=base_env, text=True)
    require("--xdata-ownership" not in help_text, "Control compiler is not pristine")
    name = "sdcc-" + config["release"].removeprefix("v") + "-" + config["platform"]
    generated = []
    for index in range(2 if reproduce else 1):
        work = output / ("build-" + str(index + 1))
        source, package = compile_toolchain(work, revision, config, epoch)
        env = environment(package, output)
        with (work / "compiler-regressions.txt").open("w") as log:
            execute(["python3", "-B", str(source / "support/regression/test-xdata-ownership.py"),
                     "--sdcc", str(package / "bin/sdcc"), "--control", str(control / "bin/sdcc")],
                    work, env, log)
        tools = {name: subprocess.check_output([name, "--version"], text=True).splitlines()[0]
                 for name in ("gcc", "g++", "make", "bison", "flex", "m4", "strip")}
        info = dict(config, source_commit=revision, source_date_epoch=epoch,
                    build_tools=tools, host_libc=platform.libc_ver(),
                    host_compile_flags="-O2 -ffile-prefix-map=<source>=/usr/src/sdcc",
                    compiler_regression="PASS", compiler_regression_sha256=sha(work / "compiler-regressions.txt"),
                    archive_sha256="See the external BUILDINFO.txt; an archive cannot contain its own digest.")
        write_json(package / "BUILDINFO.txt", info)
        manifest(package)
        archive = package_archive(package, work, name, epoch)
        extracted = work / "extracted"
        extracted.mkdir()
        with tarfile.open(archive) as stream:
            stream.extractall(extracted, filter="data")
        result = test(extracted / name)
        write_json(work / "package-self-test.json", result)
        generated.append((archive, check_manifest(extracted / name), info, result))
    if reproduce:
        require(generated[0][1] == generated[1][1], "Independent package contents are not reproducible")
        require(sha(generated[0][0]) == sha(generated[1][0]), "Independent archives are not byte-identical")
    dist = output / "dist"
    dist.mkdir()
    archive, files, info, result = generated[0]
    target = dist / archive.name
    shutil.copyfile(archive, target)
    info.update(archive_sha256=sha(target), archive=target.name,
                executable_sha256=files["files"]["bin/sdcc"]["sha256"], packaged_self_test="PASS",
                clean_builds=len(generated), bit_reproducible=reproduce)
    write_json(dist / "BUILDINFO.txt", info)
    write_json(dist / "package-self-test.json", result)
    source_archive = dist / ("sdcc-" + config["release"].removeprefix("v") + "-source.tar.xz")
    raw = subprocess.check_output(["git", "-C", str(ROOT), "archive", "--format=tar",
                                   "--prefix=sdcc-source/", revision])
    import lzma
    source_archive.write_bytes(lzma.compress(raw, preset=6))
    (dist / "SHA256SUMS").write_text(
        "".join(f"{sha(path)}  {path.name}\n" for path in sorted(dist.iterdir()) if path.is_file()),
        encoding="ascii")
    print(json.dumps(info, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reproduce", action="store_true")
    args = parser.parse_args()
    config = json.loads((ROOT / "release/version.json").read_bytes())
    build(args.output.resolve(), config, args.reproduce)


if __name__ == "__main__":
    main()
