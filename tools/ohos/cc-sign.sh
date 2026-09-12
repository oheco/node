#!/bin/sh
# Sign native configure probes, V8 build tools, Node, and addon libraries.
set -eu
node_cc=${NODE_OHOS_REAL_CC:-clang}
node_link=yes
node_output=a.out
node_output_next=no
for node_arg do
  if [ "$node_output_next" = yes ]; then
    node_output=$node_arg
    node_output_next=no
    continue
  fi
  case "$node_arg" in
    -c|-E|-S|-M|-MM|-fsyntax-only|--version|--help|-dump*|-print*|--print*|-###) node_link=no ;;
    -o) node_output_next=yes ;;
    -o?*) node_output=${node_arg#-o} ;;
  esac
done
if [ "$node_link" = no ]; then
  exec "$node_cc" -fno-emulated-tls "$@"
fi
if [ "$node_link" = yes ] && [ -f "$node_output" ]; then
  rm -f "$node_output"
fi
if [ "$node_link" = yes ] && [ "${NODE_OHOS_STATIC_CXX:-0}" = 1 ]; then
  set -- "$@" -static-libstdc++
fi
"$node_cc" -fno-emulated-tls "$@"
if [ "$node_link" = yes ] && [ -f "$node_output" ]; then
  node_signer=$(command -v binary-sign-tool) || {
    echo 'binary-sign-tool not found; check the LLVM tool directory in PATH.' >&2
    exit 1
  }
  : "${TMPDIR:?Set TMPDIR to a private writable directory}"
  node_sign_dir=$(mktemp -d "$TMPDIR/node-sign.XXXXXXXX")
  trap 'rm -rf "$node_sign_dir"' 0
  if ! "$node_signer" sign -inFile "$node_output" -outFile "$node_sign_dir/signed" -selfSign 1 >"$node_sign_dir/log" 2>&1; then
    cat "$node_sign_dir/log" >&2
    exit 1
  fi
  chmod +x "$node_sign_dir/signed"
  mv -f "$node_sign_dir/signed" "$node_output"
fi
