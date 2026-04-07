from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'

import re

try:
    from qt.core import QModelIndex, QMenu, QToolButton
except ImportError:
    from PyQt5.Qt import QModelIndex, QMenu, QToolButton

from calibre.gui2 import error_dialog, info_dialog
from calibre.gui2.actions import InterfaceAction

import calibre_plugins.manga_updates.config as cfg
from calibre_plugins.manga_updates.common_icons import set_plugin_icon_resources, get_icon
from calibre_plugins.manga_updates.common_menus import create_menu_action_unique
from calibre_plugins.manga_updates.dialogs import (DownloadProgressDialog, ApplyMetadataDialog,
                                                   BookDetailDialog, SearchLinkDialog,
                                                   AddFromMUDialog)

PLUGIN_ICONS = ['images/mangaupdates.png']

# Matches mangaupdates.com series URLs (new /series/<slug> and old /series.html?id=<num>)
MU_URL_RE = re.compile(r'https?://(?:www\.)?mangaupdates\.com/series(?:\.html\?id=\d+|/[^\s"\'<>\]]+)')


def find_mu_url(book_id, db, config):
    '''
    Discover a MangaUpdates URL for a book by scanning configured fields.
    Returns the URL string or None.
    '''
    identifiers = db.get_identifiers(book_id, index_is_id=True)

    # Fast path: already cached as 'mangaupdates' identifier
    mu_cached = identifiers.get('mangaupdates', '')
    if mu_cached:
        url = mu_cached if mu_cached.startswith('http') else ('https://www.mangaupdates.com/series/' + mu_cached)
        return url.rstrip('/')

    # Scan url/uri identifiers
    if config.get(cfg.KEY_SCAN_IDENTIFIERS, True):
        for key in ('url', 'uri'):
            val = identifiers.get(key, '')
            if val:
                m = MU_URL_RE.search(val)
                if m:
                    return m.group(0).rstrip('/')

    # Scan comments
    if config.get(cfg.KEY_SCAN_COMMENTS, True):
        comments = db.comments(book_id, index_is_id=True) or ''
        m = MU_URL_RE.search(comments)
        if m:
            return m.group(0).rstrip('/')

    # Scan custom column
    if config.get(cfg.KEY_SCAN_CUSTOM_COL, True):
        col_name = config.get(cfg.KEY_CUSTOM_COL_NAME, '#links')
        if col_name:
            try:
                if hasattr(db, 'new_api'):
                    val = db.new_api.field_for(col_name, book_id)
                else:
                    val = db.get_custom(book_id, label=col_name.lstrip('#'), index_is_id=True)
                if val:
                    m = MU_URL_RE.search(str(val))
                    if m:
                        return m.group(0).rstrip('/')
            except Exception:
                pass

    return None


def get_search_title(book_id, db, config):
    '''
    Return the best title string for search, checking columns listed in
    the KEY_SEARCH_TITLE_COLS config value (comma-separated, tried in order).
    Falls back to the Calibre title or the book_id.
    '''
    cols_str = config.get(cfg.KEY_SEARCH_TITLE_COLS, 'title')
    for col_name in cols_str.split(','):
        col_name = col_name.strip()
        if not col_name:
            continue
        try:
            if col_name == 'title':
                val = db.title(book_id, index_is_id=True)
            elif col_name.startswith('#'):
                if hasattr(db, 'new_api'):
                    val = db.new_api.field_for(col_name, book_id)
                else:
                    val = db.get_custom(book_id, label=col_name.lstrip('#'), index_is_id=True)
            else:
                if hasattr(db, 'new_api'):
                    val = db.new_api.field_for(col_name, book_id)
                else:
                    val = None
            if val and str(val).strip():
                return str(val).strip()
        except Exception:
            continue
    return db.title(book_id, index_is_id=True) or str(book_id)


