# Native Node.js for HarmonyOS PC ARM64

This community adaptation uses upstream Node.js `v24.21.0` (Krypton LTS), commit
`955266bfdd854cd280dffd47548673914484e4c0`, in the upstream fork
<https://github.com/oheco/node>, branch `ohos/24.21.0`.
The first package version is `24.21.0-ohos.1`; Node reports `v24.21.0`.

The upstream platform identity is retained:
`process.platform === 'openharmony'` and `process.arch === 'arm64'`.

## Install and use

```sh
oo update
oo install nodejs
node --version
npm --version
node -p "process.platform + '/' + process.arch"
```

The package includes signed Node, npm 11.19.0, npx, Corepack 0.36.0, development
headers and licenses. Its npm/npx/Corepack launchers locate their own Node and
resources, including when the installation path contains spaces. Versioned
commands such as `node@24.21.0-ohos.1` are available through oo.
The client does not install cross-package dependencies automatically.

Node statically includes its C++ runtime and bundled libraries; its only ELF
`NEEDED` dependency is the host's `libc.so`. Running JavaScript or installing
pure JavaScript packages does not require Python or the SDK.

For operations requiring Unix sockets or strict POSIX permissions, use the
terminal application's private writable storage:

```sh
export TMPDIR=/data/storage/el2/base/haps/entry/files/node-tmp
mkdir -p "$TMPDIR"
```

The shared user directory is suitable for sources and relocatable packages.
Unix socket names must also fit the system's socket pathname limit. The above
private path is interpreted in the current terminal application's sandbox.

### npm and native addons

Normal `npm install` uses the project's `node_modules`; global commands use
npm's selected prefix. The included node-gyp automatically finds the matching
headers beside the running Node. Explicit `--nodedir` remains supported.

Native addons require Python 3, OHOS SDK Clang/Clang++, GNU Make and
`binary-sign-tool`. Set `MAKE` to an absolute GNU Make path if it is not on PATH.
The npm launchers select the included compiler helpers unless `CC`/`CXX` were
explicitly set; these helpers use native TLS, static C++ linkage and sign the
resulting addon. Use a private `TMPDIR` for builds.

Only the bundled npm/node-gyp has these adaptations. Updating npm independently
may replace them. Third-party addon build systems can require their own changes.
Generic Linux ARM64 prebuilt addons are not ABI-compatible with this platform;
packages need an OpenHarmony build or compatible source compilation. The signed
C N-API addon validation is described in [VALIDATION.md](VALIDATION.md).

Network access in the validation environment uses a SOCKS5 proxy with remote DNS,
for example `HTTPS_PROXY=socks5h://172.16.105.2:10808` for npm. Configure the proxy
for your environment; certificate checks remain enabled.

## Native build

Run in the native ARM64 HarmonyOS terminal, with Python 3.14, the OHOS SDK's
LLVM tools, Ninja, and `binary-sign-tool` in PATH:

```sh
sh tools/ohos/build.sh
```

The compiler wrappers disable emulated TLS, link the C++ runtime statically, and
sign linked outputs before configure probes and V8 build tools execute.
Previously signed output inodes are removed before linking. Signing always uses
the `binary-sign-tool` found in PATH.

The script synchronizes source inputs into `$NODE_OHOS_BUILD_ROOT/source` and
builds in its `out/Release` directory. The default build root is
`/data/storage/el2/base/haps/entry/files/node-24.21.0-build`.
For incremental work, `sh tools/ohos/build.sh --compile-only` synchronizes edits
and resumes configured targets. Use a fresh `NODE_OHOS_BUILD_ROOT` when changing
toolchains or verifying a complete build. `JOBS` defaults to 2; the tested 32 GiB
host completed the build with 8 jobs. Nothing is installed into `/usr` or added
to shell startup files.

Temporary build files default to `$NODE_OHOS_BUILD_ROOT/tmp`. Override
`NODE_OHOS_BUILD_ROOT` or `NODE_OHOS_TMPDIR` as appropriate for another terminal.
The SDK, Python and Ninja are separately installed build prerequisites.
The source archive includes the pinned V8, libuv, OpenSSL, full ICU data, npm and
other vendored dependencies. The native build does not download dependencies.

### Toolchain compatibility

The tested SDK ships Clang 15.0.4 and libc++ 15. Its header-only C++20 ranges
algorithms are enabled with `_LIBCPP_ENABLE_EXPERIMENTAL`; missing view adaptors
have OHOS-specific equivalents. No `libc++experimental` linkage is required.
Missing `make_unique_for_overwrite` uses equivalent default-initialized arrays.
zlib retains ARM CRC/crypto acceleration with the native compiler's supported
function target attribute spelling.

Dependent types use explicit `typename`, and aggregate records use brace
initialization where Clang 15 lacks C++20 parenthesized aggregate initialization.
V8 heap visitor predicates are enforced with `static_assert` at instantiation
on this compiler, avoiding premature checks on incomplete derived classes.
The garbage collection algorithms and their predicates remain enabled.
Statement-level forced-inline annotations in the JSON stringifier are omitted
only on OHOS Clang below 16 because they crash its parser on dependent template
calls. The fast JSON implementation and normal optimization remain enabled.

Both GYP copies recognize native Python's OHOS platform. The Make generator
quotes include arguments on OpenHarmony so addon builds can use an installation
prefix containing spaces.

## Validation and packaging

The native integration checks cover JIT, WebAssembly, asm.js, GC, threads,
modules, filesystem operations, signals, loopback networking, HTTPS, crypto,
compression, full ICU, Inspector, tracing and SQLite. See [VALIDATION.md](VALIDATION.md)
for the tested environment, results and limits.

```sh
export TMPDIR=/data/storage/el2/base/haps/entry/files/node-24.21.0-build/tmp
node_build=/data/storage/el2/base/haps/entry/files/node-24.21.0-build/source/out/Release/node
"$node_build" tools/ohos/smoke.mjs
python3 tools/ohos/test-repl.py "$node_build"
python3 tools/ohos/test-v8.py "$node_build"
python3 tools/ohos/test-upstream.py "$node_build"
python3 tools/ohos/package.py
```

`test-upstream.py` uses a short private test root to keep Unix socket paths within
the kernel limit, and retains the source working directory for upstream test
reporters. Override its parent with `--temp-parent` or `NODE_OHOS_TEST_TMPDIR`.

`package.py` produces `out/node-v24.21.0-ohos.1-arm64.tar.gz` on the native host.
For test packages use `--output out/package-tests`. It refuses to overwrite an
existing archive. The archive has one top-level directory; oo removes this with
`strip_components: 1`. `source-archive.py --commit TAG` exports the complete
committed source with its Git commit recorded in the tar PAX header.
Release assets are immutable; fixes require another adaptation revision.

Only the tested HarmonyOS PC ARM64 native terminal is covered by this community
prerelease. Other system versions, architectures, phone sandboxes, arbitrary
third-party native packages and long-running workloads require separate tests.

## References

- Upstream Node.js: <https://github.com/nodejs/node>, including its existing
  `--dest-os=openharmony` configuration and dependency support.
- <https://github.com/hqzing/ohos-node>: community cross-build recipe, particularly
  the OpenHarmony target and native TLS model.
- <https://github.com/nilpwoer/build-ohos-node>: earlier community build recipe.
- <https://github.com/openharmony/third_party_node>: N-API header integration,
  rather than a complete Node runtime distribution.

Older community JIT workarounds were not needed on this host. All upstream
licenses and notices are retained; the runtime includes Node's consolidated
third-party license notices and the Release includes corresponding source.
