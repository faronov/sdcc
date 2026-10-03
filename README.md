# SDCC mcs51 XDATA ownership fork

This fork adds **compiler-owned XDATA metadata**, not XDATA overlay, to
SDCC 4.2.0 #13081. The optional `--xdata-ownership` flag writes a schema-1
`<output>.xdata.json` sidecar. It does not change normal allocation,
instructions, calling conventions or the ordinary assembler/linker outputs.
An external consumer must independently prove any physical storage reuse.

The release line is `v4.2.0-xdata-ownership.N`; the first published release is
`v4.2.0-xdata-ownership.1`. This is not stock SDCC 4.2.0. The normal compiler
version string remains unchanged; release identity is its source commit,
archive/executable hashes, BUILDINFO and a real compilation capability probe.
The [tag-source release](https://github.com/faronov/sdcc/releases/tag/v4.2.0-xdata-ownership.1)
passed two clean byte-identical package builds and extracted-package checks.

## Source and patch history

This is a GitHub fork of `swegener/sdcc`, a mirror of the upstream
[SDCC SourceForge repository](https://sourceforge.net/p/sdcc/code/).
The release branch starts at SVN r13081, mirror commit
`69e89aa1bab8b96494c6d4d351d0e2d601ec5bb8`.
Commit `c324be6c05a410d87b03f64eb9e7ee5815226fc7` then reproduces **every
one of the 5628 files and modes** in the verified public Debian DFSG archive:

- File: `sdcc_4.2.0+dfsg.orig.tar.xz`
- URL: <https://deb.debian.org/debian/pool/main/s/sdcc/sdcc_4.2.0+dfsg.orig.tar.xz>
- SHA256: `ebe7bfb0894380cd92798b57fb9de96e6c0b913a02b6854d0a01cd70328c1578`

That explicit normalization excludes 1533 upstream-only paths and reproduces
22 archive content/mode differences, including SVN keyword expansion.
It is not an unexplained compiler optimization.

The original four patch contents were independently hash-checked before
application and retain separate logical commits:

| Original study commit | This fork | Purpose |
| --- | --- | --- |
| `7bdae98` | `5d05f54cc` | Standalone ownership and artifact-invariance tests |
| `4282c3d` | `169edb18e` | Corrected fixtures, inline-return and storage-mode coverage |
| `e6f1148` | `43229f834` | Representation-only compiler implementation |
| `02bf3da` | `7292c7128` | Schema and lifetime documentation |

The patch is independent of any board, firmware repository or allocator.
See `doc/xdata-ownership.txt` for the schema and its safety boundaries.

## Build and test

Primary build environment: Ubuntu 24.04, Linux x86_64, with the packages
listed in `release/build-dependencies.txt`. No installed SDCC is required.
GNU libc and libstdc++ are host runtime dependencies, not SDCC components.

```sh
sudo apt-get update
xargs sudo apt-get install --yes --no-install-recommends < release/build-dependencies.txt
python3 -B release/build.py --output build/release --reproduce
```

Use a clean committed checkout and a new output directory. This builds a
pristine source control, then two independent clean patched toolchains;
runs the original standalone regressions; packages only mcs51/model-large
tools, headers and libraries; extracts and relocates each package; and checks
real compiler/preprocessor/assembler/linker/runtime use with `strace`.
It rejects any host SDCC lookup and compares the two complete archives.
Build logs are retained after failure; no system compiler is installed or
replaced. `--reproduce` is mandatory for tagged releases.

The package contains `bin/{sdcc,sdcpp,sdas8051,sdld,sdar}`, common/mcs51
headers and the six model-large libraries. It does not include other target
ports, device-library models, a simulator, PIC non-free files or an overlay
allocator. The configure options are explicit in `release/version.json`.
The archive includes a content/mode manifest and original license notices.
The regression now also retains a real three-byte `COMPILER_TEMP`: a
volatile pointer-valued function result in a read/modify/write expression.
The original optimized-away temporary remains a separate negative control.
Both fixtures compare ordinary output against the pristine compiler.

The external `BUILDINFO.txt` records the archive hash; the copy inside the
archive cannot include its own archive digest. Exact modified source is
available at the release tag and in the accompanying source archive.
Binary packages are release assets, never normal Git commits.

## Version and license policy

Schema 1 describes ownership and storage class, not lifetime safety or
final addresses. Consumers must reject unsupported schema versions and
upgrade by an explicit tag/asset/SHA256 change, never `latest`.
Every published asset is immutable by policy: fixes receive a new `N`.
Changes to schema, ABI or output invariance require a new documented release
line and explicit consumer admission; they are not silently compatible.

SDCC compiler modifications retain their upstream **GPL-2.0-or-later**
terms. The suite also includes GPLv3 components, runtime linking exceptions,
and other upstream notices; see `COPYING`, `sdas/COPYING3`, individual source
headers, and `doc/README.txt`. The source and binary distribution must
preserve these component terms; this fork does not relicense them as BSD.
The separately developed cc2530-zigbee firmware retains its existing license.
The binary package includes the actual Boost headers package's copyright
file (not the `libboost-dev` metapackage notice), the dbuf notice, and the
runtime linking exception verbatim. All per-file notices remain in the
corresponding source archive. Non-free PIC components are excluded.
