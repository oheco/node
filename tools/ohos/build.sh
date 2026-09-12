#!/bin/sh
# Build with the target host's Python, LLVM, Ninja, and binary signer.
set -eu
node_checkout=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd -P)
unset NODE_OPTIONS NODE_PATH LD_PRELOAD LD_LIBRARY_PATH
case "$(uname -s):$(uname -m)" in
  HarmonyOS:aarch64|OpenHarmony:aarch64|OHOS:aarch64) ;;
  *) echo 'Run this script in the native ARM64 HarmonyOS terminal.' >&2; exit 1 ;;
esac
for node_tool in python3 clang clang++ llvm-ar ninja binary-sign-tool; do
  command -v "$node_tool" >/dev/null || {
    echo "Missing $node_tool; check the Python and LLVM tool directories in PATH." >&2
    exit 1
  }
done
# Resolve the SDK compiler once; avoid a package-manager launcher for every TU.
node_llvm=$(CDPATH= cd -- "$(clang --print-resource-dir)/../../.." && pwd -P)
export NODE_OHOS_REAL_CC=${NODE_OHOS_REAL_CC:-$node_llvm/bin/clang}
export NODE_OHOS_REAL_CXX=${NODE_OHOS_REAL_CXX:-$node_llvm/bin/clang++}
node_private=${NODE_OHOS_BUILD_ROOT:-/data/storage/el2/base/haps/entry/files/node-24.21.0-build}
export TMPDIR=${NODE_OHOS_TMPDIR:-$node_private/tmp}
mkdir -p "$TMPDIR" "$node_checkout/out/ohos-logs"
node_source="$node_private/source"
python3 "$node_checkout/tools/ohos/stage-source.py" "$node_checkout" "$node_source"
# Linux-side chmod is not reflected as an executable bit by the shared mount.
# Invoke the wrappers through the native shell, also preserving spaces in paths.
export CC="/bin/sh \"$node_source/tools/ohos/cc-sign.sh\""
export CXX="/bin/sh \"$node_source/tools/ohos/cxx-sign.sh\""
# GYP interprets CC_host/CXX_host as a request for separate cross toolsets.
unset CC_host CXX_host AR_host CC_target CXX_target AR_target GYP_CROSSCOMPILE
export AR=llvm-ar
export RANLIB=llvm-ranlib
cd "$node_source"
if [ "${1:-}" != --compile-only ]; then
  python3 configure --dest-os=openharmony --dest-cpu=arm64 --ninja \
    --prefix=/usr/local --openssl-system-ca-path=/etc/ssl/certs/cacert.pem
fi
ninja -C out/Release -j "${JOBS:-2}" node
