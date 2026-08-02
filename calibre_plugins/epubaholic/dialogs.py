from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import six
import os, traceback
try:
    from qt.core import (QVBoxLayout, QLabel, QCheckBox, QGridLayout,
                      QGroupBox, Qt, QDialogButtonBox, QWidget,
                      QProgressDialog, QTimer, QScrollArea)
except ImportError:
    from PyQt5.Qt import (QVBoxLayout, QLabel, QCheckBox, QGridLayout,
                      QGroupBox, Qt, QDialogButtonBox, QWidget,
                      QProgressDialog, QTimer, QScrollArea)

# QWidget and QScrollArea added to support scrolling dialog box

from calibre.ebooks.metadata import authors_to_string
from calibre.gui2 import gprefs, warning_dialog, error_dialog
from calibre.gui2.convert.metadata import create_opf_file, create_cover_file
from calibre.ptempfile import remove_dir
from calibre.utils.config_base import tweaks

import calibre_plugins.epubaholic.config as cfg
from calibre_plugins.epubaholic.common_dialogs import SizePersistedDialog
from calibre_plugins.epubaholic.common_widgets import ImageTitleLayout


META_OPTIONS = [
    ('update_metadata', 'Update metadata', 'Update the manifest with the latest calibre metadata\nand replace an existing identifiable cover if possible.'),
    ('add_unmanifested_files', 'Add unmanifested files to manifest', 'Add files to manifest that are in the epub but do not exist in the .opf manifest\n(excluding iTunes/calibre bookmarks)'),
    ('remove_calibre_bookmarks', 'Remove calibre bookmark files', 'Remove any bookmark files added by the calibre ebook viewer'),
    ('extract_ao3_url', 'Extract AO3 URL to identifier', 'Find the archiveofourown.org/works/ link in the epub\nand save it as a uri: identifier'),
]

TEXTREPLACE_OPTIONS = [
    ('smarten_punctuation', 'Smarten punctuation', 'Convert html to use smart quotes and emdash characters'),
    ('consistent_ellipsis', 'Consistent ellipsis', 'Standardizes...ellipses formatting'),
    ('capitalize_paragraphs', 'Capitalize paragraphs', 'Makes all paragraphs start with a capital letter'),
    ('normalize_names', 'Normalize names', 'Standardizes different spellings of character names'),
    ('female-to-male', 'Change female to male', 'Changes all female pronouns to male pronouns'),
    # I've run out of room in this box
]

STYLE_OPTIONS = [
    ('inline_styles_to_tags', 'Replace inline styles with tags', 'Replace inline css styles with appropriate tags'),
    ('strip_leftover_styles', 'Strip leftover styles', 'Remove styles leftover after replacing inline css styles with tags'),
    ('strip_spans', 'Strip spans', 'Remove spans without attributes'),
    ('lily_junk_cleanup', 'Lily junk cleanup', 'Remove Lily HTML junk'),
    ('cherrymist_loading', 'Find cherrymist loading pages', 'Mark loading placeholder pages in #readlocation'),
]

IMPORT_OPTIONS = [
    ('import_chapters', 'Import chapters', 'Import chapters from a folder of html files'),
    ('appy_replacements_to_imports', 'Apply replacements to imported chapters', 'Apply the text replacements selected to the imported chapters as well'),
    # Apply replacements to existing chapters
    # Apply replacements to chapter range
    #   [ ] to [ ] (e.g. 0 to 10 or 50 to last)
]

ALL_OPTIONS = META_OPTIONS + TEXTREPLACE_OPTIONS + STYLE_OPTIONS + IMPORT_OPTIONS

