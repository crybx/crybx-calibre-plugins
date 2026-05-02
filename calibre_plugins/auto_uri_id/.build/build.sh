#!/bin/bash
set -e

PLUGIN_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COMMON_DIR="$(cd "$(dirname "$0")/../../common" && pwd)"

cd "$PLUGIN_DIR"

# Build the zip (output goes to ../installs via build.py)
python3 "$COMMON_DIR/build.py"

PLUGIN_ZIP=$(ls -t ../installs/*.zip 2>/dev/null | head -1)

if [ -z "$PLUGIN_ZIP" ]; then
    echo "ERROR: No plugin zip file found"
    exit 1
fi

echo "Build completed successfully: $PLUGIN_ZIP"
