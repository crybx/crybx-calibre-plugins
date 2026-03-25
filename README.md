## Project Overview

Epubaholic is a Calibre plugin that allows users to modify EPUB files without performing a full calibre conversion. The plugin preserves the original file structure, CSS, and formatting while applying specific modifications like text transformations, cleanup actions, cover updates, and margin adjustments.

## Build Commands

To build and install the plugin:

```bash
# From anywhere — works in MSYS2/Git Bash (preferred for Claude Code):
R:/repos/epubaholic/repo/calibre_plugins/epubaholic/.build/build.sh

# Or from the build directory using Windows cmd:
cd calibre_plugins/epubaholic/.build
build.cmd
```

The build script copies common files, creates the plugin zip, cleans up, and installs into Calibre via `calibre-customize`.

For development testing:
```bash
# Debug mode
debug.cmd

# Generate translation files
generate-pot.cmd
```

## Architecture

### Plugin Structure
- **Main entry point**: `__init__.py` - Defines the `ActionModifyEpub` wrapper class
- **Action handler**: `action.py` - Contains `ModifyEpubAction` with the main GUI logic
- **Configuration**: `config.py` - Plugin settings and preferences
- **Core processing**: `modify.py` - Main book modification logic using `BookModifier` class
- **Job management**: `jobs.py` - Handles background processing of multiple books

### Key Components
- **Container handling**: `container.py` - Extended container class for EPUB manipulation
- **Specific modifiers**:
  - `covers.py` - Cover image updates
  - `css.py` - CSS modifications 
  - `jacket.py` - Book jacket/metadata handling
  - `margins.py` - Margin adjustments
- **UI dialogs**: `dialogs.py` - Configuration and progress dialogs

### Common Files System
The `calibre_plugins/common/` directory contains shared utilities that get copied into each plugin during build:
- `common_compatibility.py` - PyQt5+ compatibility imports
- `common_dialogs.py` - Reusable dialog components
- `common_icons.py` - Icon management
- `common_menus.py` - Menu building helpers
- `common_widgets.py` - Custom Qt widgets

These common files are automatically integrated during the build process via `build.py`.

## Development Notes

- The plugin follows Calibre's InterfaceAction pattern
- All modifications are done in temporary directories before updating library files
- The plugin supports batch processing of multiple EPUB files
- User confirmation is required before final library updates
- Plugin preferences are stored using Calibre's config system