# crybx-calibre-plugins

A collection of [Calibre](https://calibre-ebook.com/) plugins for ebook management, metadata scraping, and EPUB editing.

## Plugins

### Library Plugins (Calibre main window)

| Plugin | Description |
|--------|-------------|
| **Epubaholic** | Build EPUBs from a folder of HTML files, or apply text transformations and cleanup actions to existing EPUBs without a full conversion |
| **NovelUpdates** | Download metadata from [novelupdates.com](https://www.novelupdates.com/) |
| **MangaUpdates** | Download metadata from [mangaupdates.com](https://www.mangaupdates.com/) |
| **MangaDex** | Download metadata from [mangadex.org](https://mangadex.org/) |
| **MetaManipulator** | Bulk metadata manipulation for any book format |
| **LinkManager** | Manage markdown links in a custom column |

### Edit Book Plugins (Calibre book editor)

| Plugin | Description                                                                                              |
|--------|----------------------------------------------------------------------------------------------------------|
| **BulkFileEdits** | Bulk file operations: rename by chapter content, sort by filename, insert headers, delete matching files |

## Building

Each plugin has a `.build/` directory with build scripts:

```bash
cd calibre_plugins/<PluginName>/.build
bash build.sh    # Linux / MSYS2 / Git Bash
build.cmd        # Windows cmd
```

Built zips are placed in `calibre_plugins/installs/`. Install via Calibre's Preferences > Plugins > Load plugin from file.

### Shared code

The `calibre_plugins/common/` directory contains shared utilities (Qt compatibility shims, dialogs, icon management, menu helpers, widgets) originally from [kiwidude68/calibre_plugins](https://github.com/kiwidude68/calibre_plugins). These are copied into each plugin zip at build time.

## License

[GPL v3](LICENSE.md)
