from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'

try:
    from qt.core import (Qt, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                         QGridLayout, QLabel, QCheckBox, QLineEdit, QComboBox,
                         QPushButton)
except ImportError:
    from PyQt5.Qt import (Qt, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
                          QGridLayout, QLabel, QCheckBox, QLineEdit, QComboBox,
                          QPushButton)

from calibre.utils.config import JSONConfig

STORE_NAME = 'Options'

# URL discovery
KEY_SCAN_IDENTIFIERS  = 'scanIdentifiers'   # bool: scan url/uri identifiers
KEY_SCAN_COMMENTS     = 'scanComments'      # bool: scan comments field
KEY_SCAN_CUSTOM_COL   = 'scanCustomCol'     # bool: scan a custom column
KEY_CUSTOM_COL_NAME   = 'customColName'     # str:  name of the custom column to scan

# Field mapping — what to write and where
KEY_UPDATE_GENRES         = 'updateGenres'       # bool: apply by default
KEY_GENRES_COL            = 'genresCol'          # str: column for MU genres
KEY_GENRES_APPEND         = 'genresAppend'       # bool: append or replace
KEY_UPDATE_CATEGORIES     = 'updateCategories'   # bool: apply by default
KEY_CATEGORIES_COL        = 'categoriesCol'      # str: column for MU categories
KEY_CATEGORIES_APPEND     = 'categoriesAppend'   # bool: append or replace
KEY_UPDATE_ASSOC_NAMES    = 'updateAssocNames'   # bool: apply by default
KEY_ASSOC_NAMES_COL       = 'assocNamesCol'      # str: column for associated names
KEY_ASSOC_NAMES_APPEND    = 'assocNamesAppend'   # bool: append or replace
KEY_UPDATE_DESCRIPTION    = 'updateDescription'  # bool
KEY_DESCRIPTION_APPEND    = 'descriptionAppend'  # bool: append to existing comments
KEY_UPDATE_COVER          = 'updateCover'        # bool
KEY_UPDATE_AUTHORS        = 'updateAuthors'      # bool
KEY_AUTHORS_APPEND        = 'authorsAppend'      # bool: append or replace
KEY_UPDATE_TITLE          = 'updateTitle'        # bool
KEY_UPDATE_ORIG_LANG      = 'updateOrigLang'     # bool: write original language (inferred from type)
KEY_ORIG_LANG_COL         = 'origLangCol'        # str: column for original language (empty = Calibre languages field)
KEY_ARTISTS_TO_AUTHORS    = 'artistsToAuthors'   # bool: merge artists into authors field
KEY_UPDATE_ARTISTS        = 'updateArtists'      # bool: apply artists to custom column
KEY_ARTISTS_COL           = 'artistsCol'         # str: column for artists
KEY_ARTISTS_APPEND        = 'artistsAppend'      # bool: append or replace
KEY_USER_AGENT            = 'userAgent'          # str: browser User-Agent to send
KEY_LINK_COL              = 'linkCol'            # str: column to write MU link (markdown)

DEFAULT_STORE_VALUES = {
    KEY_SCAN_IDENTIFIERS:  True,
    KEY_SCAN_COMMENTS:     True,
    KEY_SCAN_CUSTOM_COL:   True,
    KEY_CUSTOM_COL_NAME:   '#links',
    KEY_UPDATE_GENRES:        True,
    KEY_GENRES_COL:           '#extratags',
    KEY_GENRES_APPEND:        True,
    KEY_UPDATE_CATEGORIES:    True,
    KEY_CATEGORIES_COL:       '#extratags',
    KEY_CATEGORIES_APPEND:    True,
    KEY_UPDATE_ASSOC_NAMES:   True,
    KEY_ASSOC_NAMES_COL:      '',
    KEY_ASSOC_NAMES_APPEND:   True,
    KEY_UPDATE_DESCRIPTION:   True,
    KEY_DESCRIPTION_APPEND:   False,
    KEY_UPDATE_COVER:         True,
    KEY_UPDATE_AUTHORS:       True,
    KEY_AUTHORS_APPEND:       False,
    KEY_UPDATE_TITLE:         False,
    KEY_UPDATE_ORIG_LANG:     True,
    KEY_ORIG_LANG_COL:        '',
    KEY_ARTISTS_TO_AUTHORS:   True,
    KEY_UPDATE_ARTISTS:       False,
    KEY_ARTISTS_COL:          '',
    KEY_ARTISTS_APPEND:       False,
    KEY_LINK_COL:             '#links',
}

