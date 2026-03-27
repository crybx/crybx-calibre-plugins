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
KEY_GENRES_COL            = 'genresCol'          # str: column for NU genres (empty = skip)
KEY_GENRES_APPEND         = 'genresAppend'       # bool: append or replace
KEY_UPDATE_TAGS           = 'updateTags'         # bool: apply by default
KEY_TAGS_COL              = 'tagsCol'            # str: column for NU tags (empty = skip)
KEY_TAGS_APPEND           = 'tagsAppend'         # bool: append or replace
KEY_UPDATE_ASSOC_NAMES    = 'updateAssocNames'   # bool: apply by default
KEY_ASSOC_NAMES_COL       = 'assocNamesCol'      # str: column for associated names (empty = skip)
KEY_ASSOC_NAMES_APPEND    = 'assocNamesAppend'   # bool: append or replace
KEY_UPDATE_DESCRIPTION    = 'updateDescription'  # bool
KEY_DESCRIPTION_APPEND    = 'descriptionAppend'  # bool: append to existing comments
KEY_UPDATE_COVER          = 'updateCover'        # bool
KEY_UPDATE_AUTHORS        = 'updateAuthors'      # bool
KEY_AUTHORS_APPEND        = 'authorsAppend'      # bool: append or replace
KEY_UPDATE_TITLE          = 'updateTitle'        # bool
KEY_UPDATE_ORIG_LANG      = 'updateOrigLang'     # bool: write original language
KEY_ORIG_LANG_COL         = 'origLangCol'        # str: column for original language (empty = Calibre languages field)
KEY_CF_COOKIE             = 'cfCookie'           # str: Cloudflare cf_clearance cookie value
KEY_USER_AGENT            = 'userAgent'          # str: browser User-Agent to send (must match cookie)
KEY_LINK_COL              = 'linkCol'            # str: column to write NU link (markdown)

DEFAULT_STORE_VALUES = {
    KEY_SCAN_IDENTIFIERS:  True,
    KEY_SCAN_COMMENTS:     True,
    KEY_SCAN_CUSTOM_COL:   True,
    KEY_CUSTOM_COL_NAME:   '#links',
    KEY_UPDATE_GENRES:        True,
    KEY_GENRES_COL:           '#extratags',
    KEY_GENRES_APPEND:        True,
    KEY_UPDATE_TAGS:          True,
    KEY_TAGS_COL:             '#extratags',
    KEY_TAGS_APPEND:          True,
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
    KEY_CF_COOKIE:            '',
    KEY_USER_AGENT:           '',
    KEY_LINK_COL:             '#links',
}

