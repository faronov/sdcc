# XDATA ownership release evidence

1. SDCC fork URL: https://github.com/faronov/sdcc
2. Base SDCC version: 4.2.0 #13081, exact Debian DFSG archive.
3. Fork release tag: `v4.2.0-xdata-ownership.1` (publication pending).
4. Source commit: the exact tag checkout, recorded by the external BUILDINFO.
5. Linux release asset: `sdcc-4.2.0-xdata-ownership.1-linux-x86_64.tar.xz`.
6. Release archive SHA256: pending the tag-source release build.
7. sdcc executable SHA256: pending the tag-source release build.
8. XDATA ownership schema: 1.
9. Compiler CI: initial package check failed; corrected CI pending.
10. Packaged-toolchain self-test: PASS locally on the extracted pilot;
    release-package acceptance pending.
11. cc2530-zigbee clean download/build: NOT RUN; requires the published release.
12. Overlay final l_XSEG: not measured with the release; required value is 7123.
13. Overlay full simulator release gate: NOT RUN with the release.
14. Feature-off build unchanged: not yet rechecked for consumer integration.
15. Source reproduction: PARTIAL; clean pilot compilation and regressions pass,
    two-build archive comparison is mandatory in the release workflow.
16. GPL/source distribution: REVIEW REQUIRED until source/binary assets exist.

## Fork provenance and patch history

See [README](README.md) for the exact SVN mirror commit, archive digest,
DFSG normalization and four distinct transferred patch commits. Normal
source commits implement the feature; no firmware repository is required
for compiler CI. No binary is committed into Git.

## Build configuration and CI architecture

`release/version.json` defines the release, schema, source base and complete
configure arguments. Only mcs51 and model-large runtime libraries are
packaged. `release/build-dependencies.txt` declares Ubuntu 24.04 build
dependencies. Compiler, preprocessor, assembler, linker and archiver are
built together from the exported Git source.

Normal PR/push CI has read-only permissions. The tag workflow verifies the
declared tag and exact checkout, builds a pristine control and two clean
patched packages, then compares manifests and entire archive hashes.
Only a separate publishing job receives `contents: write`, with the
GitHub-provided token. It checks source/hash/test bindings before creating
a new release; it cannot overwrite an existing release through this flow.

Reproduce from a full clone checked out at the exact release tag:

```sh
python3 -B -m unittest discover -s release -p 'test_*.py' -v
python3 -B release/build.py --output build/reproduced --reproduce
```

Install the declared dependencies first, as documented in README.
Two builds use separate exported source and output directories. Archive
ordering, owners, permissions and timestamps are normalized; source paths
are mapped by the host compiler. Equality is measured, never assumed.
BUILDINFO records tool/package versions and flags. Different distribution
or host compiler versions are not promised to produce identical binaries.

## Release contents and self-containment

The package contains five executables, generic/mcs51 headers, six large-model
libraries, BUILDINFO, a complete content/mode manifest and license material.
The external BUILDINFO supplies the archive's own digest and the source
commit; an archive cannot contain its own digest. SHA256SUMS also covers the
corresponding modified-source archive and package test report.

The test executes an extracted, relocated package with a scrubbed
environment. Per-process syscall traces require successful executions of
all compiler children and successful opens of packaged headers and runtime
libraries. Failed lookups do not count as evidence. A real 64-bit division
exercises the explicitly linked long-long library.

Normal compiler outputs are compared with and without metadata; the
standalone suite separately compares them with a pristine control and
covers every documented emitted storage class, ISR and reentrancy.

## Negative tests

Package tests reject absent/changed/nonexecutable/symlinked tools, absent
runtime libraries, unsupported manifest versions, unsuccessful subprocess
executions or file opens, and host SDCC accesses. Compiler regressions reject
unwritable sidecar destinations and preserve option-off absence.
Firmware archive/cache/receipt tests belong to the consumer integration;
they are not claimed by these compiler-only tests.

## Firmware consumer, pinning and upgrades

The intended consumer accepts schema 1 only and pins exact release tag,
asset, archive SHA256, source commit and executable identity. Compiler
development overrides must have a distinct receipt identity. An upgrade
requires an explicit consumer change and full firmware admission, never a
floating URL. Consumer implementation and its measured 7123-byte release
gate will be reported in `cc2530-zigbee/docs/XDATA_TOOLCHAIN.md`.

## Licensing and limitations

The compiler modifications are GPL-2.0-or-later. GPLv3 component terms,
Boost notices, dbuf terms and runtime linking exceptions are preserved
separately; neither the toolchain nor its notices are relicensed as BSD.
The exact modified source is to be published at the tag and as a release
asset alongside the binary. This is conventional source distribution,
not a legal opinion or a claim that every component has identical terms.

Only Linux x86_64 on Ubuntu 24.04 is tested. Host GNU libc/libstdc++ remain
OS dependencies. This feature emits ownership metadata, not an allocator,
lifetime proof or physical hardware commissioning fix. No RF, BDB, MAC,
pool layout or Zigbee semantics are changed by this release work.
