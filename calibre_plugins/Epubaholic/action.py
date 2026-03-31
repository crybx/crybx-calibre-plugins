from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import os, traceback
try:
    from qt.core import QUrl, QModelIndex, QMenu, QToolButton, QFileDialog
except ImportError:
    from PyQt5.Qt import QUrl, QModelIndex, QMenu, QToolButton, QFileDialog

from calibre.gui2 import error_dialog
from calibre.gui2.actions import InterfaceAction
from calibre.ptempfile import PersistentTemporaryDirectory, PersistentTemporaryFile, remove_dir

import calibre_plugins.epubaholic.config as cfg
from calibre_plugins.epubaholic import ActionModifyEpub
from calibre_plugins.epubaholic.common_icons import set_plugin_icon_resources, get_icon
from calibre_plugins.epubaholic.common_menus import create_menu_action_unique
from calibre_plugins.epubaholic.dialogs import (ModifyEpubDialog, QueueProgressDialog,
                                                 AddBooksProgressDialog)

PLUGIN_ICONS = ['images/epubaholic_book.png']

class ModifyEpubAction(InterfaceAction):

    name = 'Epubaholic'
    # Create our top-level menu/toolbar action (text, icon_path, tooltip, keyboard shortcut)
    action_spec = ('Epubaholic', None, 'Modify the contents of an epub without a conversion', ())
    action_type = 'current'
    popup_type = QToolButton.MenuButtonPopup

    def genesis(self):
        icon_resources = self.load_resources(PLUGIN_ICONS)
        set_plugin_icon_resources(self.name, icon_resources)
        self.qaction.setIcon(get_icon(PLUGIN_ICONS[0]))
        self.qaction.triggered.connect(self.modify_epub)

        self.menu = QMenu(self.gui)
        self.qaction.setMenu(self.menu)

        create_menu_action_unique(self, self.menu, 'Modify selected epubs',
                                  PLUGIN_ICONS[0], triggered=self.modify_epub)
        create_menu_action_unique(self, self.menu, 'Create epub from folder of HTML files\u2026',
                                  PLUGIN_ICONS[0], triggered=self.create_epub_from_folder)
        self.menu.addSeparator()
        create_menu_action_unique(self, self.menu, 'Customize plugin\u2026',
                                  'config.png', shortcut=False,
                                  triggered=self.show_configuration)
        self.gui.keyboard.finalize()

    def show_configuration(self):
        self.interface_action_base_plugin.do_user_config(self.gui)

    def create_epub_from_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self.gui, 'Select folder containing HTML files')
        if not folder:
            return

        html_extensions = ('.html', '.htm', '.xhtml')
        html_files = sorted(
            [f for f in os.listdir(folder) if f.lower().endswith(html_extensions)],
            key=lambda fn: int(''.join(c for c in fn if c.isdigit()) or '0')
        )

        if not html_files:
            return error_dialog(self.gui, 'No HTML files found',
                'The selected folder contains no HTML files.', show=True)

        title = os.path.basename(folder)

        temp_epub = PersistentTemporaryFile(suffix='.epub')
        temp_epub.close()

        try:
            self._build_epub_from_html_files(folder, temp_epub.name, title, html_files)
        except Exception as e:
            os.remove(temp_epub.name)
            return error_dialog(self.gui, 'Failed to create EPUB',
                'Error creating EPUB: %s' % str(e), show=True,
                det_msg=traceback.format_exc())

        from calibre.ebooks.metadata.book.base import Metadata
        mi = Metadata(title, ['Unknown'])
        db = self.gui.current_db
        book_id = db.import_book(mi, [temp_epub.name])
        os.remove(temp_epub.name)

        self.gui.library_view.model().books_added(1)
        self.gui.library_view.select_rows([book_id])
        self.gui.tags_view.recount()

        # Open Edit Metadata dialog for the new book
        self.gui.iactions['Edit Metadata'].edit_metadata(False)

    def _build_epub_from_html_files(self, folder_path, output_path, title, html_files):
        from lxml import etree
        from calibre.ebooks.metadata.book.base import Metadata
        from calibre.ebooks.metadata.opf2 import metadata_to_opf
        from calibre.ebooks.oeb.polish.container import OPF_NAMESPACES
        from calibre.ebooks.oeb.polish.toc import TOC, create_ncx
        from calibre.ebooks.oeb.polish.utils import guess_type
        from calibre.ebooks.oeb.polish.pretty import pretty_xml_tree
        from calibre.utils.zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED
        from calibre.utils.localization import lang_as_iso639_1

        mi = Metadata(title, ['Unknown'])
        opf = metadata_to_opf(mi, as_string=False)

        lang = 'und'
        for l in opf.xpath('//*[local-name()="language"]'):
            if l.text:
                lang = l.text
                break
        lang = lang_as_iso639_1(lang) or lang

        opfns = OPF_NAMESPACES['opf']

        # Build manifest
        manifest = opf.makeelement(f'{{{opfns}}}manifest')
        opf.insert(1, manifest)

        ncx_item = manifest.makeelement(f'{{{opfns}}}item', href='toc.ncx', id='ncx')
        ncx_item.set('media-type', guess_type('toc.ncx'))
        manifest.append(ncx_item)

        # Add stylesheet to manifest
        stylesheet = cfg.plugin_prefs[cfg.STORE_NAME].get(
            cfg.KEY_CREATE_EPUB_STYLESHEET, cfg.DEFAULT_CREATE_EPUB_STYLESHEET)
        css_item = manifest.makeelement(f'{{{opfns}}}item', href='styles/stylesheet.css', id='stylesheet')
        css_item.set('media-type', 'text/css')
        manifest.append(css_item)

        # Build spine
        spine = opf.makeelement(f'{{{opfns}}}spine', toc='ncx')
        opf.insert(2, spine)

        # Add each HTML file to manifest, spine, and TOC
        toc = TOC()
        for i, html_file in enumerate(html_files):
            file_id = 'chapter_%d' % i
            href = 'text/%s' % html_file

            item = manifest.makeelement(f'{{{opfns}}}item', href=href, id=file_id)
            item.set('media-type', guess_type('a.xhtml'))
            manifest.append(item)

            itemref = spine.makeelement(f'{{{opfns}}}itemref', idref=file_id)
            spine.append(itemref)

            toc_title = os.path.splitext(html_file)[0]
            toc.add(toc_title, href)

        # Build NCX
        uuid = ''
        for u in opf.xpath('//*[@id="uuid_id"]'):
            uuid = u.text
        ncx = create_ncx(toc, lambda x: x, title, lang, uuid)

        # Serialize XML
        pretty_xml_tree(opf)
        opf_bytes = etree.tostring(opf, encoding='utf-8', xml_declaration=True, pretty_print=True)
        ncx_bytes = etree.tostring(ncx, encoding='utf-8', xml_declaration=True, pretty_print=True)

        container_xml = (
            '<?xml version="1.0"?>\n'
            '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
            '   <rootfiles>\n'
            '      <rootfile full-path="EPUB/content.opf"'
            ' media-type="application/oebps-package+xml"/>\n'
            '   </rootfiles>\n'
            '</container>'
        ).encode('utf-8')

        # Write EPUB zip
        with ZipFile(output_path, 'w', compression=ZIP_DEFLATED) as zf:
            zf.writestr('mimetype', b'application/epub+zip', compression=ZIP_STORED)
            zf.writestr('META-INF/container.xml', container_xml)
            zf.writestr('EPUB/content.opf', opf_bytes)
            zf.writestr('EPUB/toc.ncx', ncx_bytes)
            zf.writestr('EPUB/styles/stylesheet.css', stylesheet.encode('utf-8'))
            for html_file in html_files:
                file_path = os.path.join(folder_path, html_file)
                zf.write(file_path, 'EPUB/text/%s' % html_file)

    def modify_epub(self):
        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows or len(rows) == 0:
            return error_dialog(self.gui, 'Cannot modify epub',
                'You must select one or more books to perform this action.', show=True)

        book_ids = set(self.gui.library_view.get_selected_ids())
        db = self.gui.library_view.model().db
        book_epubs = []
        for book_id in book_ids:
            if db.has_format(book_id, 'EPUB', index_is_id=True):
                book_epubs.append(book_id)

        if not book_epubs:
            return error_dialog(self.gui, 'Cannot modify epub',
                    'No epub available. First convert the book to epub.',
                    show=True)

        # Launch dialog asking user to specify what options to modify
        dlg = ModifyEpubDialog(self.gui, self)
        if dlg.exec_() == dlg.Accepted:
            # Create a temporary directory to copy all the epubs to while scanning
            tdir = PersistentTemporaryDirectory('_epubaholic', prefix='')
            QueueProgressDialog(self.gui, book_epubs, tdir, dlg.options, self._queue_job, db)

    def _queue_job(self, tdir, options, books_to_modify):
        if not books_to_modify:
            # All failed so cleanup our temp directory
            remove_dir(tdir)
            return

        func = 'arbitrary_n'
        cpus = self.gui.job_manager.server.pool_size
        args = ['calibre_plugins.epubaholic.jobs', 'do_modify_epubs',
                (books_to_modify, options, cpus)]
        desc = 'Modify epubs version ' + str(ActionModifyEpub.version)
        job = self.gui.job_manager.run_job(
                self.Dispatcher(self._modify_completed), func, args=args,
                    description=desc)
        job._tdir = tdir
        self.gui.status_bar.show_message('Modifying %d books'%len(books_to_modify))

    def _modify_completed(self, job):
        if job.failed:
            self.gui.job_exception(job, dialog_title='Failed to modify epubs')
            return
        modified_epubs_map = job.result
        self.gui.status_bar.show_message('Modify epub completed', 3000)

        update_count = len(modified_epubs_map)
        if update_count == 0:
            msg = ("No epub files were updated. If this isn't what you expected "
                    "then press the Show details button to check for errors in the log.")
            return error_dialog(self.gui, "Modify epub changed no files", msg,
                                show_copy_button=True, show=True,
                                det_msg=job.details)

        payload = (modified_epubs_map, job._tdir)

        if cfg.plugin_prefs[cfg.STORE_NAME].get(cfg.KEY_ASK_FOR_CONFIRMATION,
                                                cfg.DEFAULT_STORE_VALUES[cfg.KEY_ASK_FOR_CONFIRMATION]):
            msg = '<p>' + ('Modify epub modified <b>%d epub files(s)</b> into a temporary location. '
                   'Proceed with replacing the versions in your library?') % update_count

            self.gui.proceed_question(self._proceed_with_updating_epubs,
                payload, job.details,
                'Modify log', 'Modify epub complete', msg,
                show_copy_button=False,
                cancel_callback=self._cancel_updating_epubs)
        else:
            self._proceed_with_updating_epubs(payload)


    def _proceed_with_updating_epubs(self, payload):
        modified_epubs_map, tdir = payload

        # Check for custom metadata updates and apply them to the database
        custom_metadata_updates = {}
        for book_id, result in modified_epubs_map.items():
            if isinstance(result, tuple) and len(result) == 2:
                epub_path, custom_metadata = result
                if custom_metadata:
                    custom_metadata_updates[book_id] = custom_metadata

        if custom_metadata_updates:
            self._update_custom_columns(custom_metadata_updates)

        AddBooksProgressDialog(self.gui, modified_epubs_map, tdir)
        self.gui.tags_view.recount()
        if self.gui.current_view() is self.gui.library_view:
            current = self.gui.library_view.currentIndex()
            if current.isValid():
                self.gui.library_view.model().current_changed(current, QModelIndex())

    def _update_custom_columns(self, custom_metadata_updates):
        """Update custom columns and identifiers in Calibre's database"""
        db = self.gui.current_db
        db_ref = db.new_api if hasattr(db, 'new_api') else db

        # Group updates by column name
        col_name_books_map = {}
        identifier_updates = {}  # book_id -> {id_type: value}
        book_ids_to_update = []

        for book_id, custom_metadata in custom_metadata_updates.items():
            if db_ref.has_id(book_id):
                for col_name, value in custom_metadata.items():
                    if col_name == '_identifiers':
                        identifier_updates[book_id] = value
                        if book_id not in book_ids_to_update:
                            book_ids_to_update.append(book_id)
                        continue
                    if col_name not in col_name_books_map:
                        col_name_books_map[col_name] = {}
                    col_name_books_map[col_name][book_id] = value
                    if book_id not in book_ids_to_update:
                        book_ids_to_update.append(book_id)

        # Apply custom column updates
        for col_name, book_values_map in col_name_books_map.items():
            try:
                db_ref.set_field(col_name, book_values_map)
            except Exception as e:
                print(f"Failed to update custom column {col_name}: {str(e)}")

        # Apply identifier updates
        for book_id, identifiers in identifier_updates.items():
            for id_type, id_val in identifiers.items():
                try:
                    db.set_identifier(book_id, id_type, id_val)
                except Exception as e:
                    print(f"Failed to set identifier {id_type} for book {book_id}: {str(e)}")

        # Refresh the UI
        if book_ids_to_update:
            self.gui.library_view.model().refresh_ids(book_ids_to_update)
            self.gui.library_view.model().refresh_ids(book_ids_to_update,
                                      current_row=self.gui.library_view.currentIndex().row())

    def _cancel_updating_epubs(self, payload):
        _modified_epubs_map, tdir = payload
        # All failed so cleanup our temp directory
        remove_dir(tdir)
