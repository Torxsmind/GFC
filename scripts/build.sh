#!/usr/bin/env bash
set -euo pipefail
export PVSNESLIB_HOME="$(cygpath -u "$GFC_SDK")"
cd "$(cygpath -u "$GFC_ROOT")"
if [ "${GFC_CLEAN:-0}" = 1 ]; then make clean; fi
make
