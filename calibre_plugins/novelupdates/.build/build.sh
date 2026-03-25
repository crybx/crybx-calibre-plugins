#!/bin/bash
set -e

PLUGIN_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COMMON_DIR="$(cd "$(dirname "$0")/../../common" && pwd)"

cd "$PLUGIN_DIR"

# Copy common files
echo "Copying common files for zip"
cp "$COMMON_DIR"/common_*.py .

# Build the zip
python3 "$COMMON_DIR/build.py"

# Clean up common files
echo "Deleting common files after zip"
rm -f common_*.py

# Find the most recently modified zip
PLUGIN_ZIP=$(ls -t *.zip 2>/dev/null | head -1)

if [ -z "$PLUGIN_ZIP" ]; then
    echo "ERROR: No plugin zip file found"
    exit 1
fi

echo "Build completed successfully: $PLUGIN_ZIP"
