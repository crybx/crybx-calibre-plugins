from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'

import re

try:
    from qt.core import (Qt, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                         QPushButton, QProgressBar, QTableWidget,
                         QTableWidgetItem, QAbstractItemView, QHeaderView,
                         QDialogButtonBox, QScrollArea, QWidget,
                         QThread, pyqtSignal, QPixmap, QCheckBox, QPlainTextEdit,
                         QComboBox, QLineEdit)
except ImportError:
    from PyQt5.Qt import (Qt, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                          QPushButton, QProgressBar, QTableWidget,
                          QTableWidgetItem, QAbstractItemView, QHeaderView,
                          QDialogButtonBox, QScrollArea, QWidget,
                          QThread, pyqtSignal, QPixmap, QCheckBox, QPlainTextEdit,
                          QComboBox)

from calibre_plugins.mangaupdates.jobs import FetchWorker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_COVER_W = 120
_COVER_H = 170


def _pixmap_from_bytes(data):
    if not data:
        return None
    pm = QPixmap()
    pm.loadFromData(data)
    return pm if not pm.isNull() else None


def _scale_pixmap(pm):
    return pm.scaled(_COVER_W, _COVER_H,
                     Qt.AspectRatioMode.KeepAspectRatio,
                     Qt.TransformationMode.SmoothTransformation)


def _cover_label(text=''):
    lbl = QLabel(text)
    lbl.setFixedSize(_COVER_W, _COVER_H)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet('border: 1px solid #888; background: #f0f0f0;')
    return lbl


def _strip_html(html):
    if not html:
        return ''
    try:
        from lxml import html as lxml_html
        return lxml_html.fromstring(html).text_content().strip()
    except Exception:
        return re.sub(r'<[^>]+>', '', html).strip()


# ---------------------------------------------------------------------------
# Background cover fetcher
# ---------------------------------------------------------------------------

class _CoverFetchWorker(QThread):
    cover_fetched = pyqtSignal(object)  # bytes or None

    def __init__(self, url, parent=None):
        QThread.__init__(self, parent)
        self.url = url

    def run(self):
        try:
            try:
                from urllib.request import Request, urlopen
            except ImportError:
                from urllib2 import Request, urlopen
            req = Request(self.url, headers={
                'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                               'AppleWebKit/537.36 (KHTML, like Gecko) '
                               'Chrome/120.0.0.0 Safari/537.36'),
                'Referer': 'https://www.mangaupdates.com/',
            })
            data = urlopen(req, timeout=15).read()
            self.cover_fetched.emit(data if len(data) > 1024 else None)
        except Exception:
            self.cover_fetched.emit(None)


# ---------------------------------------------------------------------------
# Download progress dialog
# ---------------------------------------------------------------------------

class DownloadProgressDialog(QDialog):

    def __init__(self, parent, books_data, config, db):
        QDialog.__init__(self, parent)
        self.books_data = books_data
        self.config = config
        self.db = db
        self.results = {}

        self.setWindowTitle('Downloading MangaUpdates Metadata')
        self.setMinimumWidth(450)

        layout = QVBoxLayout(self)
        self.setLayout(layout)

        self.status_label = QLabel('Starting...', self)
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(len(books_data))
        layout.addWidget(self.progress_bar)

        btn_layout = QHBoxLayout()
        layout.addLayout(btn_layout)
        btn_layout.addStretch()
        self.cancel_btn = QPushButton('Cancel', self)
        self.cancel_btn.clicked.connect(self._cancel)
        btn_layout.addWidget(self.cancel_btn)

        from calibre_plugins.mangaupdates.config import KEY_USER_AGENT
        user_agent = config.get(KEY_USER_AGENT, '').strip() or None
        self.worker = FetchWorker(books_data, user_agent=user_agent, parent=self)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, current, total, title):
        self.progress_bar.setValue(current)
        self.status_label.setText('Fetching: %s (%d/%d)' % (title, current + 1, total))

    def _on_finished(self, results):
        self.results = results
        self.progress_bar.setValue(self.progress_bar.maximum())
        self.accept()

    def _cancel(self):
        self.worker.abort()
        self.worker.wait(3000)
        self.reject()


# ---------------------------------------------------------------------------
# Per-book detail dialog
# ---------------------------------------------------------------------------

