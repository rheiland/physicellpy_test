#!/usr/bin/env bash
set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 v#.#.#" >&2
    exit 1
fi

VERSION="$1"

gh release download --clobber "$VERSION" -R rheiland/physicellpy_test -p physicellpy-0.1.0-cp312-cp312-macosx_14_0_arm64.whl
# gh release download --clobber "$VERSION" -R rheiland/physicellpy_test -p physicellpy-0.1.0-cp313-cp313-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
# gh release download --clobber "$VERSION" -R rheiland/physicellpy_test -p physicellpy-0.1.0-cp314-cp314-macosx_14_0_arm64.whl
