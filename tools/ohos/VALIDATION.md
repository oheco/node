# Node.js 24.21.0-ohos.1 native validation

Validation date: 2026-09-12. This is a community prerelease for the tested
HarmonyOS PC ARM64 native terminal.

## Source and environment

- Upstream: Node.js `v24.21.0`, commit
  `955266bfdd854cd280dffd47548673914484e4c0`.
- Adaptation: <https://github.com/oheco/node>, branch `ohos/24.21.0`,
  release tag `v24.21.0-ohos.1`. The corresponding source archive records the
  exact Git commit in its global PAX `comment` header.
- Host: `HarmonyOS`, `HongMeng Kernel 1.13.0`, `aarch64`, 32 GiB RAM.
- SDK: `ohos-sdk-native/26.0.0.35-Beta`, native Clang 15.0.4 and libc++ 15004.
- Build tools: native Python 3.14.7, Ninja, LLVM archiver/linker and
  `binary-sign-tool` from PATH. Addon validation used GNU Make 4.4.1.
- Build root: `/data/storage/el2/base/haps/entry/files/node-24.21.0-build`.
  The build began in a fresh private source/build tree and resumed incrementally
  as compatibility fixes were made. The complete native build exited with code 0.
- Runtime: `v24.21.0`, platform `openharmony`, architecture `arm64`;
  V8 `13.6.233.17-node.53`, OpenSSL `3.5.8`, ICU `78.3`, libuv `1.52.1`,
  SQLite `3.53.4`, module ABI `137`, N-API `10`.
- Bundled command versions: npm/npx `11.19.0`, Corepack `0.36.0`.

The signed `bin/node` is an AArch64 ELF PIE with interpreter
`/lib/ld-musl-aarch64.so.1`, only `libc.so` in `DT_NEEDED`, and no RPATH/RUNPATH.
It runs with `LD_PRELOAD` and `LD_LIBRARY_PATH` unset.
Its size is 126,753,536 bytes and SHA-256 is:

```text
69b0664f303a1581f8f31574560e560c1566ea175a4fd14a03b69cbd41e5e4c6
```

Copying, archiving, native extraction and relocation preserved the executable's
hash and ability to run. Archive sizes and SHA-256 values are provided separately
in the Release's `SHA256SUMS`.

## Native results

| Check | Result |
| --- | --- |
| `smoke.mjs` | All 20 integration checks passed; the test runner reports 21 including the parent test, with no failures or skips |
| `test-v8.py` | All 5 selected upstream V8 regression files passed |
| `test-upstream.py` | All 57 selected upstream Node regression files passed, with no skips |
| `test-repl.py` | PTY REPL, TTY detection, Chinese output, Ctrl-C recovery and clean exit passed |
| `check-https.mjs` | Registry HTTPS through remote-DNS SOCKS5 returned HTTP 200 with trusted TLS; an empty trust store was rejected |
| Relocated runtime package | All 20 integration checks, REPL and HTTPS checks passed under a shared path containing spaces |
| `test-npm.py` | Registry install, local CLI, npx, isolated global install/remove and offline signed C N-API addon passed |

The integration checks exercise full ICU locale support; builtin enumeration and
Inspector comma-option parsing; trace categories and output; ESM/CommonJS;
JSON fast paths, Unicode and error cases; file writes/fsync/rename/symlinks;
filesystem notifications; shared-buffer decoding; subprocess cwd/pipes/signals;
workers and Atomics; loopback TCP and HTTP/fetch; hashes/randomness/CRC32/gzip/
Brotli; VM cached code; WebAssembly; optimizing JIT; asm.js-to-Wasm compilation;
minor/major GC with live objects; and SQLite transactions/WAL.

JIT validation requested optimization and observed generated optimized code
executing successfully. No old community JIT workaround was applied.
The V8 regression selection covers asm.js validation and Turboshaft string escape
analysis, including reconstruction after deoptimization. Warnings in the negative
asm.js cases are expected by the upstream tests.

Node regression selection covers Buffer/encoding, cryptographic signing and
randomness, KMAC known-answer signing/verification vectors, filesystem/error
paths, children, workers, streams, TCP/Unix sockets, HTTP parsing, Inspector,
module loading, SQLite, CLI options, tracing and zlib.

The filesystem error fixture uses a known readable directory so sandbox denial
of `/` cannot mask the expected `EISDIR`. The runtime still returns the actual
host error; no syscall error was remapped. Tests use a short private temporary
root and the source working directory to satisfy Unix socket path limits and
upstream relative reporter paths.

The npm test uses isolated configs, cache, project and global prefix. It installs
`is-number@7.0.0` through the proxy, exercises a local executable with npx and a
global prefix, removes the global package, and builds a C N-API addon offline.
Both the Node installation and addon project paths contain spaces. No manual
`--nodedir` is supplied. The addon is automatically signed and returns 42 when
loaded. The runtime and helper files are tested again from the final archive
before publication.

## Release and catalog checks

The source export was checked for its recorded commit, vendored inputs, adapted
files and contained symlinks. The runtime archive retains executable permissions,
package-relative launchers, headers, resources and consolidated license notices.

Official-index installation is a post-publication check. Its final result,
catalog commit and Pages deployment are recorded in the Release notes.
`test-catalog.py` uses the official v2 index and an isolated install root containing
spaces. It checks update, installation without activation, versioned commands,
switching, regular commands, the 20 runtime checks, listing and removal.

## Limits

These results cover one HarmonyOS PC native terminal and the recorded SDK/kernel.
They do not establish support for other architectures, phone application
sandboxes, all system releases, every npm package or long-running workloads.

Pure JavaScript use needs no compiler or Python. Native addons require separately
installed Python 3, OHOS SDK Clang, GNU Make and `binary-sign-tool`; third-party
build systems may need additional adaptation. Generic Linux ARM64 prebuilt addons
are not interchangeable with OpenHarmony addons. Independently upgrading npm may
replace the bundled node-gyp patches.

Shared storage does not provide every private-storage permission/socket behavior.
Use a writable application-private `TMPDIR`, and keep Unix socket names short.
All external network checks used the configured proxy and retained certificate
verification. The complete upstream Node and V8 test suites were not run.