class BookDetailDialog(QDialog):
    '''
    Before/after view for a single book with per-field checkboxes.
    Checkbox state is written back to data['_apply_fields'] immediately
    on change so the main dialog can apply the choices.
    '''

    def __init__(self, parent, book_id, book_title, data, config, db, can_apply=False):
        QDialog.__init__(self, parent)
        self.setWindowTitle('Preview: ' + book_title)
        self.setMinimumSize(820, 600)
        self._data = data
        self._checkboxes = {}   # field_name → QCheckBox (standalone apply, no append)
        self._paired_cbs = {}   # field_name → (overwrite_cb, append_key, append_cb)
        self._combos     = {}   # field_name → QComboBox (pick-one fields)
        self._cover_worker = None

        from calibre_plugins.mangaupdates.config import (
            KEY_UPDATE_TITLE, KEY_UPDATE_AUTHORS, KEY_AUTHORS_APPEND,
            KEY_UPDATE_DESCRIPTION, KEY_DESCRIPTION_APPEND,
            KEY_UPDATE_ORIG_LANG, KEY_ORIG_LANG_COL, KEY_UPDATE_COVER,
            KEY_UPDATE_GENRES, KEY_GENRES_COL, KEY_GENRES_APPEND,
            KEY_UPDATE_CATEGORIES, KEY_CATEGORIES_COL, KEY_CATEGORIES_APPEND,
            KEY_UPDATE_ASSOC_NAMES, KEY_ASSOC_NAMES_COL, KEY_ASSOC_NAMES_APPEND,
            KEY_UPDATE_ARTISTS, KEY_ARTISTS_COL, KEY_ARTISTS_APPEND,
            KEY_ARTISTS_TO_AUTHORS)

        layout = QVBoxLayout(self)
        self.setLayout(layout)

        saved = data.get('_apply_fields')

        # --- Scrollable field sections ---
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)

        container = QWidget()
        sections_layout = QVBoxLayout(container)
        sections_layout.setSpacing(4)
        sections_layout.setContentsMargins(4, 4, 4, 4)

        # Column header row
        _CTR_W = 90
        hdr = QWidget()
        hdr.setStyleSheet('background: #e0e0e0;')
        hdr_h = QHBoxLayout(hdr)
        hdr_h.setContentsMargins(0, 3, 0, 3)
        hdr_h.setSpacing(8)
        _hl = QLabel('<b>From Manga Updates</b>')
        _hl.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        hdr_h.addWidget(_hl, 1)
        _uncheck_btn = QPushButton('Uncheck all')
        _uncheck_btn.setFixedWidth(_CTR_W)
        _uncheck_btn.setStyleSheet(
            'QPushButton { color: #0066cc; text-decoration: underline; '
            'border: none; background: transparent; padding: 0; }'
            'QPushButton:hover { color: #003399; }')
        _uncheck_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        _uncheck_btn.clicked.connect(self._uncheck_all)
        hdr_h.addWidget(_uncheck_btn)
        _hr = QLabel('<b>Current</b>')
        _hr.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        hdr_h.addWidget(_hr, 1)
        sections_layout.addWidget(hdr)

        # Cover row
        cover_url       = data.get('cover_url')
        cur_cover_bytes = db.cover(book_id, index_is_id=True)

        cover_section = QWidget()
        cov_row = QHBoxLayout(cover_section)
        cov_row.setSpacing(8)
        cov_row.setContentsMargins(0, 2, 0, 2)

        # Left: new cover
        cov_left = QWidget()
        cov_left_v = QVBoxLayout(cov_left)
        cov_left_v.setSpacing(2)
        cov_left_v.setContentsMargins(0, 0, 0, 0)
        cov_left_v.addWidget(QLabel('<b>Cover</b>'))
        new_img_row = QHBoxLayout()
        self._new_cover_img = _cover_label('Loading\u2026' if cover_url else '(no cover)')
        new_img_row.addWidget(self._new_cover_img)
        self._new_size_lbl = QLabel('')
        new_img_row.addWidget(self._new_size_lbl, 0, Qt.AlignmentFlag.AlignVCenter)
        new_img_row.addStretch()
        cov_left_v.addLayout(new_img_row)
        cov_left_v.addStretch()
        cov_row.addWidget(cov_left, 1)

        # Center: Apply checkbox
        cov_center = QWidget()
        cov_center.setFixedWidth(_CTR_W)
        cov_center_v = QVBoxLayout(cov_center)
        cov_center_v.setSpacing(4)
        cov_center_v.setContentsMargins(4, 0, 4, 0)
        cov_center_v.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        _arr = QLabel('\u2192')
        _arr.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        cov_center_v.addWidget(_arr)
        cover_cb = QCheckBox('Overwrite')
        cover_cb.setEnabled(bool(cover_url))
        if saved is not None:
            cover_cb.setChecked(saved.get('cover', False))
        else:
            cover_cb.setChecked(bool(cover_url) and config.get(KEY_UPDATE_COVER, True))
        cover_cb.stateChanged.connect(self._save_choices)
        self._checkboxes['cover'] = cover_cb
        cov_center_v.addWidget(cover_cb)
        cov_row.addWidget(cov_center)

        # Right: current cover
        cov_right = QWidget()
        cov_right_v = QVBoxLayout(cov_right)
        cov_right_v.setSpacing(2)
        cov_right_v.setContentsMargins(0, 0, 0, 0)
        cov_right_v.addWidget(QLabel('<b>cover</b>'))
        cur_img_row = QHBoxLayout()
        cur_img = _cover_label()
        cur_img_row.addWidget(cur_img)
        self._cur_size_lbl = QLabel('')
        cur_img_row.addWidget(self._cur_size_lbl, 0, Qt.AlignmentFlag.AlignVCenter)
        cur_img_row.addStretch()
        cov_right_v.addLayout(cur_img_row)
        cov_right_v.addStretch()
        cov_row.addWidget(cov_right, 1)

        sections_layout.addWidget(cover_section)

        # Load covers
        if cur_cover_bytes:
            pm = _pixmap_from_bytes(cur_cover_bytes)
            if pm:
                self._cur_size_lbl.setText('%d \u00d7 %d' % (pm.width(), pm.height()))
                cur_img.setPixmap(_scale_pixmap(pm))
                cur_img.setText('')
        if cover_url:
            self._cover_worker = _CoverFetchWorker(cover_url, self)
            self._cover_worker.cover_fetched.connect(self._on_cover_fetched)
            self._cover_worker.start()

        # Gather current values
        current_title = db.title(book_id, index_is_id=True) or ''
        from calibre.utils.localization import calibre_langcode_to_name
        if hasattr(db, 'new_api'):
            current_authors = ' & '.join(db.new_api.field_for('authors', book_id) or [])
            raw_langs       = db.new_api.field_for('languages', book_id) or []
            current_langs   = ', '.join(calibre_langcode_to_name(l) for l in raw_langs)
        else:
            _a = db.authors(book_id, index_is_id=True) or ''
            current_authors = _a
            _l = db.languages(book_id, index_is_id=True) or ''
            if isinstance(_l, str):
                current_langs = calibre_langcode_to_name(_l) if _l else ''
            else:
                current_langs = ', '.join(calibre_langcode_to_name(l) for l in (_l or []))
        current_desc = _strip_html(db.comments(book_id, index_is_id=True) or '')

        genres_col      = config.get(KEY_GENRES_COL,      '#extratags').strip()
        categories_col  = config.get(KEY_CATEGORIES_COL,  '#extratags').strip()
        assoc_names_col = config.get(KEY_ASSOC_NAMES_COL, '').strip()
        artists_col     = config.get(KEY_ARTISTS_COL,     '').strip()

        def _col_value(col):
            if not col:
                return ''
            try:
                if hasattr(db, 'new_api'):
                    val = db.new_api.field_for(col, book_id) or []
                else:
                    val = db.get_custom(book_id, label=col.lstrip('#'),
                                        index_is_id=True) or []
                return ', '.join(val) if isinstance(val, (list, tuple)) else str(val or '')
            except Exception:
                return ''

        current_genres_val      = _col_value(genres_col)
        current_categories_val  = _col_value(categories_col)
        current_assoc_names_val = _col_value(assoc_names_col)

        # Gather new values
        new_title        = data.get('title') or ''
        new_desc         = _strip_html(data.get('description') or '')
        # Original language (inferred from type)
        from calibre_plugins.mangaupdates.action import _mu_type_to_language
        from calibre_plugins.mangaupdates.common_lang import resolve_lang_for_column as _resolve_lang_for_column
        from calibre.utils.localization import calibre_langcode_to_name
        mu_type          = data.get('type') or ''
        lang_code        = _mu_type_to_language(mu_type)
        orig_lang_col    = config.get(KEY_ORIG_LANG_COL, '').strip()
        orig_lang_dest   = orig_lang_col or 'languages'
        if lang_code and orig_lang_col:
            new_orig_lang = _resolve_lang_for_column(db, orig_lang_col, lang_code) or ''
        elif lang_code:
            new_orig_lang = calibre_langcode_to_name(lang_code)
        else:
            new_orig_lang = ''
        current_orig_lang_val = _col_value(orig_lang_col) if orig_lang_col else current_langs
        new_genres       = ', '.join(data.get('genres') or [])
        new_categories   = ', '.join(data.get('categories') or [])
        assoc_names_list = data.get('assoc_names') or []

        # Authors + Artists: when artistsToAuthors is on, combine them for display
        artists_to_authors = config.get(KEY_ARTISTS_TO_AUTHORS, True)
        if artists_to_authors and data.get('artists'):
            combined = list(data.get('authors') or [])
            for a in (data.get('artists') or []):
                if a not in combined:
                    combined.append(a)
            new_authors = ' & '.join(combined)
        else:
            new_authors = ' & '.join(data.get('authors') or [])

        # 9-tuple: (fname, clean_name, dest_label, cur_val, new_val,
        #           cfg_default, append_key, append_def, choices)
        field_defs = [
            ('title', 'Title', 'title',
             current_title, new_title,
             config.get(KEY_UPDATE_TITLE, False), None, None, None),
            ('authors', 'Authors', 'authors',
             current_authors, new_authors,
             config.get(KEY_UPDATE_AUTHORS, True),
             'authors_append', config.get(KEY_AUTHORS_APPEND, False), None),
        ]

        # Artists row: only show when writing to a separate custom column
        if not artists_to_authors and artists_col:
            new_artists = ' & '.join(data.get('artists') or [])
            field_defs.append(
                ('artists', 'Artists', artists_col,
                 _col_value(artists_col), new_artists,
                 config.get(KEY_UPDATE_ARTISTS, False),
                 'artists_append', config.get(KEY_ARTISTS_APPEND, False), None))

        field_defs += [
            ('orig_lang', 'Orig. Language', orig_lang_dest,
             current_orig_lang_val, new_orig_lang,
             config.get(KEY_UPDATE_ORIG_LANG, True), None, None, None),
            ('genres', 'Genres', genres_col or '(not set)',
             current_genres_val, new_genres,
             bool(genres_col) and config.get(KEY_UPDATE_GENRES, True),
             'genres_append', config.get(KEY_GENRES_APPEND, True), None),
            ('categories', 'Categories', categories_col or '(not set)',
             current_categories_val, new_categories,
             bool(categories_col) and config.get(KEY_UPDATE_CATEGORIES, True),
             'categories_append', config.get(KEY_CATEGORIES_APPEND, True), None),
            ('assoc_names', 'Assoc. Names', assoc_names_col or '(not set)',
             current_assoc_names_val, '',
             bool(assoc_names_col) and config.get(KEY_UPDATE_ASSOC_NAMES, True),
             'assoc_names_append', config.get(KEY_ASSOC_NAMES_APPEND, True),
             assoc_names_list),
            ('description', 'Description', 'comments',
             current_desc, new_desc,
             config.get(KEY_UPDATE_DESCRIPTION, True),
             'description_append', config.get(KEY_DESCRIPTION_APPEND, False), None),
        ]

        for fname, clean_name, dest_label, cur_val, new_val, cfg_default, \
                append_key, append_def, choices in field_defs:

            if choices is not None:
                has_new = bool(choices)
            else:
                has_new = bool(new_val.strip()) and new_val != '(not found)'

            if saved is not None:
                checked = saved.get(fname, False)
            else:
                checked = cfg_default and has_new

            # Per-field section row
            section = QWidget()
            row_h = QHBoxLayout(section)
            row_h.setSpacing(8)
            row_h.setContentsMargins(0, 2, 0, 2)

            # Left column: MU source value
            left_w = QWidget()
            left_v = QVBoxLayout(left_w)
            left_v.setSpacing(2)
            left_v.setContentsMargins(0, 0, 0, 0)
            left_v.addWidget(QLabel('<b>%s</b>' % clean_name))

            # Right column: current library value
            right_w = QWidget()
            right_v = QVBoxLayout(right_w)
            right_v.setSpacing(2)
            right_v.setContentsMargins(0, 0, 0, 0)
            right_v.addWidget(QLabel('<b>%s</b>' % dest_label))

            if choices is not None:
                combo = QComboBox()
                for choice in choices:
                    combo.addItem(choice)
                combo.setEnabled(has_new)
                if saved is not None:
                    idx = combo.findText(saved.get(fname + '_value', ''))
                    if idx >= 0:
                        combo.setCurrentIndex(idx)
                combo.currentTextChanged.connect(self._save_choices)
                self._combos[fname] = combo
                left_v.addWidget(combo)
                right_v.addWidget(self._field_cell(cur_val))
            else:
                cell_h = max(self._cell_height(new_val), self._cell_height(cur_val))
                new_cell = self._field_cell(new_val, height=cell_h)
                if has_new and cur_val.strip() != new_val.strip():
                    new_cell.setStyleSheet('background: #fffacc; border: 1px solid #ddd;')
                if not has_new:
                    new_cell.setStyleSheet('background: #fafafa; border: 1px solid #ddd; color: #aaa;')
                left_v.addWidget(new_cell)
                right_v.addWidget(self._field_cell(cur_val, height=cell_h))

            row_h.addWidget(left_w, 1)

            # Center column: Overwrite/Append or Apply
            center_w = QWidget()
            center_w.setFixedWidth(_CTR_W)
            center_v = QVBoxLayout(center_w)
            center_v.setSpacing(1)
            center_v.setContentsMargins(4, 0, 4, 0)
            center_v.setAlignment(Qt.AlignmentFlag.AlignTop)
            _arr = QLabel('\u2192')
            _arr.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            center_v.addWidget(_arr)

            if append_key is not None:
                if saved is not None:
                    _was_apply  = saved.get(fname, False)
                    _was_append = saved.get(append_key, False)
                    _ow_chk  = _was_apply and not _was_append
                    _app_chk = _was_apply and _was_append
                else:
                    _ow_chk  = checked and not append_def
                    _app_chk = checked and append_def

                ow_cb  = QCheckBox('Overwrite')
                ow_cb.setChecked(_ow_chk)
                ow_cb.setEnabled(has_new)

                app_cb = QCheckBox('Append')
                app_cb.setChecked(_app_chk)
                app_cb.setEnabled(has_new)

                def _make_exclusive(this_cb, other_cb):
                    def _on_state(state):
                        if state:
                            other_cb.blockSignals(True)
                            other_cb.setChecked(False)
                            other_cb.blockSignals(False)
                        self._save_choices()
                    this_cb.stateChanged.connect(_on_state)

                _make_exclusive(ow_cb, app_cb)
                _make_exclusive(app_cb, ow_cb)

                self._paired_cbs[fname] = (ow_cb, append_key, app_cb)
                center_v.addWidget(ow_cb)
                center_v.addWidget(app_cb)
            else:
                cb = QCheckBox('Overwrite')
                cb.setChecked(checked)
                cb.setEnabled(has_new)
                cb.setToolTip('Overwrite existing value')
                cb.stateChanged.connect(self._save_choices)
                self._checkboxes[fname] = cb
                center_v.addWidget(cb)

            row_h.addWidget(center_w)
            row_h.addWidget(right_w, 1)

            sections_layout.addWidget(section)

        sections_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

        buttons = QDialogButtonBox(self)
        if can_apply:
            apply_btn = buttons.addButton('Apply', QDialogButtonBox.ButtonRole.AcceptRole)
            apply_btn.setToolTip('Apply these changes to the library and remove from list')
            _ = apply_btn
        close_btn = buttons.addButton('Close', QDialogButtonBox.ButtonRole.RejectRole)
        _ = close_btn
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Write initial state
        self._save_choices()

    def _cell_height(self, text, chars_per_line=45):
        """Estimate the pixel height needed to show text without scrolling."""
        if not hasattr(self, '_fm_cache'):
            tmp = QPlainTextEdit()
            self._fm_cache = tmp.fontMetrics()
        fm = self._fm_cache
        line_h = fm.lineSpacing()
        visual_lines = sum(
            max(1, (len(para) + chars_per_line - 1) // chars_per_line)
            for para in text.split('\n')
        )
        return max(line_h * min(visual_lines, 6) + 12, line_h + 10)

    def _field_cell(self, text, height=None):
        edit = QPlainTextEdit(text)
        edit.setReadOnly(True)
        if height is None:
            height = self._cell_height(text)
        edit.setFixedHeight(height)
        edit.setStyleSheet('background: #fafafa; border: 1px solid #ddd;')
        return edit

    def _uncheck_all(self):
        for cb in self._checkboxes.values():
            cb.setChecked(False)
        for ow_cb, _key, app_cb in self._paired_cbs.values():
            ow_cb.setChecked(False)
            app_cb.setChecked(False)

    def _save_choices(self):
        result = {fname: cb.isChecked() for fname, cb in self._checkboxes.items()}
        for fname, (ow_cb, append_key, app_cb) in self._paired_cbs.items():
            result[fname]      = ow_cb.isChecked() or app_cb.isChecked()
            result[append_key] = app_cb.isChecked()
        for fname, combo in self._combos.items():
            result[fname + '_value'] = combo.currentText()
        self._data['_apply_fields'] = result

    def _on_cover_fetched(self, data):
        pm = _pixmap_from_bytes(data)
        if pm:
            self._new_size_lbl.setText('%d \u00d7 %d' % (pm.width(), pm.height()))
            self._new_cover_img.setPixmap(_scale_pixmap(pm))
            self._new_cover_img.setText('')
        else:
            self._new_cover_img.setText('(failed)')


# ---------------------------------------------------------------------------
# Main apply dialog
# ---------------------------------------------------------------------------

class ApplyMetadataDialog(QDialog):

    def __init__(self, parent, results, books_data, config, db, apply_book_fn=None):
        QDialog.__init__(self, parent)
        self.results         = results
        self.books_data      = books_data
        self.config          = config
        self.db              = db
        self._apply_book_fn  = apply_book_fn

        self.setWindowTitle('Apply MangaUpdates Metadata')
        self.setMinimumWidth(620)
        self.setMinimumHeight(300)

        layout = QVBoxLayout(self)
        self.setLayout(layout)

        book_titles = {bid: title for bid, title, _ in books_data}
        found     = [(bid, results[bid]) for bid in results
                     if results[bid] and not results[bid].get('_failed')]
        not_found = [bid for bid in results
                     if not results[bid] or results[bid].get('_failed')]

        summary = QLabel(
            '<b>%d book(s)</b> fetched successfully, <b>%d</b> not found / failed.'
            % (len(found), len(not_found))
        )
        layout.addWidget(summary)

        if found:
            hint = QLabel(
                'Double-click a row to preview changes and choose which fields to apply.')
            hint.setStyleSheet('color: #555; font-style: italic;')
            layout.addWidget(hint)

            self._found       = found
            self._book_titles = book_titles

            table = QTableWidget(len(found), 4, self)
            table.setHorizontalHeaderLabels(['Book', 'MU Title', 'Authors', 'Cover'])
            table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            hh = table.horizontalHeader()
            hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            table.verticalHeader().setVisible(False)

            for row, (book_id, data) in enumerate(found):
                table.setItem(row, 0, QTableWidgetItem(
                    book_titles.get(book_id, str(book_id))))
                table.setItem(row, 1, QTableWidgetItem(data.get('title') or ''))
                table.setItem(row, 2, QTableWidgetItem(
                    ' & '.join(data.get('authors') or [])))
                table.setItem(row, 3, QTableWidgetItem(
                    '\u2713' if data.get('cover_url') else '\u2013'))

            table.cellDoubleClicked.connect(self._on_double_click)
            layout.addWidget(table)
            self._table = table

        if not_found:
            titles = ', '.join(book_titles.get(bid, str(bid)) for bid in not_found)
            warn = QLabel('<i>Not found: %s</i>' % titles)
            warn.setWordWrap(True)
            layout.addWidget(warn)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText('Apply to Library')
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_double_click(self, row, _col):
        book_id, data = self._found[row]
        title = self._book_titles.get(book_id, str(book_id))
        dlg = BookDetailDialog(self, book_id, title, data, self.config, self.db,
                               can_apply=self._apply_book_fn is not None)
        dlg.exec_()

        # If the user clicked Apply inside the detail dialog, apply + remove the row
        if dlg.result() == dlg.Accepted and self._apply_book_fn is not None:
            self._apply_book_fn(book_id)
            self._table.removeRow(row)
            self._found.pop(row)
            if not self._found:
                self.accept()


# ---------------------------------------------------------------------------
# Search worker (background thread for MU search)
# ---------------------------------------------------------------------------

class _SearchWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, query, user_agent=None, parent=None):
        QThread.__init__(self, parent)
        self.query = query
        self.user_agent = user_agent

    def run(self):
        from calibre_plugins.mangaupdates.scraper import search_mu_series
        try:
            results = search_mu_series(self.query, user_agent=self.user_agent)
            self.finished.emit(results or [])
        except Exception as e:
            self.error.emit(str(e))


