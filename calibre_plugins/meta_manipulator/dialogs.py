from qt.core import (QVBoxLayout, QCheckBox, QGridLayout,
                      QGroupBox, Qt, QDialogButtonBox, QDialog,
                      QIcon, QPixmap, QHBoxLayout, QLabel)

from calibre.gui2 import gprefs, error_dialog


META_OPTIONS = [
    ('save_title_author_to_description', 'Save title and author to description',
     'Prepend "Title by Author" to the book description/comments field'),
    ('save_title_to_originaltitle', 'Save title to #originaltitle',
     'Copy the current title to the #originaltitle custom column'),
    ('move_contents_from_title', 'Move contents from title',
     'Move a trailing parenthesized group from the title into the #contents column'),
]

ALL_OPTIONS = META_OPTIONS


class MetaManipulatorDialog(QDialog):

    PREFS_KEY = 'metamanipulator plugin:options dialog'

    def __init__(self, gui, icon_data=None):
        QDialog.__init__(self, gui)
        self.setWindowTitle('MetaManipulator')
        self.options = {}

        layout = QVBoxLayout(self)
        self.setLayout(layout)

        # Title bar with icon
        title_layout = QHBoxLayout()
        if icon_data:
            pm = QPixmap()
            pm.loadFromData(icon_data)
            icon_label = QLabel()
            icon_label.setPixmap(pm.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            title_layout.addWidget(icon_label)
        title_label = QLabel('<b>MetaManipulator Options</b>')
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        layout.addSpacing(5)

        # Options group
        saved = gprefs.get(self.PREFS_KEY + ':settings', {})
        self.main_layout = QGridLayout()
        layout.addLayout(self.main_layout, 1)

        self._add_groupbox(0, 0, 'Metadata Operations', META_OPTIONS, saved)

        layout.addSpacing(10)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._ok_clicked)
        button_box.rejected.connect(self.reject)
        self.clear_button = button_box.addButton(' Clear all ', QDialogButtonBox.ResetRole)
        self.clear_button.setToolTip('Clear all selections')
        self.clear_button.clicked.connect(self._clear_clicked)
        layout.addWidget(button_box)

    def _add_groupbox(self, row, col, title, option_info, saved):
        groupbox = QGroupBox(title)
        self.main_layout.addWidget(groupbox, row, col, 1, 1)
        groupbox_layout = QVBoxLayout()
        groupbox.setLayout(groupbox_layout)

        for key, text, tooltip in option_info:
            checkbox = QCheckBox(text, self)
            checkbox.setToolTip(tooltip)
            checkbox.setCheckState(Qt.Checked if saved.get(key, False) else Qt.Unchecked)
            setattr(self, key, checkbox)
            groupbox_layout.addWidget(checkbox)
        groupbox_layout.addStretch(-5)

    def _ok_clicked(self):
        self._set_options()
        gprefs.set(self.PREFS_KEY + ':settings', self.options)

        for key in self.options:
            if self.options[key]:
                self.accept()
                return
        return error_dialog(self, 'No options selected',
                            'You must select at least one option to continue',
                            show=True, show_copy_button=False)

    def _set_options(self):
        self.options = {}
        for key, _t, _tt in ALL_OPTIONS:
            self.options[key] = getattr(self, key).checkState() == Qt.Checked

    def _clear_clicked(self):
        for key, _t, _tt in ALL_OPTIONS:
            getattr(self, key).setCheckState(Qt.Unchecked)
