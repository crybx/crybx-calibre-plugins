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
KEY_SCAN_IDENTIFIERS  = 'scanIdentifiers'
KEY_SCAN_COMMENTS     = 'scanComments'
KEY_SCAN_CUSTOM_COL   = 'scanCustomCol'
KEY_CUSTOM_COL_NAME   = 'customColName'
KEY_SEARCH_TITLE_COLS = 'searchTitleCols'

# Field mapping
KEY_UPDATE_GENRES         = 'updateGenres'
KEY_GENRES_COL            = 'genresCol'
KEY_GENRES_APPEND         = 'genresAppend'
KEY_UPDATE_TAGS           = 'updateTags'
KEY_TAGS_COL              = 'tagsCol'
KEY_TAGS_APPEND           = 'tagsAppend'
KEY_UPDATE_DESCRIPTION    = 'updateDescription'
KEY_DESCRIPTION_APPEND    = 'descriptionAppend'
KEY_UPDATE_COVER          = 'updateCover'
KEY_UPDATE_AUTHORS        = 'updateAuthors'
KEY_AUTHORS_APPEND        = 'authorsAppend'
KEY_UPDATE_TITLE          = 'updateTitle'
KEY_UPDATE_ORIG_LANG      = 'updateOrigLang'
KEY_ORIG_LANG_COL         = 'origLangCol'
KEY_ARTISTS_TO_AUTHORS    = 'artistsToAuthors'
KEY_UPDATE_ARTISTS        = 'updateArtists'
KEY_ARTISTS_COL           = 'artistsCol'
KEY_ARTISTS_APPEND        = 'artistsAppend'
KEY_LINK_COL              = 'linkCol'
KEY_USER_AGENT            = 'userAgent'

