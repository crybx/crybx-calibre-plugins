from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

try:
    from qt.core import (QWidget, QGridLayout, QGroupBox, QVBoxLayout, QCheckBox,
                      QPushButton, QLabel, QPlainTextEdit, QLineEdit)
except ImportError:
    from PyQt5.Qt import (QWidget, QGridLayout, QGroupBox, QVBoxLayout, QCheckBox,
                       QPushButton, QLabel, QPlainTextEdit, QLineEdit)

from calibre.utils.config import JSONConfig
from calibre_plugins.epubaholic.common_dialogs import KeyboardConfigDialog


STORE_SAVED_SETTINGS = 'SavedSettings'
STORE_NAME = 'Options'
KEY_ASK_FOR_CONFIRMATION = 'askForConfirmation'
KEY_CREATE_EPUB_STYLESHEET = 'createEpubStylesheet'
KEY_NEW_CHAPTERS_PATH = 'newChaptersPath'
KEY_ADDED_CHAPTERS_PATH = 'addedChaptersPath'

DEFAULT_NEW_CHAPTERS_PATH = 'R:/epub-manipulator/new-chapters'
DEFAULT_ADDED_CHAPTERS_PATH = 'R:/epub-manipulator/added-chapters'

DEFAULT_CREATE_EPUB_STYLESHEET = '''\
@charset "utf-8";
body, div, h1, p, pre, blockquote, img {
  margin: 0;
  padding: 0;
  border: 0;
  border-width: 0;
}
body {
  hyphens: auto;
  -epub-hyphens: auto;
  -webkit-hyphens: auto;
  font-family: "Crimson", Bookerly, serif;
  font-style: normal;
  font-variant: normal;
  font-weight: normal;
  line-height: 1.6;
  overflow-wrap: break-word;
  text-align: left;
}
img {
  max-width: 100%;
  max-height: 100%;
}
h1, h2, h3, h4, h5, h6 {
  text-align: center;
  page-break-after: avoid;
  page-break-before: avoid;
}
h1 {
  font-size: 1.8em;
  font-weight: normal;
  line-height: 1.4;
  margin-top: 2em;
  margin-bottom: 2em;
}
h2 {
  margin-top: 10%;
  margin-bottom: 8%;
}
h3, h4, h5, h6 {
  margin-top: 7%;
  margin-bottom: 5%;
}
p.no-indent, p.nodent {
  text-indent: 0;
  page-break-after: avoid;
  page-break-before: avoid;
}
i, .i, .italic, .flashback, .memory {
  font-style: italic;
}
b, .b, .bold {
  font-weight: bold;
}
a {
  color: #0057ad;
  text-decoration: underline;
}
p {
  text-align: left;
  text-indent: 1.5em;
  text-decoration: none;
  widows: 2;
  orphans: 2;
  hyphens: none;
  -epub-hyphens: none;
  -webkit-hyphens: none;
}
.chapter-content {
  page-break-after: auto;
  page-break-before: auto;
}
pre {
  font-family: "Roboto Mono", monospace;
  background: #f5f5f5;
  padding: 1em;
  margin: 1em 0;
  text-indent: 0;
  text-align: left;
  white-space: pre-wrap;
  font-size: 0.8em;
  font-weight: bold;
}
.align_center, .c, .center, .separator, .ridicenter {
  text-align: center;
  text-indent: 0;
  padding: 1em 0;
}
.sup {
  font-size: 0.7em;
  vertical-align: super;
  color: #5a54d3;
}
.box, .paper, .ridiborder, .ridipost, .screen, .sys, .system {
  padding: 0.7em 1.6em;
  border-radius: 0.5em;
  border: 1px solid #868a8e;
  margin-top: 5px;
}
.ridipost p {
  text-indent: 0;
}
.paper {
  background-color: #faf9f6;
  border-radius: 0;
}
.ridipost {
  background-color: #e8f4fd;
}'''

DEFAULT_STORE_VALUES = {
                        KEY_ASK_FOR_CONFIRMATION : True,
                        KEY_CREATE_EPUB_STYLESHEET : DEFAULT_CREATE_EPUB_STYLESHEET,
                        KEY_NEW_CHAPTERS_PATH : DEFAULT_NEW_CHAPTERS_PATH,
                        KEY_ADDED_CHAPTERS_PATH : DEFAULT_ADDED_CHAPTERS_PATH,
                       }

# This is where all preferences for this plugin will be stored
plugin_prefs = JSONConfig('plugins/Epubaholic')

# Set defaults
plugin_prefs.defaults[STORE_SAVED_SETTINGS] = []
plugin_prefs.defaults[STORE_NAME] = DEFAULT_STORE_VALUES

