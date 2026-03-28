from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'

try:
    from qt.core import QMenu, QToolButton
except ImportError:
    from PyQt5.Qt import QMenu, QToolButton

from calibre.gui2 import error_dialog
from calibre.gui2.actions import InterfaceAction

import calibre_plugins.linkmanager.config as cfg
from calibre_plugins.linkmanager.common_icons import set_plugin_icon_resources, get_icon
from calibre_plugins.linkmanager.common_menus import create_menu_action_unique

PLUGIN_ICONS = ['images/linkmanager.png']


class LinkManagerAction(InterfaceAction):

    name = 'Link Manager'
    action_spec = ('Link Manager', None, 'Manage markdown links in a custom column', ())
    action_type = 'current'
    popup_type = QToolButton.ToolButtonPopupMode.MenuButtonPopup

    def genesis(self):
        icon_resources = self.load_resources(PLUGIN_ICONS)
        set_plugin_icon_resources(self.name, icon_resources)
        self.qaction.setIcon(get_icon(PLUGIN_ICONS[0]))
        self.qaction.triggered.connect(self.manage_links)

        self.menu = QMenu(self.gui)
        self.qaction.setMenu(self.menu)

        create_menu_action_unique(self, self.menu, 'Manage Links\u2026',
                                  PLUGIN_ICONS[0], triggered=self.manage_links)
        self.menu.addSeparator()
        create_menu_action_unique(self, self.menu, 'Customize plugin\u2026',
                                  'config.png', shortcut=False,
                                  triggered=self.show_configuration)
        self.gui.keyboard.finalize()

    def show_configuration(self):
        self.interface_action_base_plugin.do_user_config(self.gui)

    def manage_links(self):
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows:
            return error_dialog(self.gui, 'Link Manager',
                'Select a book first.', show=True)

        book_ids = list(self.gui.library_view.get_selected_ids())
        db = self.gui.current_db
        config = cfg.plugin_prefs[cfg.STORE_NAME]
        col_name = config.get(cfg.KEY_COLUMN_NAME, '#links')

        if not col_name:
            return error_dialog(self.gui, 'Link Manager',
                'No column configured. Go to Customize plugin to set one.',
                show=True)

        if len(book_ids) > 1:
            self._manage_bulk(book_ids, db, config, col_name)
        else:
            self._manage_single(book_ids[0], db, config, col_name)

    def _manage_single(self, book_id, db, config, col_name):
        try:
            db_api = db.new_api if hasattr(db, 'new_api') else db
            current_val = db_api.field_for(col_name, book_id)
        except Exception as e:
            return error_dialog(self.gui, 'Link Manager',
                'Could not read column %s: %s' % (col_name, e), show=True)

        title = db.title(book_id, index_is_id=True) or str(book_id)

        from calibre_plugins.linkmanager.dialogs import LinkManagerDialog
        dlg = LinkManagerDialog(self.gui, title, current_val or '', col_name,
                                default_folder_dir=config.get(cfg.KEY_FOLDER_DEFAULT_DIR, ''),
                                default_folder_text=config.get(cfg.KEY_FOLDER_DEFAULT_TEXT, ''))
        if dlg.exec_() == dlg.Accepted:
            new_val = dlg.get_value()
            try:
                db_api.set_field(col_name, {book_id: new_val})
            except Exception as e:
                return error_dialog(self.gui, 'Link Manager',
                    'Could not write to column %s: %s' % (col_name, e),
                    show=True)

            self.gui.library_view.model().refresh_ids([book_id])
            current = self.gui.library_view.currentIndex()
            if current.isValid():
                from qt.core import QModelIndex
                self.gui.library_view.model().current_changed(current, QModelIndex())

    def _manage_bulk(self, book_ids, db, config, col_name):
        from calibre_plugins.linkmanager.dialogs import BulkLinkManagerDialog
        dlg = BulkLinkManagerDialog(self.gui, book_ids, db, col_name)
        if dlg.exec_() == dlg.Accepted:
            updated = dlg.updated_ids
            if updated:
                self.gui.library_view.model().refresh_ids(updated)
                self.gui.tags_view.recount()
