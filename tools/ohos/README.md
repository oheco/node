# Native Node.js for HarmonyOS PC ARM64

This adaptation starts at upstream Node.js `v24.21.0` (Krypton LTS), commit
`955266bfdd854cd280dffd47548673914484e4c0`, in the upstream fork
<https://github.com/oheco/node>, branch `ohos/24.21.0`.

The upstream `openharmony` platform is retained. Native binaries must report
`process.platform === 'openharmony'` and `process.arch === 'arm64'`; arbitrary
Linux ARM64 prebuilt addons are not treated as compatible.

## Native build

Run in the native ARM64 HarmonyOS terminal, with Python 3.14, the OHOS SDK's
LLVM tools, Ninja, and `binary-sign-tool` in PATH:

```sh
sh tools/ohos/build.sh
```

The default compiler is Clang. The compiler wrappers disable emulated TLS,
link the C++ runtime statically, and sign linked outputs before configure probes
and V8 build tools execute.
Previously signed output inodes are removed before linking. Signing always uses
the `binary-sign-tool` found in PATH.

The script synchronizes source inputs into `$NODE_OHOS_BUILD_ROOT/source` and
builds in its fresh `out/Release` directory, reducing shared-filesystem header
lookup overhead. For incremental development,
`sh tools/ohos/build.sh --compile-only` synchronizes edits and rebuilds configured
targets. Use a fresh `NODE_OHOS_BUILD_ROOT` when changing toolchains or verifying
a complete build. `JOBS` defaults to 2 to limit native compiler memory use.
Nothing is installed into `/usr` or added to shell startup files.

Temporary build files default to the current terminal application's private
directory `/data/storage/el2/base/haps/entry/files/node-24.21.0-build/tmp`.
Override `NODE_OHOS_BUILD_ROOT` or `NODE_OHOS_TMPDIR` for other terminal applications.
The shared development directory is suitable for sources and release archives;
operations requiring Unix sockets or strict POSIX permissions need private storage.

The source tree includes the upstream pinned V8, libuv, OpenSSL, ICU, npm and
other dependencies. The build uses the bundled full ICU data. These dependencies
are not downloaded from unpinned locations during the native build.
The SDK, Python and Ninja are separately installed build prerequisites.

The OHOS SDK used here ships libc++ 15. Its available C++20 ranges algorithms
are enabled with `_LIBCPP_ENABLE_EXPERIMENTAL`; the few missing view adaptors
have OHOS-specific equivalents. This does not require `libc++experimental`.
The SDK also lacks `make_unique_for_overwrite`, for which the adaptation uses
equivalent default-initialized arrays. zlib keeps ARM CRC/crypto acceleration
using the function target attribute spelling accepted by native Clang 15.
V8 dependent types use explicit `typename`, and its WebAssembly type index uses
brace initialization, for C++20 syntax that Clang 15 does not yet implement.
These spelling changes preserve the upstream types and behavior.
For the same compiler, heap visitor predicates are checked with `static_assert`
when the selected method is instantiated, avoiding premature constraint
evaluation while the derived visitor is incomplete. The garbage collection
algorithms and their compile-time predicates remain enabled.
In the JSON stringifier only, statement-level forced-inline annotations are
omitted on native Clang 15 because they crash its parser on dependent template
calls. The fast JSON implementation and normal optimization remain enabled.

## Validation in progress

`smoke.mjs` exercises platform identity, full ICU, module loading, filesystem
operations, subprocesses and signals, worker threads, TCP, HTTP/fetch, crypto,
compression, VM code caches, WebAssembly, optimizing JIT and SQLite. Run it with
`TMPDIR` pointing to private writable storage:

```sh
export NODE_OHOS_BUILD_ROOT=${NODE_OHOS_BUILD_ROOT:-/data/storage/el2/base/haps/entry/files/node-24.21.0-build}
export TMPDIR="$NODE_OHOS_BUILD_ROOT/tmp"
"$NODE_OHOS_BUILD_ROOT/source/out/Release/node" tools/ohos/smoke.mjs
```

Release packaging, npm/addon integration and native validation results will be
documented after the corresponding build and installed-package checks complete.
The target is the current HarmonyOS PC native terminal; other architectures,
system versions and ordinary phone application sandboxes require separate tests.

## References

- Upstream Node.js: <https://github.com/nodejs/node>, including its existing
  `--dest-os=openharmony` configuration and dependency support.
- <https://github.com/hqzing/ohos-node>: community cross-build recipe, particularly
  the OpenHarmony target and native TLS model.
- <https://github.com/nilpwoer/build-ohos-node>: earlier community build recipe.
- <https://github.com/openharmony/third_party_node>: OpenHarmony's N-API header
  integration; this repository itself does not contain a complete Node runtime.

Older community JIT workarounds target different devices and security contexts.
They are not applied without reproducing the corresponding issue on this host.
All upstream licenses and notices are retained in the source tree and must be
included with the corresponding release artifacts.