class MangaUpdatesAction(InterfaceAction):

    name = 'MangaUpdates'
    action_spec = ('MangaUpdates', None, 'Download metadata from mangaupdates.com', ())
    action_type = 'current'
    popup_type = QToolButton.MenuButtonPopup

    def genesis(self):
        icon_resources = self.load_resources(PLUGIN_ICONS)
        set_plugin_icon_resources(self.name, icon_resources)
        self.qaction.setIcon(get_icon(PLUGIN_ICONS[0]))
        self.qaction.triggered.connect(self.download_metadata)

        self.menu = QMenu(self.gui)
        self.qaction.setMenu(self.menu)

        create_menu_action_unique(self, self.menu, 'Download MangaUpdates Metadata',
                                  PLUGIN_ICONS[0], triggered=self.download_metadata)
        create_menu_action_unique(self, self.menu, 'Link to MangaUpdates\u2026',
                                  PLUGIN_ICONS[0], triggered=self.link_to_mu)
        create_menu_action_unique(self, self.menu, 'Add from MangaUpdates\u2026',
                                  PLUGIN_ICONS[0], triggered=self.add_from_mu)
        self.menu.addSeparator()
        create_menu_action_unique(self, self.menu, 'Customize plugin\u2026',
                                  'config.png', shortcut=False,
                                  triggered=self.show_configuration)
        self.gui.keyboard.finalize()

    def show_configuration(self):
        self.interface_action_base_plugin.do_user_config(self.gui)

    def link_to_mu(self):
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows:
            return error_dialog(self.gui, 'MangaUpdates',
                'Select one or more books first.', show=True)

        book_ids = list(self.gui.library_view.get_selected_ids())
        db = self.gui.current_db
        config = cfg.plugin_prefs[cfg.STORE_NAME]

        books_data = []
        for book_id in book_ids:
            title = get_search_title(book_id, db, config)
            books_data.append((book_id, title))

        dlg = SearchLinkDialog(self.gui, books_data, config, db)
        dlg.exec_()

        if dlg.linked:
            self.gui.library_view.model().refresh_ids(dlg.linked)
            current = self.gui.library_view.currentIndex()
            if current.isValid():
                self.gui.library_view.model().current_changed(current, QModelIndex())
            info_dialog(self.gui, 'MangaUpdates',
                'Linked %d book(s) to MangaUpdates.' % len(dlg.linked),
                show=True)

    def add_from_mu(self):
        db = self.gui.current_db
        config = cfg.plugin_prefs[cfg.STORE_NAME]

        dlg = AddFromMUDialog(self.gui, config, db, apply_fn=self._apply_one)
        dlg.exec_()

        if dlg.added:
            self.gui.library_view.model().books_added(len(dlg.added))
            self.gui.library_view.model().refresh_ids(dlg.added)
            self.gui.tags_view.recount()
            info_dialog(self.gui, 'MangaUpdates',
                'Added %d book(s) from MangaUpdates.' % len(dlg.added),
                show=True)

    def download_metadata(self):
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows:
            return error_dialog(self.gui, 'MangaUpdates',
                'Select one or more books first.', show=True)

        book_ids = list(self.gui.library_view.get_selected_ids())
        db = self.gui.current_db
        config = cfg.plugin_prefs[cfg.STORE_NAME]

        # Discover MU URLs for each selected book
        books_data = []   # (book_id, title, mu_url_or_None)
        for book_id in book_ids:
            title = get_search_title(book_id, db, config)
            mu_url = find_mu_url(book_id, db, config)
            books_data.append((book_id, title, mu_url))

        # For books with no MU URL, offer to link them first
        missing = [(bid, title) for bid, title, url in books_data if not url]
        if missing:
            dlg = SearchLinkDialog(self.gui, missing, config, db)
            dlg.exec_()

            if dlg.linked:
                self.gui.library_view.model().refresh_ids(dlg.linked)

            # Re-discover URLs after linking
            books_data = []
            for book_id in book_ids:
                title = get_search_title(book_id, db, config)
                mu_url = find_mu_url(book_id, db, config)
                books_data.append((book_id, title, mu_url))

        found_count = sum(1 for _, _, url in books_data if url)
        if found_count == 0:
            return

        # Fetch metadata in background
        dlg = DownloadProgressDialog(self.gui, books_data, config, db)
        if dlg.exec_() != dlg.Accepted:
            return

        results = dlg.results
        if all(r.get('_failed') for r in results.values()):
            log_lines = []
            for book_id, title, _ in books_data:
                r = results.get(book_id, {})
                for line in r.get('_log', []):
                    log_lines.append('[%s] %s' % (title, line))
            return error_dialog(self.gui, 'MangaUpdates',
                'No metadata could be downloaded.',
                det_msg='\n'.join(log_lines),
                show=True)

        # Show preview and confirm
        _mu_url_map = {bid: url for bid, _, url in books_data}
        def _apply_book_fn(book_id):
            self._apply_one(book_id, _mu_url_map.get(book_id), results[book_id], db, config)

        # Single book shortcut: skip the list and open the detail dialog directly
        if len(books_data) == 1:
            book_id, book_title, _mu_url = books_data[0]
            data = results.get(book_id)
            if data and not data.get('_failed'):
                dlg = BookDetailDialog(self.gui, book_id, book_title, data,
                                       config, db, can_apply=True)
                dlg.exec_()
                if dlg.result() == dlg.Accepted:
                    _apply_book_fn(book_id)
                    self._apply_metadata(results, books_data, db, config)
                return

        apply_dlg = ApplyMetadataDialog(self.gui, results, books_data, config, db,
                                        apply_book_fn=_apply_book_fn)
        if apply_dlg.exec_() != apply_dlg.Accepted:
            return

        self._apply_metadata(results, books_data, db, config)

    def _apply_one(self, book_id, mu_url, data, db, config):
        '''Write metadata + cover for a single book. Sets data[_already_applied]=True.'''
        db_api = db.new_api if hasattr(db, 'new_api') else db
        overrides = data.get('_apply_fields')

        def _apply(config_key, default, field_name):
            if overrides is not None:
                return overrides.get(field_name, False)
            return config.get(config_key, default)

        # Cache the MU URL as an identifier for future fast-path lookups
        fetched_url = data.get('_url') or mu_url
        if fetched_url:
            try:
                db.set_identifier(book_id, 'mangaupdates', fetched_url, index_is_id=True)
            except Exception:
                pass

        fields_to_set = {}

        # Title
        if _apply(cfg.KEY_UPDATE_TITLE, False, 'title') and data.get('title'):
            fields_to_set['title'] = data['title']

        # Authors
        if _apply(cfg.KEY_UPDATE_AUTHORS, True, 'authors') and data.get('authors'):
            author_list = list(data['authors'])

            # Merge artists into authors if configured
            if config.get(cfg.KEY_ARTISTS_TO_AUTHORS, True) and data.get('artists'):
                for a in data['artists']:
                    if a not in author_list:
                        author_list.append(a)

            if overrides is not None:
                auth_append = overrides.get('authors_append', config.get(cfg.KEY_AUTHORS_APPEND, False))
            else:
                auth_append = config.get(cfg.KEY_AUTHORS_APPEND, False)
            if auth_append:
                existing = list(db_api.field_for('authors', book_id) or [])
                merged = existing + [a for a in author_list if a not in existing]
                fields_to_set['authors'] = merged
            else:
                fields_to_set['authors'] = author_list

        # Comments / Description
        if _apply(cfg.KEY_UPDATE_DESCRIPTION, True, 'description') and data.get('description'):
            if overrides is not None:
                desc_append = overrides.get('description_append', config.get(cfg.KEY_DESCRIPTION_APPEND, False))
            else:
                desc_append = config.get(cfg.KEY_DESCRIPTION_APPEND, False)
            if desc_append:
                existing = db.comments(book_id, index_is_id=True) or ''
                fields_to_set['comments'] = existing + data['description']
            else:
                fields_to_set['comments'] = data['description']

        # Apply standard fields
        if fields_to_set:
            try:
                db_api.set_metadata(book_id, _dict_to_partial_metadata(fields_to_set),
                                    set_title=('title' in fields_to_set),
                                    set_authors=('authors' in fields_to_set))
            except Exception:
                for field, value in fields_to_set.items():
                    try:
                        db_api.set_field(field, {book_id: value})
                    except Exception:
                        pass

        # Original Language (inferred from type) — to custom column or Calibre languages
        if _apply(cfg.KEY_UPDATE_ORIG_LANG, True, 'orig_lang') and data.get('type'):
            lang_code = _mu_type_to_language(data['type'])
            if lang_code:
                orig_lang_col = config.get(cfg.KEY_ORIG_LANG_COL, '').strip()
                if orig_lang_col:
                    value = _resolve_lang_for_column(db, orig_lang_col, lang_code)
                    if value:
                        try:
                            db_api.set_field(orig_lang_col, {book_id: value})
                        except Exception as e:
                            print('MangaUpdates: failed to set %s: %s' % (orig_lang_col, e))
                else:
                    try:
                        db_api.set_field('languages', {book_id: [lang_code]})
                    except Exception as e:
                        print('MangaUpdates: failed to set languages: %s' % e)

        # Genres and Categories — written to configurable columns
        genres_col     = config.get(cfg.KEY_GENRES_COL, '#extratags').strip()
        categories_col = config.get(cfg.KEY_CATEGORIES_COL, '#extratags').strip()

        if overrides is not None:
            apply_genres     = overrides.get('genres', False) and bool(genres_col)
            apply_categories = overrides.get('categories', False) and bool(categories_col)
        else:
            apply_genres     = bool(genres_col)
            apply_categories = bool(categories_col)

        if apply_genres or apply_categories:
            mu_genres     = list(dict.fromkeys(data.get('genres') or []))
            mu_categories = list(dict.fromkeys(data.get('categories') or []))

            if overrides is not None:
                genres_append     = overrides.get('genres_append', config.get(cfg.KEY_GENRES_APPEND, True))
                categories_append = overrides.get('categories_append', config.get(cfg.KEY_CATEGORIES_APPEND, True))
            else:
                genres_append     = config.get(cfg.KEY_GENRES_APPEND, True)
                categories_append = config.get(cfg.KEY_CATEGORIES_APPEND, True)

            if apply_genres and apply_categories and genres_col == categories_col:
                combined = list(dict.fromkeys(mu_genres + mu_categories))
                _write_tags(db_api, book_id, genres_col, genres_append, combined)
            else:
                if apply_genres and mu_genres:
                    _write_tags(db_api, book_id, genres_col, genres_append, mu_genres)
                if apply_categories and mu_categories:
                    _write_tags(db_api, book_id, categories_col, categories_append, mu_categories)

        # Associated Names — use override pick if available, otherwise first name
        assoc_col = config.get(cfg.KEY_ASSOC_NAMES_COL, '').strip()
        if assoc_col and _apply(cfg.KEY_UPDATE_ASSOC_NAMES, True, 'assoc_names'):
            if overrides is not None:
                selected = overrides.get('assoc_names_value', '').strip()
            else:
                names = data.get('assoc_names') or []
                selected = names[0].strip() if names else ''
            if selected:
                if overrides is not None:
                    assoc_append = overrides.get('assoc_names_append',
                                                 config.get(cfg.KEY_ASSOC_NAMES_APPEND, True))
                else:
                    assoc_append = config.get(cfg.KEY_ASSOC_NAMES_APPEND, True)
                try:
                    existing = db_api.field_for(assoc_col, book_id)
                    if isinstance(existing, (list, tuple, frozenset)):
                        ex_list = list(existing) if existing else []
                        new_val = (ex_list + [selected] if selected not in ex_list
                                   else ex_list) if assoc_append else [selected]
                        db_api.set_field(assoc_col, {book_id: new_val})
                    else:
                        if assoc_append and existing:
                            db_api.set_field(assoc_col, {book_id: existing + ', ' + selected})
                        else:
                            db_api.set_field(assoc_col, {book_id: selected})
                except Exception as e:
                    print('MangaUpdates: failed to set %s: %s' % (assoc_col, e))

        # Artists → custom column (separate from authors merge)
        artists_col = config.get(cfg.KEY_ARTISTS_COL, '').strip()
        if artists_col and data.get('artists'):
            if overrides is not None:
                apply_artists = overrides.get('artists', False)
            else:
                apply_artists = config.get(cfg.KEY_UPDATE_ARTISTS, False)
            if apply_artists:
                if overrides is not None:
                    artists_append = overrides.get('artists_append', config.get(cfg.KEY_ARTISTS_APPEND, False))
                else:
                    artists_append = config.get(cfg.KEY_ARTISTS_APPEND, False)
                _write_tags(db_api, book_id, artists_col, artists_append, data['artists'])

        # Cover
        if overrides is not None:
            apply_cover = overrides.get('cover', False)
        else:
            apply_cover = config.get(cfg.KEY_UPDATE_COVER, True)
        if apply_cover:
            cover_url = data.get('cover_url')
            if cover_url:
                self._download_one_cover(book_id, cover_url, db, db_api)

        data['_already_applied'] = True

    def _apply_metadata(self, results, books_data, db, config):
        '''Write downloaded metadata to the Calibre library for any not yet applied.'''
        newly_updated = []
        pre_applied = []

        for book_id, title, mu_url in books_data:
            data = results.get(book_id)
            if not data or data.get('_failed'):
                continue
            if data.get('_already_applied'):
                pre_applied.append(book_id)
                continue
            self._apply_one(book_id, mu_url, data, db, config)
            newly_updated.append(book_id)

        all_updated = newly_updated + pre_applied

        # Refresh UI
        if all_updated:
            self.gui.library_view.model().refresh_ids(all_updated)
            current = self.gui.library_view.currentIndex()
            if current.isValid():
                self.gui.library_view.model().current_changed(current, QModelIndex())
            self.gui.tags_view.recount()

        info_dialog(self.gui, 'MangaUpdates',
            'Updated metadata for %d book(s).' % len(all_updated),
            show=True)

    def _download_one_cover(self, book_id, cover_url, db, db_api):
        '''Download and set cover for a single book.'''
        try:
            import urllib.request as ulr
        except ImportError:
            import urllib2 as ulr

        headers = {
            'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/120.0.0.0 Safari/537.36'),
            'Referer': 'https://www.mangaupdates.com/',
        }

        try:
            req = ulr.Request(cover_url, headers=headers)
            cover_data = ulr.urlopen(req, timeout=15).read()
            if cover_data and len(cover_data) > 1024:
                try:
                    db_api.set_cover({book_id: cover_data})
                except Exception:
                    db.set_cover(book_id, cover_data, index_is_id=True)
        except Exception as e:
            print('MangaUpdates: cover download failed for book %s: %s' % (book_id, e))


