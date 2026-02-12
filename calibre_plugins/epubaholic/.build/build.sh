#!/bin/bash
set -e

PLUGIN_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COMMON_DIR="$(cd "$(dirname "$0")/../../common" && pwd)"

cd "$PLUGIN_DIR"

# Compile translations if they exist
if [ -d "translations" ]; then
    cd translations
    export PYTHONIOENCODING=UTF-8
    for f in *.po; do
        [ -f "$f" ] || continue
        name="${f%.po}"
        echo "Compiling translation for: $name"
        if [ -n "$CALIBRE_DIRECTORY" ]; then
            "$CALIBRE_DIRECTORY/calibre-debug.exe" -c "from calibre.translations.msgfmt import main; main()" "$name"
        else
            calibre-debug.exe -c "from calibre.translations.msgfmt import main; main()" "$name"
        fi
    done
    cd "$PLUGIN_DIR"
else
    echo "No translations subfolder found"
fi

# Copy common files
echo "Copying common files for zip"
cp "$COMMON_DIR"/common_*.py .

# Build the zip
python "$COMMON_DIR/build.py"

# Clean up common files
echo "Deleting common files after zip"
rm -f common_*.py

# Find the most recently modified zip
PLUGIN_ZIP=$(ls -t *.zip 2>/dev/null | head -1)

if [ -z "$PLUGIN_ZIP" ]; then
    echo "ERROR: No plugin zip file found"
    exit 1
fi

# Install into calibre
echo "Installing plugin \"$PLUGIN_ZIP\" into calibre..."
if [ -n "$CALIBRE_DIRECTORY" ]; then
    "$CALIBRE_DIRECTORY/calibre-customize" -a "$PLUGIN_ZIP"
else
    calibre-customize -a "$PLUGIN_ZIP"
fi

echo "Build completed successfully"