# ---------------------------------------------------------------------------
# Search & Link dialog
# ---------------------------------------------------------------------------

class SearchLinkDialog(QDialog):
    '''
    Search MangaUpdates and link a series to each selected book.
    Processes books one at a time; user picks the matching series from results.
    '''

    linked = []  # list of book_ids that were linked (set after dialog closes)

    def __init__(self, parent, books_data, config, db):
        '''books_data: list of (book_id, title)'''
        QDialog.__init__(self, parent)
        self._books = list(books_data)
        self._config = config
        self._db = db
        self._current_idx = 0
        self.linked = []
        self._worker = None
        self._results = []

        self.setWindowTitle('Link to MangaUpdates')
        self.setMinimumSize(750, 500)

        layout = QVBoxLayout(self)
        self.setLayout(layout)

        # Book label
        self._book_label = QLabel(self)
        self._book_label.setWordWrap(True)
        layout.addWidget(self._book_label)

        # Search row
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel('Search:', self))
        self._search_edit = QLineEdit(self)
        self._search_edit.returnPressed.connect(self._do_search)
        search_layout.addWidget(self._search_edit)
        self._search_btn = QPushButton('Search', self)
        self._search_btn.clicked.connect(self._do_search)
        search_layout.addWidget(self._search_btn)
        layout.addLayout(search_layout)

        # Results table
        self._table = QTableWidget(0, 4, self)
        self._table.setHorizontalHeaderLabels(['Title', 'Genre', 'Year', 'Rating'])
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        self._table.setWordWrap(True)
        self._table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._table.itemSelectionChanged.connect(self._on_selection)
        layout.addWidget(self._table)

        # Status
        self._status = QLabel('', self)
        self._status.setStyleSheet('color: #555;')
        layout.addWidget(self._status)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        if len(self._books) > 1:
            self._skip_btn = QPushButton('Skip', self)
            self._skip_btn.clicked.connect(self._skip)
            btn_layout.addWidget(self._skip_btn)
        self._link_btn = QPushButton('Link', self)
        self._link_btn.setEnabled(False)
        self._link_btn.clicked.connect(self._link)
        btn_layout.addWidget(self._link_btn)
        close_btn = QPushButton('Close', self)
        close_btn.clicked.connect(self.reject)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        self._load_book(0)

    def _load_book(self, idx):
        if idx >= len(self._books):
            self.accept()
            return
        self._current_idx = idx
        book_id, title = self._books[idx]
        if len(self._books) > 1:
            self._book_label.setText(
                '<b>Book %d of %d:</b> %s' % (idx + 1, len(self._books), title))
        else:
            self._book_label.setText('<b>%s</b>' % title)
        self._search_edit.setText(title)
        self._table.setRowCount(0)
        self._results = []
        self._link_btn.setEnabled(False)
        self._status.setText('')
        # Auto-search on load
        self._do_search()

    def _do_search(self):
        query = self._search_edit.text().strip()
        if not query:
            return
        self._status.setText('Searching\u2026')
        self._search_btn.setEnabled(False)
        self._link_btn.setEnabled(False)
        self._table.setRowCount(0)

        # Clean up previous worker
        if self._worker is not None:
            try:
                self._worker.finished.disconnect()
                self._worker.error.disconnect()
            except Exception:
                pass

        from calibre_plugins.mangaupdates.config import KEY_USER_AGENT
        ua = self._config.get(KEY_USER_AGENT, '').strip() or None
        self._worker = _SearchWorker(query, user_agent=ua, parent=self)
        self._worker.finished.connect(self._on_results)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_results(self, results):
        self._search_btn.setEnabled(True)
        self._results = results
        self._table.setRowCount(len(results))
        for row, r in enumerate(results):
            self._table.setItem(row, 0, QTableWidgetItem(r.get('title', '')))
            self._table.setItem(row, 1, QTableWidgetItem(r.get('genres', '')))
            self._table.setItem(row, 2, QTableWidgetItem(r.get('year', '')))
            self._table.setItem(row, 3, QTableWidgetItem(r.get('rating', '')))
        self._status.setText('%d series found.' % len(results) if results
                             else 'No series found.')

    def _on_error(self, msg):
        self._search_btn.setEnabled(True)
        self._status.setText('Error: ' + msg)

    def _on_selection(self):
        rows = self._table.selectionModel().selectedRows()
        self._link_btn.setEnabled(bool(rows))

    def _selected_result(self):
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        return self._results[rows[0].row()]

    def _link(self):
        result = self._selected_result()
        if not result:
            return
        book_id = self._books[self._current_idx][0]
        self._write_link(book_id, result['url'])
        self.linked.append(book_id)
        self._load_book(self._current_idx + 1)

    def _skip(self):
        self._load_book(self._current_idx + 1)

    def _write_link(self, book_id, mu_url):
        db = self._db
        db_api = db.new_api if hasattr(db, 'new_api') else db

        # Cache as identifier for fast-path lookups
        try:
            db.set_identifier(book_id, 'mangaupdates', mu_url, index_is_id=True)
        except Exception:
            pass

        from calibre_plugins.mangaupdates.config import KEY_LINK_COL
        link_col = self._config.get(KEY_LINK_COL, '#links').strip()
        if not link_col:
            return

        md_link = '[MangaUpdates](%s)' % mu_url
        try:
            existing = db_api.field_for(link_col, book_id)
            if existing:
                if isinstance(existing, (list, tuple)):
                    existing = ', '.join(str(v) for v in existing)
                existing = str(existing)
                # Replace existing MU link if present, otherwise append
                mu_link_re = re.compile(
                    r'\[MangaUpdates\]\([^)]*mangaupdates\.com[^)]*\)', re.IGNORECASE)
                if mu_link_re.search(existing):
                    new_val = mu_link_re.sub(md_link, existing)
                else:
                    new_val = existing + ', \n' + md_link
            else:
                new_val = md_link
            db_api.set_field(link_col, {book_id: new_val})
        except Exception as e:
            print('MangaUpdates: failed to write link to %s: %s' % (link_col, e))


