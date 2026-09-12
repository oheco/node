#!/bin/sh
set -eu
export NODE_OHOS_REAL_CC=${NODE_OHOS_REAL_CXX:-clang++}
export NODE_OHOS_STATIC_CXX=1
exec /bin/sh "$(dirname "$0")/cc-sign.sh" "$@"