DEFAULT_STORE_VALUES = {
    KEY_SCAN_IDENTIFIERS:  True,
    KEY_SCAN_COMMENTS:     True,
    KEY_SCAN_CUSTOM_COL:   True,
    KEY_CUSTOM_COL_NAME:   '#links',
    KEY_SEARCH_TITLE_COLS: 'title',
    KEY_UPDATE_GENRES:        True,
    KEY_GENRES_COL:           '#extratags',
    KEY_GENRES_APPEND:        True,
    KEY_UPDATE_TAGS:          True,
    KEY_TAGS_COL:             '#extratags',
    KEY_TAGS_APPEND:          True,
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

plugin_prefs = JSONConfig('plugins/MangaDex')
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
        self.scan_identifiers_cb.setChecked(c.get(KEY_SCAN_IDENTIFIERS, True))
        disc_layout.addWidget(self.scan_identifiers_cb, 0, 0, 1, 3)

        self.scan_comments_cb = QCheckBox('Scan Comments field', self)
        self.scan_comments_cb.setChecked(c.get(KEY_SCAN_COMMENTS, True))
        disc_layout.addWidget(self.scan_comments_cb, 1, 0, 1, 3)

        self.scan_custom_col_cb = QCheckBox('Scan custom column:', self)
        self.scan_custom_col_cb.setChecked(c.get(KEY_SCAN_CUSTOM_COL, True))
        disc_layout.addWidget(self.scan_custom_col_cb, 2, 0)

        self.custom_col_edit = QLineEdit(c.get(KEY_CUSTOM_COL_NAME, '#links'), self)
        self.custom_col_edit.setMaximumWidth(120)
        disc_layout.addWidget(self.custom_col_edit, 2, 1)

        disc_layout.addWidget(QLabel('Search title columns:', self), 3, 0)
        self.search_title_cols_edit = QLineEdit(
            c.get(KEY_SEARCH_TITLE_COLS, DEFAULT_STORE_VALUES[KEY_SEARCH_TITLE_COLS]), self)
        self.search_title_cols_edit.setPlaceholderText('#originaltitle, title')
        self.search_title_cols_edit.setToolTip(
            'Comma-separated list of columns to use for the search field.\n'
            'Tries each in order; uses the first non-empty value.\n'
            'Example: #originaltitle, title')
        disc_layout.addWidget(self.search_title_cols_edit, 3, 1, 1, 2)
        disc_layout.setColumnStretch(2, 1)

        # --- Field Mapping ---
        field_group = QGroupBox('What to update', self)
        layout.addWidget(field_group)
        field_layout = QGridLayout()
        field_group.setLayout(field_layout)

        row = 0

        # Genres
        self.update_genres_cb = QCheckBox('Genres \u2192', self)
        self.update_genres_cb.setChecked(c.get(KEY_UPDATE_GENRES, True))
        field_layout.addWidget(self.update_genres_cb, row, 0)
        self.genres_col_edit = QLineEdit(c.get(KEY_GENRES_COL, '#extratags'), self)
        self.genres_col_edit.setMaximumWidth(120)
        self.genres_col_edit.setPlaceholderText('(blank = skip)')
        field_layout.addWidget(self.genres_col_edit, row, 1)
        self.genres_append_cb = QCheckBox('Append (not replace)', self)
        self.genres_append_cb.setChecked(c.get(KEY_GENRES_APPEND, True))
        field_layout.addWidget(self.genres_append_cb, row, 2)
        row += 1

        # Tags (themes/format)
        self.update_tags_cb = QCheckBox('Tags \u2192', self)
        self.update_tags_cb.setChecked(c.get(KEY_UPDATE_TAGS, True))
        field_layout.addWidget(self.update_tags_cb, row, 0)
        self.tags_col_edit = QLineEdit(c.get(KEY_TAGS_COL, '#extratags'), self)
        self.tags_col_edit.setMaximumWidth(120)
        self.tags_col_edit.setPlaceholderText('(blank = skip)')
        field_layout.addWidget(self.tags_col_edit, row, 1)
        self.tags_append_cb = QCheckBox('Append (not replace)', self)
        self.tags_append_cb.setChecked(c.get(KEY_TAGS_APPEND, True))
        field_layout.addWidget(self.tags_append_cb, row, 2)
        row += 1

        # Description
        self.update_desc_cb = QCheckBox('Description \u2192 Comments', self)
        self.update_desc_cb.setChecked(c.get(KEY_UPDATE_DESCRIPTION, True))
        field_layout.addWidget(self.update_desc_cb, row, 0, 1, 2)
        self.desc_append_cb = QCheckBox('Append (not replace)', self)
        self.desc_append_cb.setChecked(c.get(KEY_DESCRIPTION_APPEND, False))
        field_layout.addWidget(self.desc_append_cb, row, 2)
        row += 1

        # Cover
        self.update_cover_cb = QCheckBox('Download cover', self)
        self.update_cover_cb.setChecked(c.get(KEY_UPDATE_COVER, True))
        field_layout.addWidget(self.update_cover_cb, row, 0, 1, 3)
        row += 1

        # Authors
        self.update_authors_cb = QCheckBox('Update Authors', self)
        self.update_authors_cb.setChecked(c.get(KEY_UPDATE_AUTHORS, True))
        field_layout.addWidget(self.update_authors_cb, row, 0, 1, 2)
        self.authors_append_cb = QCheckBox('Append (not replace)', self)
        self.authors_append_cb.setChecked(c.get(KEY_AUTHORS_APPEND, False))
        field_layout.addWidget(self.authors_append_cb, row, 2)
        row += 1

        # Artists → Authors
        self.artists_to_authors_cb = QCheckBox('Include Artists in Authors list', self)
        self.artists_to_authors_cb.setChecked(c.get(KEY_ARTISTS_TO_AUTHORS, True))
        field_layout.addWidget(self.artists_to_authors_cb, row, 0, 1, 3)
        row += 1

        # Artists → custom column
        self.update_artists_cb = QCheckBox('Artists \u2192', self)
        self.update_artists_cb.setChecked(c.get(KEY_UPDATE_ARTISTS, False))
        field_layout.addWidget(self.update_artists_cb, row, 0)
        self.artists_col_edit = QLineEdit(c.get(KEY_ARTISTS_COL, ''), self)
        self.artists_col_edit.setMaximumWidth(120)
        self.artists_col_edit.setPlaceholderText('(blank = skip)')
        field_layout.addWidget(self.artists_col_edit, row, 1)
        self.artists_append_cb = QCheckBox('Append (not replace)', self)
        self.artists_append_cb.setChecked(c.get(KEY_ARTISTS_APPEND, False))
        field_layout.addWidget(self.artists_append_cb, row, 2)
        row += 1

        # Title
        self.update_title_cb = QCheckBox('Update Title (off by default)', self)
        self.update_title_cb.setChecked(c.get(KEY_UPDATE_TITLE, False))
        field_layout.addWidget(self.update_title_cb, row, 0, 1, 3)
        row += 1

        # Original Language
        self.update_orig_lang_cb = QCheckBox('Orig. Language \u2192', self)
        self.update_orig_lang_cb.setChecked(c.get(KEY_UPDATE_ORIG_LANG, True))
        field_layout.addWidget(self.update_orig_lang_cb, row, 0)
        self.orig_lang_col_edit = QLineEdit(c.get(KEY_ORIG_LANG_COL, ''), self)
        self.orig_lang_col_edit.setMaximumWidth(120)
        self.orig_lang_col_edit.setPlaceholderText('(blank = languages)')
        field_layout.addWidget(self.orig_lang_col_edit, row, 1)
        row += 1

        field_layout.setColumnStretch(3, 1)

        # --- Link Column ---
        link_group = QGroupBox('Link to MangaDex', self)
        layout.addWidget(link_group)
        link_layout = QGridLayout()
        link_group.setLayout(link_layout)

        link_layout.addWidget(QLabel('Write link to column:', self), 0, 0)
        self.link_col_edit = QLineEdit(c.get(KEY_LINK_COL, '#links'), self)
        self.link_col_edit.setMaximumWidth(120)
        link_layout.addWidget(self.link_col_edit, 0, 1)
        link_layout.addWidget(QLabel('Appended as [MangaDex](url)', self), 0, 2)
        link_layout.setColumnStretch(2, 1)

        layout.addStretch()

    def save_settings(self):
        new_prefs = {
            KEY_SCAN_IDENTIFIERS:    self.scan_identifiers_cb.isChecked(),
            KEY_SCAN_COMMENTS:       self.scan_comments_cb.isChecked(),
            KEY_SCAN_CUSTOM_COL:     self.scan_custom_col_cb.isChecked(),
            KEY_CUSTOM_COL_NAME:     self.custom_col_edit.text().strip(),
            KEY_SEARCH_TITLE_COLS:   self.search_title_cols_edit.text().strip(),
            KEY_UPDATE_GENRES:        self.update_genres_cb.isChecked(),
            KEY_GENRES_COL:           self.genres_col_edit.text().strip(),
            KEY_GENRES_APPEND:        self.genres_append_cb.isChecked(),
            KEY_UPDATE_TAGS:          self.update_tags_cb.isChecked(),
            KEY_TAGS_COL:             self.tags_col_edit.text().strip(),
            KEY_TAGS_APPEND:          self.tags_append_cb.isChecked(),
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