# --- Helpers ---

def _write_tags(db_api, book_id, col, append, new_values):
    '''Write a list of tag-like values to a Calibre column, optionally appending.'''
    if not col or not new_values:
        return
    try:
        if append:
            existing = db_api.field_for(col, book_id) or []
            if isinstance(existing, (list, tuple)):
                existing = list(existing)
            else:
                existing = []
            new_values = existing + [t for t in new_values if t not in existing]
        db_api.set_field(col, {book_id: new_values})
    except Exception as e:
        print('MangaUpdates: failed to set %s: %s' % (col, e))

_MU_TYPE_TO_LANG = {
    'manga': 'jpn',
    'manhwa': 'kor',
    'manhua': 'zho',
    'doujinshi': 'jpn',
    'oel': 'eng',
}

def _mu_type_to_language(type_str):
    '''Infer a Calibre language code from MU series type.'''
    if not type_str:
        return None
    return _MU_TYPE_TO_LANG.get(type_str.lower().strip())

from calibre_plugins.manga_updates.common_lang import resolve_lang_for_column as _resolve_lang_for_column


def _dict_to_partial_metadata(fields):
    '''Build a minimal Metadata object from a dict of field→value pairs.'''
    from calibre.ebooks.metadata.book.base import Metadata
    authors = fields.get('authors') or ['Unknown']
    title = fields.get('title') or 'Unknown'
    mi = Metadata(title, authors)
    if 'comments' in fields:
        mi.comments = fields['comments']
    if 'languages' in fields:
        mi.languages = fields['languages']
    return mi