plugin_prefs = JSONConfig('plugins/MangaUpdates')
plugin_prefs.defaults[STORE_NAME] = DEFAULT_STORE_VALUES


class ConfigWidget(QWidget):

    def __init__(self, plugin_action):
        QWidget.__init__(self)
        self.plugin_action = plugin_action
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        c = plugin_prefs[STORE_NAME]

        # --- URL Discovery ---
        disc_group = QGroupBox('URL Discovery', self)
        layout.addWidget(disc_group)
        disc_layout = QGridLayout()
        disc_group.setLayout(disc_layout)

        self.scan_identifiers_cb = QCheckBox('Scan url/uri identifiers', self)
        self.scan_identifiers_cb.setChecked(c.get(KEY_SCAN_IDENTIFIERS, DEFAULT_STORE_VALUES[KEY_SCAN_IDENTIFIERS]))
        disc_layout.addWidget(self.scan_identifiers_cb, 0, 0, 1, 3)

        self.scan_comments_cb = QCheckBox('Scan Comments field', self)
        self.scan_comments_cb.setChecked(c.get(KEY_SCAN_COMMENTS, DEFAULT_STORE_VALUES[KEY_SCAN_COMMENTS]))
        disc_layout.addWidget(self.scan_comments_cb, 1, 0, 1, 3)

        self.scan_custom_col_cb = QCheckBox('Scan custom column:', self)
        self.scan_custom_col_cb.setChecked(c.get(KEY_SCAN_CUSTOM_COL, DEFAULT_STORE_VALUES[KEY_SCAN_CUSTOM_COL]))
        disc_layout.addWidget(self.scan_custom_col_cb, 2, 0)

        self.custom_col_edit = QLineEdit(c.get(KEY_CUSTOM_COL_NAME, DEFAULT_STORE_VALUES[KEY_CUSTOM_COL_NAME]), self)
        self.custom_col_edit.setMaximumWidth(120)
        disc_layout.addWidget(self.custom_col_edit, 2, 1)
        disc_layout.setColumnStretch(2, 1)

        # --- Field Mapping ---
        field_group = QGroupBox('What to update', self)
        layout.addWidget(field_group)
        field_layout = QGridLayout()
        field_group.setLayout(field_layout)

        row = 0

        # Genres
        self.update_genres_cb = QCheckBox('Genres \u2192', self)
        self.update_genres_cb.setChecked(c.get(KEY_UPDATE_GENRES, DEFAULT_STORE_VALUES[KEY_UPDATE_GENRES]))
        field_layout.addWidget(self.update_genres_cb, row, 0)
        self.genres_col_edit = QLineEdit(c.get(KEY_GENRES_COL, DEFAULT_STORE_VALUES[KEY_GENRES_COL]), self)
        self.genres_col_edit.setMaximumWidth(120)
        self.genres_col_edit.setPlaceholderText('(blank = skip)')
        field_layout.addWidget(self.genres_col_edit, row, 1)
        self.genres_append_cb = QCheckBox('Append (not replace)', self)
        self.genres_append_cb.setChecked(c.get(KEY_GENRES_APPEND, DEFAULT_STORE_VALUES[KEY_GENRES_APPEND]))
        field_layout.addWidget(self.genres_append_cb, row, 2)
        row += 1

        # Categories
        self.update_categories_cb = QCheckBox('Categories \u2192', self)
        self.update_categories_cb.setChecked(c.get(KEY_UPDATE_CATEGORIES, DEFAULT_STORE_VALUES[KEY_UPDATE_CATEGORIES]))
        field_layout.addWidget(self.update_categories_cb, row, 0)
        self.categories_col_edit = QLineEdit(c.get(KEY_CATEGORIES_COL, DEFAULT_STORE_VALUES[KEY_CATEGORIES_COL]), self)
        self.categories_col_edit.setMaximumWidth(120)
        self.categories_col_edit.setPlaceholderText('(blank = skip)')
        field_layout.addWidget(self.categories_col_edit, row, 1)
        self.categories_append_cb = QCheckBox('Append (not replace)', self)
        self.categories_append_cb.setChecked(c.get(KEY_CATEGORIES_APPEND, DEFAULT_STORE_VALUES[KEY_CATEGORIES_APPEND]))
        field_layout.addWidget(self.categories_append_cb, row, 2)
        row += 1

        # Associated Names
        self.update_assoc_names_cb = QCheckBox('Assoc. Names \u2192', self)
        self.update_assoc_names_cb.setChecked(c.get(KEY_UPDATE_ASSOC_NAMES, DEFAULT_STORE_VALUES[KEY_UPDATE_ASSOC_NAMES]))
        field_layout.addWidget(self.update_assoc_names_cb, row, 0)
        self.assoc_names_col_edit = QLineEdit(c.get(KEY_ASSOC_NAMES_COL, DEFAULT_STORE_VALUES[KEY_ASSOC_NAMES_COL]), self)
        self.assoc_names_col_edit.setMaximumWidth(120)
        self.assoc_names_col_edit.setPlaceholderText('(blank = skip)')
        field_layout.addWidget(self.assoc_names_col_edit, row, 1)
        self.assoc_names_append_cb = QCheckBox('Append (not replace)', self)
        self.assoc_names_append_cb.setChecked(c.get(KEY_ASSOC_NAMES_APPEND, DEFAULT_STORE_VALUES[KEY_ASSOC_NAMES_APPEND]))
        field_layout.addWidget(self.assoc_names_append_cb, row, 2)
        row += 1

        # Description
        self.update_desc_cb = QCheckBox('Description \u2192 Comments', self)
        self.update_desc_cb.setChecked(c.get(KEY_UPDATE_DESCRIPTION, DEFAULT_STORE_VALUES[KEY_UPDATE_DESCRIPTION]))
        field_layout.addWidget(self.update_desc_cb, row, 0, 1, 2)

        self.desc_append_cb = QCheckBox('Append (not replace)', self)
        self.desc_append_cb.setChecked(c.get(KEY_DESCRIPTION_APPEND, DEFAULT_STORE_VALUES[KEY_DESCRIPTION_APPEND]))
        field_layout.addWidget(self.desc_append_cb, row, 2)
        row += 1

        # Cover
        self.update_cover_cb = QCheckBox('Download cover', self)
        self.update_cover_cb.setChecked(c.get(KEY_UPDATE_COVER, DEFAULT_STORE_VALUES[KEY_UPDATE_COVER]))
        field_layout.addWidget(self.update_cover_cb, row, 0, 1, 3)
        row += 1

        # Authors
        self.update_authors_cb = QCheckBox('Update Authors', self)
        self.update_authors_cb.setChecked(c.get(KEY_UPDATE_AUTHORS, DEFAULT_STORE_VALUES[KEY_UPDATE_AUTHORS]))
        field_layout.addWidget(self.update_authors_cb, row, 0, 1, 2)
        self.authors_append_cb = QCheckBox('Append (not replace)', self)
        self.authors_append_cb.setChecked(c.get(KEY_AUTHORS_APPEND, DEFAULT_STORE_VALUES[KEY_AUTHORS_APPEND]))
        field_layout.addWidget(self.authors_append_cb, row, 2)
        row += 1

        # Artists → Authors
        self.artists_to_authors_cb = QCheckBox('Include Artists in Authors list', self)
        self.artists_to_authors_cb.setChecked(c.get(KEY_ARTISTS_TO_AUTHORS, DEFAULT_STORE_VALUES[KEY_ARTISTS_TO_AUTHORS]))
        field_layout.addWidget(self.artists_to_authors_cb, row, 0, 1, 3)
        row += 1

        # Artists → custom column
        self.update_artists_cb = QCheckBox('Artists \u2192', self)
        self.update_artists_cb.setChecked(c.get(KEY_UPDATE_ARTISTS, DEFAULT_STORE_VALUES[KEY_UPDATE_ARTISTS]))
        field_layout.addWidget(self.update_artists_cb, row, 0)
        self.artists_col_edit = QLineEdit(c.get(KEY_ARTISTS_COL, DEFAULT_STORE_VALUES[KEY_ARTISTS_COL]), self)
        self.artists_col_edit.setMaximumWidth(120)
        self.artists_col_edit.setPlaceholderText('(blank = skip)')
        field_layout.addWidget(self.artists_col_edit, row, 1)
        self.artists_append_cb = QCheckBox('Append (not replace)', self)
        self.artists_append_cb.setChecked(c.get(KEY_ARTISTS_APPEND, DEFAULT_STORE_VALUES[KEY_ARTISTS_APPEND]))
        field_layout.addWidget(self.artists_append_cb, row, 2)
        row += 1

        # Title
        self.update_title_cb = QCheckBox('Update Title (off by default)', self)
        self.update_title_cb.setChecked(c.get(KEY_UPDATE_TITLE, DEFAULT_STORE_VALUES[KEY_UPDATE_TITLE]))
        field_layout.addWidget(self.update_title_cb, row, 0, 1, 3)
        row += 1

        # Original Language (inferred from Type)
        self.update_orig_lang_cb = QCheckBox('Orig. Language \u2192', self)
        self.update_orig_lang_cb.setChecked(c.get(KEY_UPDATE_ORIG_LANG, DEFAULT_STORE_VALUES[KEY_UPDATE_ORIG_LANG]))
        field_layout.addWidget(self.update_orig_lang_cb, row, 0)
        self.orig_lang_col_edit = QLineEdit(c.get(KEY_ORIG_LANG_COL, DEFAULT_STORE_VALUES[KEY_ORIG_LANG_COL]), self)
        self.orig_lang_col_edit.setMaximumWidth(120)
        self.orig_lang_col_edit.setPlaceholderText('(blank = languages)')
        field_layout.addWidget(self.orig_lang_col_edit, row, 1)
        field_layout.addWidget(QLabel('Inferred from Type', self), row, 2)
        row += 1

        field_layout.setColumnStretch(3, 1)

        # --- Link Column ---
        link_group = QGroupBox('Link to MangaUpdates', self)
        layout.addWidget(link_group)
        link_layout = QGridLayout()
        link_group.setLayout(link_layout)

        link_layout.addWidget(QLabel('Write link to column:', self), 0, 0)
        self.link_col_edit = QLineEdit(c.get(KEY_LINK_COL, DEFAULT_STORE_VALUES[KEY_LINK_COL]), self)
        self.link_col_edit.setMaximumWidth(120)
        link_layout.addWidget(self.link_col_edit, 0, 1)
        link_layout.addWidget(QLabel('Appended as [MangaUpdates](url)', self), 0, 2)
        link_layout.setColumnStretch(2, 1)

        layout.addStretch()

    def save_settings(self):
        new_prefs = {
            KEY_SCAN_IDENTIFIERS:    self.scan_identifiers_cb.isChecked(),
            KEY_SCAN_COMMENTS:       self.scan_comments_cb.isChecked(),
            KEY_SCAN_CUSTOM_COL:     self.scan_custom_col_cb.isChecked(),
            KEY_CUSTOM_COL_NAME:     self.custom_col_edit.text().strip(),
            KEY_UPDATE_GENRES:        self.update_genres_cb.isChecked(),
            KEY_GENRES_COL:           self.genres_col_edit.text().strip(),
            KEY_GENRES_APPEND:        self.genres_append_cb.isChecked(),
            KEY_UPDATE_CATEGORIES:    self.update_categories_cb.isChecked(),
            KEY_CATEGORIES_COL:       self.categories_col_edit.text().strip(),
            KEY_CATEGORIES_APPEND:    self.categories_append_cb.isChecked(),
            KEY_UPDATE_ASSOC_NAMES:   self.update_assoc_names_cb.isChecked(),
            KEY_ASSOC_NAMES_COL:      self.assoc_names_col_edit.text().strip(),
            KEY_ASSOC_NAMES_APPEND:   self.assoc_names_append_cb.isChecked(),
            KEY_UPDATE_DESCRIPTION:   self.update_desc_cb.isChecked(),
            KEY_DESCRIPTION_APPEND:   self.desc_append_cb.isChecked(),
            KEY_UPDATE_COVER:         self.update_cover_cb.isChecked(),
            KEY_UPDATE_AUTHORS:       self.update_authors_cb.isChecked(),
            KEY_AUTHORS_APPEND:       self.authors_append_cb.isChecked(),
            KEY_ARTISTS_TO_AUTHORS:   self.artists_to_authors_cb.isChecked(),
            KEY_UPDATE_ARTISTS:       self.update_artists_cb.isChecked(),
            KEY_ARTISTS_COL:          self.artists_col_edit.text().strip(),
            KEY_ARTISTS_APPEND:       self.artists_append_cb.isChecked(),
            KEY_UPDATE_TITLE:         self.update_title_cb.isChecked(),
            KEY_UPDATE_ORIG_LANG:     self.update_orig_lang_cb.isChecked(),
            KEY_ORIG_LANG_COL:        self.orig_lang_col_edit.text().strip(),
            KEY_LINK_COL:             self.link_col_edit.text().strip(),
        }
        plugin_prefs[STORE_NAME] = new_prefs
