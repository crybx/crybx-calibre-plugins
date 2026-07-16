from qt.core import QIcon, QMenu, QModelIndex, QPixmap, QToolButton

from calibre.ebooks.metadata import authors_to_string
from calibre.gui2 import error_dialog, info_dialog
from calibre.gui2.actions import InterfaceAction

from calibre_plugins.meta_manipulator.dialogs import MetaManipulatorDialog

ICON = 'images/metamanipulator.png'


class MetaManipulatorAction(InterfaceAction):

    name = 'MetaManipulator'
    action_spec = ('MetaManipulator', None, 'Bulk metadata manipulation', ())
    action_type = 'current'
    popup_type = QToolButton.MenuButtonPopup

    def genesis(self):
        self.icon_data = self.load_resources([ICON]).get(ICON)
        if self.icon_data:
            pm = QPixmap()
            pm.loadFromData(self.icon_data)
            self.qaction.setIcon(QIcon(pm))
        self.qaction.triggered.connect(self._show_dialog)
        self.menu = QMenu(self.gui)
        self.qaction.setMenu(self.menu)
        self._create_menu()

    def _create_menu(self):
        self.menu.clear()
        self.menu.addAction('Select operations\u2026', self._show_dialog)
        self.menu.addSeparator()
        self.menu.addAction('Save title and author to description',
            self._save_title_author_to_description)
        self.menu.addAction('Save title to #originaltitle',
            self._save_title_to_originaltitle)
        self.menu.addAction('Move contents from title',
            self._move_contents_from_title)

    def _show_dialog(self):
        book_ids = self._get_selected_ids()
        if not book_ids:
            return

        dlg = MetaManipulatorDialog(self.gui, self.icon_data)
        if dlg.exec_() != dlg.Accepted:
            return

        options = dlg.options
        db = self.gui.current_db.new_api
        count = 0

        if options.get('save_title_author_to_description'):
            count += self._do_save_title_author_to_description(db, book_ids)

        if options.get('save_title_to_originaltitle'):
            count += self._do_save_title_to_originaltitle(db, book_ids)

        if options.get('move_contents_from_title'):
            count += self._do_move_contents_from_title(db, book_ids)

        self._refresh_ui(book_ids)
        info_dialog(self.gui, 'MetaManipulator',
            'Completed %d operation(s) across %d book(s).' % (count, len(book_ids)),
            show=True)

    def _get_selected_ids(self):
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows:
            error_dialog(self.gui, 'MetaManipulator',
                'You must select one or more books.', show=True)
            return None
        return self.gui.library_view.get_selected_ids()

    def _refresh_ui(self, book_ids):
        self.gui.library_view.model().refresh_ids(list(book_ids))
        current = self.gui.library_view.currentIndex()
        if current.isValid():
            self.gui.library_view.model().current_changed(current, QModelIndex())

    def _do_save_title_author_to_description(self, db, book_ids):
        count = 0
        for book_id in book_ids:
            mi = db.get_metadata(book_id)
            title = mi.title or ''
            if not title:
                continue

            authors = authors_to_string(mi.authors) if mi.authors else ''
            header = '%s by %s' % (title, authors) if authors else title

            existing = mi.comments or ''
            new_comments = '<p>%s</p>\n%s' % (header, existing)
            db.set_field('comments', {book_id: new_comments})
            count += 1
        return count

    def _do_save_title_to_originaltitle(self, db, book_ids):
        updates = {}
        for book_id in book_ids:
            mi = db.get_metadata(book_id)
            title = mi.title or ''
            if title:
                updates[book_id] = title.replace('_', ' ')

        if updates:
            try:
                db.set_field('#originaltitle', updates)
            except Exception as e:
                error_dialog(self.gui, 'MetaManipulator',
                    'Failed to update #originaltitle: %s' % str(e), show=True)
                return 0
        return len(updates)

    @staticmethod
    def _split_trailing_parens(title):
        """Split a trailing balanced parenthesized group off the title.

        Returns (new_title, inner) where ``inner`` is the text inside the
        outermost trailing parentheses (nested parentheses preserved), or
        (title, None) when there is no balanced trailing group.
        """
        stripped = (title or '').rstrip()
        if not stripped.endswith(')'):
            return title, None

        depth = 0
        for i in range(len(stripped) - 1, -1, -1):
            ch = stripped[i]
            if ch == ')':
                depth += 1
            elif ch == '(':
                depth -= 1
                if depth == 0:
                    inner = stripped[i + 1:-1]
                    new_title = stripped[:i].rstrip()
                    if not new_title or not inner:
                        return title, None
                    return new_title, inner
        return title, None

    def _do_move_contents_from_title(self, db, book_ids):
        title_updates = {}
        contents_updates = {}
        for book_id in book_ids:
            mi = db.get_metadata(book_id)
            title = mi.title or ''
            new_title, inner = self._split_trailing_parens(title)
            if inner is None:
                continue
            title_updates[book_id] = new_title
            contents_updates[book_id] = inner

        if not contents_updates:
            return 0

        try:
            db.set_field('#contents', contents_updates)
        except Exception as e:
            error_dialog(self.gui, 'MetaManipulator',
                'Failed to update #contents: %s' % str(e), show=True)
            return 0

        db.set_field('title', title_updates)
        return len(contents_updates)

    # Direct menu actions (bypass dialog)
    def _save_title_author_to_description(self):
        book_ids = self._get_selected_ids()
        if not book_ids:
            return
        db = self.gui.current_db.new_api
        count = self._do_save_title_author_to_description(db, book_ids)
        self._refresh_ui(book_ids)
        info_dialog(self.gui, 'MetaManipulator',
            'Updated description for %d book(s).' % count, show=True)

    def _save_title_to_originaltitle(self):
        book_ids = self._get_selected_ids()
        if not book_ids:
            return
        db = self.gui.current_db.new_api
        count = self._do_save_title_to_originaltitle(db, book_ids)
        self._refresh_ui(book_ids)
        info_dialog(self.gui, 'MetaManipulator',
            'Saved title to #originaltitle for %d book(s).' % count, show=True)

    def _move_contents_from_title(self):
        book_ids = self._get_selected_ids()
        if not book_ids:
            return
        db = self.gui.current_db.new_api
        count = self._do_move_contents_from_title(db, book_ids)
        self._refresh_ui(book_ids)
        info_dialog(self.gui, 'MetaManipulator',
            'Moved contents from title for %d book(s).' % count, show=True)