plugin_prefs = JSONConfig('plugins/NovelUpdates')
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

        # Tags
        self.update_tags_cb = QCheckBox('Tags \u2192', self)
        self.update_tags_cb.setChecked(c.get(KEY_UPDATE_TAGS, DEFAULT_STORE_VALUES[KEY_UPDATE_TAGS]))
        field_layout.addWidget(self.update_tags_cb, row, 0)
        self.tags_col_edit = QLineEdit(c.get(KEY_TAGS_COL, DEFAULT_STORE_VALUES[KEY_TAGS_COL]), self)
        self.tags_col_edit.setMaximumWidth(120)
        self.tags_col_edit.setPlaceholderText('(blank = skip)')
        field_layout.addWidget(self.tags_col_edit, row, 1)
        self.tags_append_cb = QCheckBox('Append (not replace)', self)
        self.tags_append_cb.setChecked(c.get(KEY_TAGS_APPEND, DEFAULT_STORE_VALUES[KEY_TAGS_APPEND]))
        field_layout.addWidget(self.tags_append_cb, row, 2)
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
        self.update_desc_cb = QCheckBox('Description → Comments', self)
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

        # Title
        self.update_title_cb = QCheckBox('Update Title (off by default)', self)
        self.update_title_cb.setChecked(c.get(KEY_UPDATE_TITLE, DEFAULT_STORE_VALUES[KEY_UPDATE_TITLE]))
        field_layout.addWidget(self.update_title_cb, row, 0, 1, 3)
        row += 1

        # Original Language
        self.update_orig_lang_cb = QCheckBox('Orig. Language \u2192', self)
        self.update_orig_lang_cb.setChecked(c.get(KEY_UPDATE_ORIG_LANG, DEFAULT_STORE_VALUES[KEY_UPDATE_ORIG_LANG]))
        field_layout.addWidget(self.update_orig_lang_cb, row, 0)
        self.orig_lang_col_edit = QLineEdit(c.get(KEY_ORIG_LANG_COL, DEFAULT_STORE_VALUES[KEY_ORIG_LANG_COL]), self)
        self.orig_lang_col_edit.setMaximumWidth(120)
        self.orig_lang_col_edit.setPlaceholderText('(blank = languages)')
        field_layout.addWidget(self.orig_lang_col_edit, row, 1)
        row += 1

        field_layout.setColumnStretch(3, 1)

        # --- Link Column ---
        link_group = QGroupBox('Link to NovelUpdates', self)
        layout.addWidget(link_group)
        link_layout = QGridLayout()
        link_group.setLayout(link_layout)

        link_layout.addWidget(QLabel('Write link to column:', self), 0, 0)
        self.link_col_edit = QLineEdit(c.get(KEY_LINK_COL, DEFAULT_STORE_VALUES[KEY_LINK_COL]), self)
        self.link_col_edit.setMaximumWidth(120)
        link_layout.addWidget(self.link_col_edit, 0, 1)
        link_layout.addWidget(QLabel('Appended as [Novel Updates](url)', self), 0, 2)
        link_layout.setColumnStretch(2, 1)

        # --- Cloudflare Cookie ---
        cf_group = QGroupBox('Cloudflare (if site is blocked)', self)
        layout.addWidget(cf_group)
        cf_layout = QGridLayout()
        cf_group.setLayout(cf_layout)

        cf_layout.addWidget(QLabel('cf_clearance cookie:', self), 0, 0)
        self.cf_cookie_edit = QLineEdit(c.get(KEY_CF_COOKIE, ''), self)
        self.cf_cookie_edit.setPlaceholderText('Paste cf_clearance value (just the value, not the name=value)')
        cf_layout.addWidget(self.cf_cookie_edit, 0, 1)

        cf_layout.addWidget(QLabel('Browser User-Agent:', self), 1, 0)
        self.ua_edit = QLineEdit(c.get(KEY_USER_AGENT, ''), self)
        self.ua_edit.setPlaceholderText('Copy from browser DevTools → Network tab (must match the browser that got the cookie)')
        cf_layout.addWidget(self.ua_edit, 1, 1)
        cf_layout.setColumnStretch(1, 1)

        layout.addStretch()

    def save_settings(self):
        new_prefs = {
            KEY_SCAN_IDENTIFIERS:  self.scan_identifiers_cb.isChecked(),
            KEY_SCAN_COMMENTS:     self.scan_comments_cb.isChecked(),
            KEY_SCAN_CUSTOM_COL:   self.scan_custom_col_cb.isChecked(),
            KEY_CUSTOM_COL_NAME:   self.custom_col_edit.text().strip(),
            KEY_UPDATE_GENRES:        self.update_genres_cb.isChecked(),
            KEY_GENRES_COL:           self.genres_col_edit.text().strip(),
            KEY_GENRES_APPEND:        self.genres_append_cb.isChecked(),
            KEY_UPDATE_TAGS:          self.update_tags_cb.isChecked(),
            KEY_TAGS_COL:             self.tags_col_edit.text().strip(),
            KEY_TAGS_APPEND:          self.tags_append_cb.isChecked(),
            KEY_UPDATE_ASSOC_NAMES:   self.update_assoc_names_cb.isChecked(),
            KEY_ASSOC_NAMES_COL:      self.assoc_names_col_edit.text().strip(),
            KEY_ASSOC_NAMES_APPEND:   self.assoc_names_append_cb.isChecked(),
            KEY_UPDATE_DESCRIPTION:   self.update_desc_cb.isChecked(),
            KEY_DESCRIPTION_APPEND:   self.desc_append_cb.isChecked(),
            KEY_UPDATE_COVER:         self.update_cover_cb.isChecked(),
            KEY_UPDATE_AUTHORS:       self.update_authors_cb.isChecked(),
            KEY_AUTHORS_APPEND:       self.authors_append_cb.isChecked(),
            KEY_UPDATE_TITLE:         self.update_title_cb.isChecked(),
            KEY_UPDATE_ORIG_LANG:     self.update_orig_lang_cb.isChecked(),
            KEY_ORIG_LANG_COL:        self.orig_lang_col_edit.text().strip(),
            KEY_CF_COOKIE:            self.cf_cookie_edit.text().strip(),
            KEY_USER_AGENT:           self.ua_edit.text().strip(),
            KEY_LINK_COL:             self.link_col_edit.text().strip(),
        }
        plugin_prefs[STORE_NAME] = new_prefs
