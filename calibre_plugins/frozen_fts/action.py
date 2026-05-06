from __future__ import unicode_literals, division, absolute_import, print_function

__license__ = 'GPL v3'

import weakref

try:
    from qt.core import QMenu, QToolButton
except ImportError:
    from PyQt5.Qt import QMenu, QToolButton

from calibre.gui2 import question_dialog, info_dialog
from calibre.gui2.actions import InterfaceAction


class FrozenFtsAction(InterfaceAction):
    name = 'Frozen FTS'
    action_spec = (_('Frozen FTS'), 'fts.png',
                   _('Search the existing FTS index without enabling live indexing'),
                   None)
    action_type = 'current'
    popup_type = QToolButton.MenuButtonPopup
    dont_add_to = frozenset(('context-menu-device',))

    def genesis(self):
        # Default click → open the search dialog (the main use case).
        self.qaction.triggered.connect(self.show_frozen_fts)
        self._dialog = None
        self._injected = False

        self.menu = QMenu(self.gui)
        self.qaction.setMenu(self.menu)

        a = self.menu.addAction(_('Search frozen full text'))
        a.triggered.connect(self.show_frozen_fts)

        self.menu.addSeparator()
        # Testing / dev helpers — let us A/B between this plugin's behavior and
        # Calibre's stock FTS UI without paying the bulk re-check storm.
        a = self.menu.addAction(_('Enable FTS indexing (skip bulk re-check)'))
        a.triggered.connect(self.enable_fts_skip_recheck)

        a = self.menu.addAction(_('Disable FTS indexing'))
        a.triggered.connect(self.disable_fts)

        a = self.menu.addAction(_('Show FTS status'))
        a.triggered.connect(self.show_status)

    # -- Search (frozen mode) -------------------------------------------------

    def show_frozen_fts(self):
        from calibre_plugins.frozen_fts.dialog import FrozenFtsDialog

        db = self.gui.current_db
        self._ensure_fts_engine(db)

        if self._dialog is None:
            self._dialog = FrozenFtsDialog(self.gui)
            self._dialog.finished.connect(self._on_dialog_finished)
        text = self.gui.search.text()
        if text and ':' not in text:
            self._dialog.set_search_text(text)
        self._dialog.show()
        self._dialog.raise_and_focus()

    def _ensure_fts_engine(self, db):
        # See notes.md: instantiate FTS without flipping prefs and without
        # calling dirty_existing(), so the dialog can search the existing
        # index. No worker pool is started.
        backend = db.new_api.backend
        if backend.prefs['fts_enabled']:
            self._injected = False
            return
        if backend.fts is None:
            from calibre.db.fts.connect import FTS
            backend.fts = FTS(weakref.ref(db.new_api))
            self._injected = True

    def _on_dialog_finished(self, _result):
        # Sweep accumulated dirtied_formats rows. See notes.md for why these
        # are harmless but still worth clearing.
        if not self._injected:
            return
        try:
            db = self.gui.current_db
            fts = db.new_api.backend.fts
            if fts is not None:
                fts.clear_all_dirty()
        except Exception:
            import traceback
            traceback.print_exc()

    def library_changed(self, db):
        if self._dialog is not None:
            self._dialog.close()
            self._dialog = None
        self._injected = False

    # -- Testing actions ------------------------------------------------------

    def enable_fts_skip_recheck(self):
        """Enable real FTS indexing WITHOUT calling dirty_existing().

        Mimics Cache.enable_fts() minus the bulk-mark step. The existing
        indexed content is trusted as-is. Going forward, normal Calibre
        machinery (SQL triggers + worker pool) processes new edits/adds.

        Side effects:
        - prefs['fts_enabled'] is set True (persists across restarts).
        - backend.fts is constructed.
        - FTS worker pool is started.
        - The 20k existing books are NOT re-hashed.
        """
        db = self.gui.current_db
        backend = db.new_api.backend
        if backend.prefs['fts_enabled']:
            info_dialog(self.gui, _('Already enabled'),
                _('FTS indexing is already enabled on this library.'),
                show=True)
            return
        msg = _(
            'This will enable Calibre\'s real FTS indexing on this library, '
            'but skip the bulk re-check that normally marks every book as '
            'dirty. The existing index will be trusted as-is.\n\n'
            'Going forward, Calibre will index new books and re-index books '
            'whose format files change (including metadata-embed rewrites). '
            'Books edited outside Calibre between the last full index and '
            'now will NOT be re-indexed automatically.\n\n'
            'Continue?')
        if not question_dialog(self.gui, _('Enable FTS without re-check?'), msg):
            return

        # Replicate Cache.enable_fts() minus dirty_existing():
        backend.prefs['fts_enabled'] = True
        backend.initialize_fts(weakref.ref(db.new_api))
        db.new_api.start_fts_pool()
        # Mark our flag false: from now on we are NOT in frozen mode for this
        # library, and clear-on-close should NOT run.
        self._injected = False

        info_dialog(self.gui, _('FTS enabled'),
            _('FTS indexing is now enabled. Existing index trusted as-is. '
              'Use Calibre\'s normal "Search full text" action to query.'),
            show=True)

    def disable_fts(self):
        db = self.gui.current_db
        backend = db.new_api.backend
        if not backend.prefs['fts_enabled']:
            info_dialog(self.gui, _('Already disabled'),
                _('FTS indexing is already disabled on this library.'),
                show=True)
            return
        msg = _(
            'This will disable FTS indexing. The existing index file is left '
            'on disk, so you can re-enable later (use this plugin\'s '
            '"Enable FTS (skip bulk re-check)" to avoid the re-hash storm).\n\n'
            'Continue?')
        if not question_dialog(self.gui, _('Disable FTS?'), msg):
            return
        # Calibre's stock disable path — sets prefs False, nulls backend.fts,
        # shuts down the queue thread. No storm on disable.
        db.new_api.enable_fts(enabled=False)
        info_dialog(self.gui, _('FTS disabled'),
            _('FTS indexing is now disabled.'), show=True)

    def show_status(self):
        db = self.gui.current_db
        backend = db.new_api.backend
        prefs_flag = bool(backend.prefs['fts_enabled'])
        fts_obj_present = backend.fts is not None
        dirty = indexed = total = None
        try:
            if fts_obj_present:
                conn = backend.fts.get_connection()
                dirty = conn.get('SELECT COUNT(*) FROM fts_db.dirtied_formats')[0][0]
                indexed = conn.get('SELECT COUNT(*) FROM fts_db.books_text')[0][0]
            total = backend.get('SELECT COUNT(*) FROM main.data')[0][0]
        except Exception as e:
            import traceback
            traceback.print_exc()
            info_dialog(self.gui, _('FTS status'),
                _('Error reading status: {}').format(e), show=True)
            return

        lines = [
            _('prefs[fts_enabled]: {}').format(prefs_flag),
            _('backend.fts is set: {}').format(fts_obj_present),
            _('Format rows in main.data: {}').format(total),
            _('Rows in books_text (indexed): {}').format(indexed),
            _('Rows in dirtied_formats (queued): {}').format(dirty),
            _('Plugin injected FTS this session: {}').format(self._injected),
        ]
        info_dialog(self.gui, _('FTS status'), '\n'.join(lines), show=True)
