# Epubaholic Calibre Plugin

## Overview

This plugin offers a way to perform certain modifications to selected epub files without performing a calibre conversion.

Performing an epub->epub conversion will enforce a number of changes to your epub, some of which can be undesirable for some users. Examples are the rewriting of CSS, margin modifications, file splitting in undesired places, changes to directory structure etc.

Instead, this plugin allows a user specific subset of changes to be performed in isolation without otherwise touching the original epub's file structure, CSS files etc. Frequently these changes have been performed manually by users either using the Tweak epub feature (time-consuming), by editing in Sigil (which introduces changes/side effects of its own), by doing epub->epub conversions, or by saving to disk and reimporting into calibre.


## To Build and Install from Source Code

- open command line and navigate to `epubaholic/.build` directory
- run `build.cmd`
- a zip file will be created or updated
- within Calibre, select Preferences > Plugins > Load plugin from file > select the zip file