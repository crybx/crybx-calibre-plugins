from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'

try:
    from qt.core import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog
except ImportError:
    from PyQt5.Qt import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog

from calibre.utils.config import JSONConfig

STORE_NAME = 'Options'

KEY_COLUMN_NAME = 'columnName'
KEY_FOLDER_DEFAULT_DIR = 'folderDefaultDir'
KEY_FOLDER_DEFAULT_TEXT = 'folderDefaultText'

DEFAULT_STORE_VALUES = {
    KEY_COLUMN_NAME: '#links',
    KEY_FOLDER_DEFAULT_DIR: '',
    KEY_FOLDER_DEFAULT_TEXT: '',
}

plugin_prefs = JSONConfig('plugins/LinkManager')
plugin_prefs.defaults[STORE_NAME] = DEFAULT_STORE_VALUES


class ConfigWidget(QWidget):

    def __init__(self, plugin_action):
        QWidget.__init__(self)
        self.plugin_action = plugin_action
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        c = plugin_prefs[STORE_NAME]

        row = QHBoxLayout()
        row.addWidget(QLabel('Custom column for links:', self))
        self.column_edit = QLineEdit(c.get(KEY_COLUMN_NAME, DEFAULT_STORE_VALUES[KEY_COLUMN_NAME]), self)
        self.column_edit.setMaximumWidth(120)
        self.column_edit.setToolTip(
            'The lookup name of the custom column to store links in.\n'
            'Must be a "Column built from other columns" or "Comments"\n'
            'type column with markdown interpretation.\n'
            'Example: #links')
        row.addWidget(self.column_edit)
        row.addStretch()
        layout.addLayout(row)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel('Default folder for folder links:', self))
        self.folder_dir_edit = QLineEdit(c.get(KEY_FOLDER_DEFAULT_DIR, DEFAULT_STORE_VALUES[KEY_FOLDER_DEFAULT_DIR]), self)
        self.folder_dir_edit.setPlaceholderText('(opens last used directory)')
        self.folder_dir_edit.setToolTip('Starting directory when picking a folder link.\nLeave blank to use the system default.')
        row2.addWidget(self.folder_dir_edit, stretch=1)
        self.browse_btn = QPushButton('Browse\u2026', self)
        self.browse_btn.clicked.connect(self.pick_default_folder)
        row2.addWidget(self.browse_btn)
        layout.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel('Default text for folder links:', self))
        self.folder_text_edit = QLineEdit(c.get(KEY_FOLDER_DEFAULT_TEXT, DEFAULT_STORE_VALUES[KEY_FOLDER_DEFAULT_TEXT]), self)
        self.folder_text_edit.setPlaceholderText('(use folder name)')
        self.folder_text_edit.setToolTip('Display text for folder links.\nLeave blank to use the folder name.')
        self.folder_text_edit.setMaximumWidth(200)
        row3.addWidget(self.folder_text_edit)
        row3.addStretch()
        layout.addLayout(row3)

        layout.addStretch()

    def pick_default_folder(self):
        start = self.folder_dir_edit.text().strip() or ''
        folder = QFileDialog.getExistingDirectory(self, 'Select Default Folder', start)
        if folder:
            self.folder_dir_edit.setText(folder)

    def save_settings(self):
        new_prefs = {
            KEY_COLUMN_NAME: self.column_edit.text().strip(),
            KEY_FOLDER_DEFAULT_DIR: self.folder_dir_edit.text().strip(),
            KEY_FOLDER_DEFAULT_TEXT: self.folder_text_edit.text().strip(),
        }
        plugin_prefs[STORE_NAME] = new_prefs