class ConfigWidget(QWidget):

    def __init__(self, plugin_action):
        QWidget.__init__(self)
        self.plugin_action = plugin_action
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        c = plugin_prefs[STORE_NAME]
        ask_for_confirmation = c.get(KEY_ASK_FOR_CONFIRMATION, DEFAULT_STORE_VALUES[KEY_ASK_FOR_CONFIRMATION])

        other_group_box = QGroupBox('Other options:', self)
        layout.addWidget(other_group_box)
        other_group_box_layout = QGridLayout()
        other_group_box.setLayout(other_group_box_layout)

        self.ask_for_confirmation_checkbox = QCheckBox('Prompt to save epubs', self)
        self.ask_for_confirmation_checkbox.setToolTip('Uncheck this option if you want changes applied without '
                                                      'a confirmation dialog.')
        self.ask_for_confirmation_checkbox.setChecked(ask_for_confirmation)
        other_group_box_layout.addWidget(self.ask_for_confirmation_checkbox, 0, 0, 1, 3)

        # Chapter import paths
        chapters_group_box = QGroupBox('Chapter import paths:', self)
        layout.addWidget(chapters_group_box)
        chapters_layout = QGridLayout()
        chapters_group_box.setLayout(chapters_layout)

        chapters_layout.addWidget(QLabel('New chapters folder:', self), 0, 0)
        self.new_chapters_edit = QLineEdit(self)
        self.new_chapters_edit.setToolTip('Folder scanned for new chapter HTML files to import into matching epubs.')
        self.new_chapters_edit.setText(c.get(KEY_NEW_CHAPTERS_PATH, DEFAULT_NEW_CHAPTERS_PATH))
        chapters_layout.addWidget(self.new_chapters_edit, 0, 1)

        chapters_layout.addWidget(QLabel('Added chapters folder:', self), 1, 0)
        self.added_chapters_edit = QLineEdit(self)
        self.added_chapters_edit.setToolTip('Folder where imported chapter files are moved (into a subfolder named '
                                            'after the book title) after a successful import.')
        self.added_chapters_edit.setText(c.get(KEY_ADDED_CHAPTERS_PATH, DEFAULT_ADDED_CHAPTERS_PATH))
        chapters_layout.addWidget(self.added_chapters_edit, 1, 1)

        # Stylesheet editor for "Create epub from folder of HTML files"
        stylesheet_group_box = QGroupBox('Create epub stylesheet:', self)
        layout.addWidget(stylesheet_group_box)
        stylesheet_layout = QVBoxLayout()
        stylesheet_group_box.setLayout(stylesheet_layout)

        stylesheet_layout.addWidget(QLabel('CSS stylesheet inserted into EPUBs created from HTML folders:', self))
        self.stylesheet_edit = QPlainTextEdit(self)
        self.stylesheet_edit.setPlainText(c.get(KEY_CREATE_EPUB_STYLESHEET, DEFAULT_CREATE_EPUB_STYLESHEET))
        self.stylesheet_edit.setMinimumHeight(150)
        stylesheet_layout.addWidget(self.stylesheet_edit)

        restore_stylesheet_button = QPushButton('Restore default stylesheet', self)
        restore_stylesheet_button.setToolTip('Reset the stylesheet to the built-in default')
        restore_stylesheet_button.clicked.connect(self._restore_default_stylesheet)
        stylesheet_layout.addWidget(restore_stylesheet_button)

        keyboard_shortcuts_button = QPushButton('Keyboard shortcuts...', self)
        keyboard_shortcuts_button.setToolTip('Edit the keyboard shortcuts associated with this plugin')
        keyboard_shortcuts_button.clicked.connect(self.edit_shortcuts)
        layout.addWidget(keyboard_shortcuts_button)


    def save_settings(self):
        new_prefs = {}
        new_prefs[KEY_ASK_FOR_CONFIRMATION] = self.ask_for_confirmation_checkbox.isChecked()
        new_prefs[KEY_CREATE_EPUB_STYLESHEET] = self.stylesheet_edit.toPlainText()
        new_prefs[KEY_NEW_CHAPTERS_PATH] = self.new_chapters_edit.text().strip()
        new_prefs[KEY_ADDED_CHAPTERS_PATH] = self.added_chapters_edit.text().strip()
        plugin_prefs[STORE_NAME] = new_prefs

    def _restore_default_stylesheet(self):
        self.stylesheet_edit.setPlainText(DEFAULT_CREATE_EPUB_STYLESHEET)

    def edit_shortcuts(self):
        d = KeyboardConfigDialog(self.plugin_action.gui, self.plugin_action.action_spec[0])
        if d.exec_() == d.Accepted:
            self.plugin_action.gui.keyboard.finalize()