class ModifyEpubDialog(SizePersistedDialog):
    """
    Configure which options you want applied during the modify process
    """
    def __init__(self, gui, plugin_action):
        self.plugin_action = plugin_action
        # This is what determines what options were already selected from previous use
        SizePersistedDialog.__init__(self, gui, 'epubaholic plugin:options dialog')
        self.setWindowTitle('Epubaholic')
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        title_layout = ImageTitleLayout(self, 'images/epubaholic_book.png', 'Epubaholic Options')
        layout.addLayout(title_layout)

        # Make dialog scrollable for smaller screens
        scrollable = QScrollArea()
        scrollcontent = QWidget()
        scrollable.setWidget(scrollcontent)
        scrollable.setWidgetResizable(True)
        layout.addWidget(scrollable)

        layout = QVBoxLayout()
        scrollcontent.setLayout(layout)

        layout.addSpacing(5)
        self.main_layout = QGridLayout()
        layout.addLayout(self.main_layout, 1)
        options = gprefs.get(self.unique_pref_name+':settings', {})

        self._add_groupbox(0, 0, 'HTML && Styles', STYLE_OPTIONS, options)
        self._add_groupbox(0, 1, 'Text Replacements', TEXTREPLACE_OPTIONS, options)

        self._add_groupbox(1, 0, 'Meta', META_OPTIONS, options)
        self._add_groupbox(1, 1, 'Import Options', IMPORT_OPTIONS, options)

        layout.addSpacing(10)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._ok_clicked)
        button_box.rejected.connect(self.reject)
        self.select_none_button = button_box.addButton(' Clear all ', QDialogButtonBox.ResetRole)
        self.select_none_button.setToolTip('Clear all selections')
        self.select_none_button.clicked.connect(self._select_none_clicked)
        self.save_button = button_box.addButton(' Save ', QDialogButtonBox.ResetRole)
        self.save_button.setToolTip('Save the current selected settings for future recall with the Restore button')
        self.save_button.clicked.connect(self._save_clicked)
        self.restore_button = button_box.addButton(' Restore ', QDialogButtonBox.ResetRole)
        self.restore_button.setToolTip('Restore your settings set when the Save button was last clicked')
        self.restore_button.clicked.connect(self._restore_clicked)
        layout.addWidget(button_box)

        self.resize_dialog()

    def _add_groupbox(self, row, col, title, option_info, options):
        groupbox = QGroupBox(title)
        self.main_layout.addWidget(groupbox, row, col, 1, 1)
        groupbox_layout = QVBoxLayout()
        groupbox.setLayout(groupbox_layout)

        for key, text, tooltip in option_info:
            checkbox = QCheckBox(text, self)
            checkbox.setToolTip(tooltip)
            checkbox.setCheckState(Qt.Checked if options.get(key, False) else Qt.Unchecked)
            setattr(self, key, checkbox)
            groupbox_layout.addWidget(checkbox)
        groupbox_layout.addStretch(-5)

    def _ok_clicked(self):
        self._set_options()
        gprefs.set(self.unique_pref_name+':settings', self.options)

        # Only if the user has checked at least one option will we continue
        for key in self.options:
            if self.options[key]:
                self.accept()
                return
        return error_dialog(self, 'No options selected',
                            'You must select at least one option to continue',
                            show=True, show_copy_button=False)

    def _set_options(self):
        self.options = {}
        for option_name, _t, _tt in ALL_OPTIONS:
            self.options[option_name] = getattr(self, option_name).checkState() == Qt.Checked

    def _select_none_clicked(self):
        for option_name, _t, _tt in ALL_OPTIONS:
            getattr(self, option_name).setCheckState(Qt.Unchecked)

    def _save_clicked(self):
        self._set_options()
        cfg.plugin_prefs[cfg.STORE_SAVED_SETTINGS] = [k for k,v in six.iteritems(self.options) if v]

    def _restore_clicked(self):
        self._select_none_clicked()
        for option_name in cfg.plugin_prefs[cfg.STORE_SAVED_SETTINGS]:
            if hasattr(self, option_name):
                getattr(self, option_name).setCheckState(Qt.Checked)


