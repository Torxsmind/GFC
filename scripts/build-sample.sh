#!/usr/bin/env bash
set -euo pipefail
export PVSNESLIB_HOME="$(cygpath -u "$GFC_SDK")"
cd "$(cygpath -u "$GFC_ROOT")/build/hello-world"
make clean
make