# ---------------------------------------------------------------------------
# Metadata fetch worker (single series page)
# ---------------------------------------------------------------------------

class _MetadataFetchWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, url, user_agent=None, parent=None):
        QThread.__init__(self, parent)
        self.url = url
        self.user_agent = user_agent

    def run(self):
        from calibre_plugins.mangaupdates.scraper import fetch_mu_metadata
        try:
            data = fetch_mu_metadata(self.url, user_agent=self.user_agent)
            if data:
                data['_url'] = self.url
                self.finished.emit(data)
            else:
                self.finished.emit({'_failed': True})
        except Exception:
            self.finished.emit({'_failed': True})


# ---------------------------------------------------------------------------
# Add from MangaUpdates dialog
# ---------------------------------------------------------------------------

class SeriesPreviewDialog(QDialog):
    '''
    Preview metadata from a MangaUpdates series page with per-field
    checkboxes.  All fields default to checked.  On accept the chosen
    fields are written into data['_apply_fields'] so _apply_one respects them.
    '''

    def __init__(self, parent, data, config):
        QDialog.__init__(self, parent)
        self.setWindowTitle('Preview: ' + (data.get('title') or ''))
        self.setMinimumSize(700, 550)
        self._data = data
        self._cover_worker = None
        self._checkboxes = {}  # field_name -> QCheckBox

        from calibre_plugins.mangaupdates.config import (
            KEY_GENRES_COL, KEY_CATEGORIES_COL, KEY_ARTISTS_COL,
            KEY_ARTISTS_TO_AUTHORS, KEY_ORIG_LANG_COL)
        from calibre_plugins.mangaupdates.action import _mu_type_to_language
        from calibre.utils.localization import calibre_langcode_to_name

        layout = QVBoxLayout(self)
        self.setLayout(layout)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        container = QWidget()
        body = QVBoxLayout(container)
        body.setSpacing(6)

        # --- Cover + title header ---
        header = QHBoxLayout()
        header.setSpacing(12)

        self._cover_img = _cover_label('Loading\u2026' if data.get('cover_url') else '(no cover)')
        header.addWidget(self._cover_img, 0, Qt.AlignmentFlag.AlignTop)

        # Right: title, type/year/status, also-known-as, cover checkbox
        title_info = QVBoxLayout()
        title_info.setSpacing(2)
        title_info.addWidget(QLabel('<h3>%s</h3>' % (data.get('title') or '')))
        info_parts = []
        if data.get('type'):
            info_parts.append('<b>Type:</b> ' + data['type'])
        if data.get('year'):
            info_parts.append('<b>Year:</b> ' + data['year'])
        if data.get('status'):
            info_parts.append('<b>Status:</b> ' + data['status'])
        if info_parts:
            lbl = QLabel('  |  '.join(info_parts))
            lbl.setWordWrap(True)
            title_info.addWidget(lbl)
        if data.get('assoc_names'):
            lbl = QLabel('<i>Also known as: ' + ', '.join(data['assoc_names']) + '</i>')
            lbl.setWordWrap(True)
            lbl.setStyleSheet('color: #666;')
            title_info.addWidget(lbl)
        if data.get('cover_url'):
            cb = QCheckBox('Include Cover', container)
            cb.setChecked(True)
            cb.setStyleSheet('font-weight: bold;')
            self._checkboxes['cover'] = cb
            title_info.addWidget(cb)
        title_info.addStretch()
        header.addLayout(title_info, 1)
        body.addLayout(header)

        body.addSpacing(4)

        # --- Per-field sections: checkbox label above, value below ---
        def _add_field(field_name, label, value, default_on=True):
            if not value:
                return
            cb = QCheckBox(label, container)
            cb.setChecked(default_on)
            cb.setStyleSheet('font-weight: bold;')
            self._checkboxes[field_name] = cb
            body.addWidget(cb)
            val_w = QPlainTextEdit(value)
            val_w.setReadOnly(True)
            line_h = val_w.fontMetrics().lineSpacing()
            lines = value.count('\n') + max(1, len(value) // 60)
            val_w.setFixedHeight(min(lines, 4) * line_h + 12)
            val_w.setStyleSheet('background: #fafafa; border: 1px solid #ddd;')
            body.addWidget(val_w)

        _add_field('authors', 'Authors',
                   ', '.join(data.get('authors') or []))

        artists_to_authors = config.get(KEY_ARTISTS_TO_AUTHORS, True)
        artists_col = config.get(KEY_ARTISTS_COL, '').strip()
        if data.get('artists') and (artists_to_authors or artists_col):
            dest = '\u2192 authors' if artists_to_authors else ('\u2192 ' + artists_col)
            _add_field('artists', 'Artists (%s)' % dest,
                       ', '.join(data['artists']))

        lang_code = _mu_type_to_language(data.get('type') or '')
        if lang_code:
            lang_display = calibre_langcode_to_name(lang_code)
            _add_field('orig_lang', 'Orig. Language', lang_display)

        _add_field('genres', 'Genres',
                   ', '.join(data.get('genres') or []))
        _add_field('categories', 'Categories',
                   ', '.join(data.get('categories') or []))

        # Assoc. Names — pick one from a combo box, like the detail dialog
        from calibre_plugins.mangaupdates.config import KEY_ASSOC_NAMES_COL
        assoc_col = config.get(KEY_ASSOC_NAMES_COL, '').strip()
        assoc_names_list = data.get('assoc_names') or []
        if assoc_names_list and assoc_col:
            cb = QCheckBox('Assoc. Name \u2192 %s' % assoc_col, container)
            cb.setChecked(True)
            cb.setStyleSheet('font-weight: bold;')
            self._checkboxes['assoc_names'] = cb
            body.addWidget(cb)
            self._assoc_combo = QComboBox(container)
            for name in assoc_names_list:
                self._assoc_combo.addItem(name)
            body.addWidget(self._assoc_combo)
        else:
            self._assoc_combo = None

        desc_html = data.get('description') or ''
        if desc_html:
            desc_text = _strip_html(desc_html)
            cb = QCheckBox('Description', container)
            cb.setChecked(True)
            cb.setStyleSheet('font-weight: bold;')
            self._checkboxes['description'] = cb
            body.addWidget(cb)
            desc_edit = QPlainTextEdit(desc_text)
            desc_edit.setReadOnly(True)
            desc_edit.setMinimumHeight(120)
            desc_edit.setStyleSheet('background: #fafafa; border: 1px solid #ddd;')
            body.addWidget(desc_edit, 1)

        body.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

        # Buttons
        buttons = QDialogButtonBox(self)
        buttons.addButton('Add to Library', QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton('Close', QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Fetch cover
        if data.get('cover_url'):
            self._cover_worker = _CoverFetchWorker(data['cover_url'], self)
            self._cover_worker.cover_fetched.connect(self._on_cover)
            self._cover_worker.start()

    def _on_cover(self, img_data):
        pm = _pixmap_from_bytes(img_data)
        if pm:
            self._cover_img.setPixmap(_scale_pixmap(pm))
            self._cover_img.setText('')
        else:
            self._cover_img.setText('(failed)')

    def _on_accept(self):
        # Write checkbox state into data so _apply_one reads it
        fields = {}
        for fname, cb in self._checkboxes.items():
            fields[fname] = cb.isChecked()
        if self._assoc_combo is not None:
            fields['assoc_names_value'] = self._assoc_combo.currentText()
        self._data['_apply_fields'] = fields
        self.accept()


class AddFromMUDialog(QDialog):
    '''
    Search MangaUpdates, preview a series, and create a new empty book
    with full metadata from the series page.
    Double-click a result to preview before adding.
    '''

    added = []  # book_ids of created books

    def __init__(self, parent, config, db, apply_fn=None):
        QDialog.__init__(self, parent)
        self._config = config
        self._db = db
        self._apply_fn = apply_fn
        self.added = []
        self._search_worker = None
        self._fetch_worker = None
        self._results = []

        self.setWindowTitle('Add from MangaUpdates')
        self.setMinimumSize(750, 500)

        layout = QVBoxLayout(self)
        self.setLayout(layout)

        hint = QLabel('Double-click a result to preview, then add to library.', self)
        hint.setStyleSheet('color: #555; font-style: italic;')
        layout.addWidget(hint)

        # Search row
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel('Search:', self))
        self._search_edit = QLineEdit(self)
        self._search_edit.returnPressed.connect(self._do_search)
        search_layout.addWidget(self._search_edit)
        self._search_btn = QPushButton('Search', self)
        self._search_btn.clicked.connect(self._do_search)
        search_layout.addWidget(self._search_btn)
        layout.addLayout(search_layout)

        # Results table
        self._table = QTableWidget(0, 4, self)
        self._table.setHorizontalHeaderLabels(['Title', 'Genre', 'Year', 'Rating'])
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        self._table.setWordWrap(True)
        self._table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._table.cellDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self._table)

        # Status
        self._status = QLabel('', self)
        self._status.setStyleSheet('color: #555;')
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton('Close', self)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        self._search_edit.setFocus()

    def _do_search(self):
        query = self._search_edit.text().strip()
        if not query:
            return
        self._status.setText('Searching\u2026')
        self._search_btn.setEnabled(False)
        self._table.setRowCount(0)

        if self._search_worker is not None:
            try:
                self._search_worker.finished.disconnect()
                self._search_worker.error.disconnect()
            except Exception:
                pass

        from calibre_plugins.mangaupdates.config import KEY_USER_AGENT
        ua = self._config.get(KEY_USER_AGENT, '').strip() or None
        self._search_worker = _SearchWorker(query, user_agent=ua, parent=self)
        self._search_worker.finished.connect(self._on_results)
        self._search_worker.error.connect(self._on_search_error)
        self._search_worker.start()

    def _on_results(self, results):
        self._search_btn.setEnabled(True)
        self._results = results
        self._table.setRowCount(len(results))
        for row, r in enumerate(results):
            self._table.setItem(row, 0, QTableWidgetItem(r.get('title', '')))
            self._table.setItem(row, 1, QTableWidgetItem(r.get('genres', '')))
            self._table.setItem(row, 2, QTableWidgetItem(r.get('year', '')))
            self._table.setItem(row, 3, QTableWidgetItem(r.get('rating', '')))
        self._status.setText('%d series found.' % len(results) if results
                             else 'No series found.')

    def _on_search_error(self, msg):
        self._search_btn.setEnabled(True)
        self._status.setText('Error: ' + msg)

    def _on_double_click(self, row, _col):
        if row < 0 or row >= len(self._results):
            return
        result = self._results[row]
        self._status.setText('Fetching metadata\u2026')
        self._search_btn.setEnabled(False)

        if self._fetch_worker is not None:
            try:
                self._fetch_worker.finished.disconnect()
            except Exception:
                pass

        from calibre_plugins.mangaupdates.config import KEY_USER_AGENT
        ua = self._config.get(KEY_USER_AGENT, '').strip() or None
        self._fetch_worker = _MetadataFetchWorker(result['url'],
                                                   user_agent=ua, parent=self)
        self._fetch_worker.finished.connect(self._on_metadata)
        self._fetch_worker.start()

    def _on_metadata(self, data):
        self._search_btn.setEnabled(True)

        if data.get('_failed'):
            self._status.setText('Failed to fetch metadata.')
            return

        self._status.setText('')

        # Show preview dialog — user decides whether to add and which fields
        preview = SeriesPreviewDialog(self, data, self._config)
        if preview.exec_() != preview.Accepted:
            return

        self._create_book(data)

    def _create_book(self, data):
        mu_url = data.get('_url', '')
        title = data.get('title') or 'Unknown'
        authors = data.get('authors') or ['Unknown']

        from calibre.ebooks.metadata.book.base import Metadata
        mi = Metadata(title, authors)
        db = self._db

        try:
            book_id = db.import_book(mi, [])
        except Exception as e:
            self._status.setText('Failed to create book: %s' % e)
            return

        # _apply_fields was set by SeriesPreviewDialog checkboxes;
        # pass config with all booleans on so only _apply_fields controls what's written
        if self._apply_fn:
            from calibre_plugins.mangaupdates.config import DEFAULT_STORE_VALUES
            add_config = dict(self._config)
            add_config.update({k: True for k, v in DEFAULT_STORE_VALUES.items()
                               if isinstance(v, bool)})
            for k in DEFAULT_STORE_VALUES:
                if k.lower().endswith('append'):
                    add_config[k] = False
            self._apply_fn(book_id, mu_url, data, db, add_config)

        # Write the markdown link
        from calibre_plugins.mangaupdates.config import KEY_LINK_COL
        link_col = self._config.get(KEY_LINK_COL, '#links').strip()
        if link_col:
            md_link = '[MangaUpdates](%s)' % mu_url
            try:
                db_api = db.new_api if hasattr(db, 'new_api') else db
                db_api.set_field(link_col, {book_id: md_link})
            except Exception:
                pass

        # Set the mangaupdates identifier
        try:
            db.set_identifier(book_id, 'mangaupdates', mu_url, index_is_id=True)
        except Exception:
            pass

        self.added.append(book_id)
        self._status.setText('Added: %s' % title)