class QueueProgressDialog(QProgressDialog):

    def __init__(self, gui, book_epubs, tdir, options, queue, db):
        QProgressDialog.__init__(self, 'Working...', 'Cancel', 0, len(book_epubs), gui)
        self.setWindowTitle('Queueing books for modifying epubs')
        self.setMinimumWidth(500)
        self.book_epubs, self.tdir, self.options, self.queue, self.db = \
            book_epubs, tdir, options, queue, db
        self.gui = gui
        self.i, self.bad, self.books_to_modify = 0, [], []
        # QTimer workaround on Win 10 on first go for Win10/Qt6 users not displaying dialog properly.
        QTimer.singleShot(100, self.do_book)
        self.exec_()

    def do_book(self):
        book_id = self.book_epubs[self.i]
        self.i += 1

        try:
            mi, opf_file = create_opf_file(self.db, book_id)
            self.setLabelText('Queueing '+mi.title)
            cover_file = create_cover_file(self.db, book_id)
            cover_file_name = cover_file.name if cover_file else None
            authors = authors_to_string(self._authors_to_list(self.db, book_id))
            # Copy the book to the temp directory, using book id as filename
            epub_file = os.path.join(self.tdir, '%d.epub'%book_id)
            with open(epub_file, 'w+b') as f:
                self.db.copy_format_to(book_id, 'EPUB', f, index_is_id=True)
            self.books_to_modify.append((book_id, mi.title, authors, epub_file,
                                         opf_file.name, cover_file_name))
        except:
            traceback.print_exc()
            self.bad.append(book_id)

        self.setValue(self.i)
        if self.i >= len(self.book_epubs):
            return self.do_queue()
        else:
            QTimer.singleShot(0, self.do_book)

    def do_queue(self):
        if self.gui is None:
            # There is a nasty QT bug with the timers/logic above which can
            # result in the do_queue method being called twice
            return
        self.hide()
        if self.bad != []:
            res = []
            for book_id in self.bad:
                title = self.db.title(book_id, True)
                res.append('%s'%title)
            msg = '%s' % '\n'.join(res)
            warning_dialog(self.gui, 'Could not modify epub for some books',
                ('Could not modify %d of %d books, because no epub '
                'source format was found.') % (len(res), len(self.book_epubs)),
                msg).exec_()
        self.gui = None
        self.db = None
        # Queue a job to process these epub books
        self.queue(self.tdir, self.options, self.books_to_modify)

    def _authors_to_list(self, db, book_id):
        authors = db.authors(book_id, index_is_id=True)
        if authors:
            return [a.strip().replace('|',',') for a in authors.split(',')]
        return []


class AddBooksProgressDialog(QProgressDialog):

    def __init__(self, gui, modified_epubs, tdir):
        self.total_count = len(modified_epubs)
        QProgressDialog.__init__(self, 'Working...', 'Cancel', 0, self.total_count, gui)
        self.setWindowTitle('Adding %d modified epubs'% self.total_count +'...' )
        self.setMinimumWidth(500)
        self.modified_epubs, self.tdir = modified_epubs, tdir
        self.book_ids = list(modified_epubs.keys())
        self.gui = gui
        self.db = self.gui.current_db
        self.i = 0
        # QTimer workaround on Win 10 on first go for Win10/Qt6 users not displaying dialog properly.
        QTimer.singleShot(100, self.do_book_check)
        self.exec_()
        if self.db:
            self.do_close()

    def do_book_check(self):
        if self.i >= self.total_count:
            return self.do_close()
        book_id = self.book_ids[self.i]
        result = self.modified_epubs[book_id]
        # Handle both string paths and (path, custom_metadata) tuples
        if isinstance(result, tuple):
            epub_path = result[0]
        else:
            epub_path = result
        self.i += 1

        title = self.db.title(book_id, index_is_id=True)
        self.setLabelText('Adding: '+title)

        formats = self.db.formats(book_id, index_is_id=True)
        if tweaks['save_original_format_when_polishing'] and 'ORIGINAL_EPUB' not in formats:
            self.db.save_original_format(book_id, 'EPUB', notify=False)
        # Add the epub back, causing the size information to be updated
        self.db.add_format(book_id, 'EPUB', open(epub_path, 'rb'), index_is_id=True)
        self.setValue(self.i)

        QTimer.singleShot(0, self.do_book_check)

    def do_close(self):
        self.hide()
        self.db.update_last_modified(self.book_ids)
        remove_dir(self.tdir)
        self.gui.status_bar.show_message('epub files updated', 3000)
        self.gui = None
        self.db = None
