from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import os, re, shutil, traceback
try:
    from qt.core import (QUrl, QModelIndex, QMenu, QToolButton, QFileDialog,
                         QListView, QTreeView, QAbstractItemView)
except ImportError:
    from PyQt5.Qt import (QUrl, QModelIndex, QMenu, QToolButton, QFileDialog,
                          QListView, QTreeView, QAbstractItemView)

from calibre.gui2 import error_dialog, question_dialog
from calibre.gui2.actions import InterfaceAction
from calibre.ptempfile import PersistentTemporaryDirectory, PersistentTemporaryFile, remove_dir

import calibre_plugins.epubaholic.config as cfg
from calibre_plugins.epubaholic import ActionModifyEpub
from calibre_plugins.epubaholic.chapter_files import (chapter_number_from_filename,
                                                      html_chapter_files)
from calibre_plugins.epubaholic.common_icons import set_plugin_icon_resources, get_icon
from calibre_plugins.epubaholic.common_menus import create_menu_action_unique
from calibre_plugins.epubaholic.dialogs import (ALL_OPTIONS, ModifyEpubDialog,
                                                 QueueProgressDialog, AddBooksProgressDialog)

PLUGIN_ICONS = ['images/epubaholic_book.png']

class ModifyEpubAction(InterfaceAction):

    name = 'Epubaholic'
    # Create our top-level menu/toolbar action (text, icon_path, tooltip, keyboard shortcut)
    action_spec = ('Epubaholic', None, 'Modify the contents of an epub without a conversion', ())
    action_type = 'current'
    popup_type = QToolButton.MenuButtonPopup

    # Hangul syllables, plus compatibility and conjoining jamo
    KOREAN_RE = re.compile('[\uac00-\ud7a3\u1100-\u11ff\u3130-\u318f]')
    LATIN_RE = re.compile('[A-Za-z]')

    def genesis(self):
        icon_resources = self.load_resources(PLUGIN_ICONS)
        set_plugin_icon_resources(self.name, icon_resources)
        self.qaction.setIcon(get_icon(PLUGIN_ICONS[0]))
        self.qaction.triggered.connect(self.modify_epub)

        self.menu = QMenu(self.gui)
        self.qaction.setMenu(self.menu)

        create_menu_action_unique(self, self.menu, 'Modify selected epubs',
                                  PLUGIN_ICONS[0], triggered=self.modify_epub)
        create_menu_action_unique(self, self.menu, 'Create epub(s) from folder(s) of HTML files\u2026',
                                  PLUGIN_ICONS[0], triggered=self.create_epub_from_folder)
        create_menu_action_unique(self, self.menu, 'Import chapters from folder\u2026',
                                  PLUGIN_ICONS[0], triggered=self.import_chapters_from_folder)
        self.menu.addSeparator()
        create_menu_action_unique(self, self.menu, 'Customize plugin\u2026',
                                  'config.png', shortcut=False,
                                  triggered=self.show_configuration)
        self.gui.keyboard.finalize()

    def show_configuration(self):
        self.interface_action_base_plugin.do_user_config(self.gui)

    def create_epub_from_folder(self):
        from calibre.utils.config import dynamic
        PREF_KEY = 'epubaholic_create_epub_last_dir'
        initial_dir = dynamic.get(PREF_KEY, os.path.expanduser('~'))
        if not os.path.isdir(initial_dir):
            initial_dir = os.path.expanduser('~')

        dialog = QFileDialog(self.gui, 'Select one or more folders containing HTML files')
        dialog.setDirectory(initial_dir)
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        for view in dialog.findChildren(QListView):
            view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        for view in dialog.findChildren(QTreeView):
            view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        if not dialog.exec_():
            return
        folders = dialog.selectedFiles()
        if not folders:
            return

        # Remember parent of selected folders for next time
        dynamic.set(PREF_KEY, os.path.dirname(folders[0]))

        for folder in folders:
            html_files = html_chapter_files(folder)
            title = os.path.basename(folder)

            temp_epub = PersistentTemporaryFile(suffix='.epub')
            temp_epub.close()

            try:
                self._build_epub_from_html_files(folder, temp_epub.name, title, html_files)
            except Exception as e:
                os.remove(temp_epub.name)
                error_dialog(self.gui, 'Failed to create EPUB',
                    'Error creating EPUB from "%s": %s' % (title, str(e)),
                    show=True, det_msg=traceback.format_exc())
                continue

            from calibre.ebooks.metadata.book.base import Metadata
            mi = Metadata(title, ['Unknown'])
            db = self.gui.current_db
            book_id = db.import_book(mi, [temp_epub.name])
            os.remove(temp_epub.name)

            self._apply_auto_metadata(book_id, title, folder, html_files)

            self.gui.library_view.model().books_added(1)
            self.gui.library_view.select_rows([book_id])
            self.gui.tags_view.recount()

            # Open Edit Metadata dialog for the new book (modal — blocks until closed)
            self.gui.iactions['Edit Metadata'].edit_metadata(False)

            # Move the source folder into the configured added-chapters directory
            self._archive_source_folder(folder)

    def _is_korean(self, folder_path, html_files, title):
        '''
        Sample the first, middle and last chapter files and decide whether the
        book is Korean by comparing Hangul characters against Latin letters in
        the visible text (markup and scripts stripped). The folder name is
        included in the sample.
        '''
        sample_files = []
        if html_files:
            for idx in (0, len(html_files) // 2, len(html_files) - 1):
                if html_files[idx] not in sample_files:
                    sample_files.append(html_files[idx])

        text = title or ''
        for html_file in sample_files:
            try:
                with open(os.path.join(folder_path, html_file), 'r',
                          encoding='utf-8', errors='replace') as f:
                    raw = f.read()
            except EnvironmentError:
                continue
            raw = re.sub(r'(?is)<(script|style)\b.*?</\1>', ' ', raw)
            text += re.sub(r'<[^>]+>', ' ', raw)

        korean = len(self.KOREAN_RE.findall(text))
        return korean > 0 and korean > len(self.LATIN_RE.findall(text))

    # Source sites from the chapter filenames, mapped to the
    # publisher name to use for them.
    PUBLISHER_BY_SOURCE = (
        ('page_kakao_com', 'Kakao'),
        ('ridibooks_com', 'Ridibooks'),
    )

    @classmethod
    def _publisher_from_filenames(cls, html_files):
        '''
        Return the publisher for the first known source site named in any of
        the chapter filenames, or None when none of them match.
        '''
        for marker, publisher in cls.PUBLISHER_BY_SOURCE:
            for html_file in html_files:
                if marker in html_file.lower():
                    return publisher
        return None

    def _apply_auto_metadata(self, book_id, title, folder_path, html_files):
        '''
        Populate #fandom, #type, #contents (from the highest detected
        chapter number) and the publisher (from the source site named in the
        chapter filenames), and for Korean content also set #origin, the
        language and #originaltitle. Custom columns that do not exist in the
        current library are skipped.
        '''
        db = self.gui.current_db.new_api
        custom_keys = set(db.field_metadata.custom_field_keys())
        updates = {}

        for field, value in (('#fandom', 'original'), ('#type', 'webnovel')):
            if field in custom_keys:
                updates[field] = value

        contents = chapter_number_from_filename(html_files[-1]) if html_files else None
        if contents and '#contents' in custom_keys:
            updates['#contents'] = contents

        publisher = self._publisher_from_filenames(html_files)
        if publisher:
            updates['publisher'] = publisher

        if self._is_korean(folder_path, html_files, title):
            updates['languages'] = ['kor']
            if '#origin' in custom_keys:
                updates['#origin'] = 'kr'
            if '#originaltitle' in custom_keys:
                updates['#originaltitle'] = title.replace('_', ' ')

        failures = []
        for field, value in updates.items():
            try:
                db.set_field(field, {book_id: value})
            except Exception as e:
                failures.append('%s: %s' % (field, str(e)))
        if failures:
            error_dialog(self.gui, 'Could not set metadata',
                'Failed to set metadata for "%s":\n%s' % (title, '\n'.join(failures)),
                show=True, det_msg=traceback.format_exc())

    def _archive_source_folder(self, folder):
        '''
        Move a processed source folder into the configured added-chapters
        directory so it doesn't get re-imported on the next run. Silently
        skips if the destination is unconfigured or unreachable; surfaces
        per-folder failures via an error dialog without aborting the loop.
        '''
        added_root = cfg.plugin_prefs[cfg.STORE_NAME].get(
            cfg.KEY_ADDED_CHAPTERS_PATH, cfg.DEFAULT_ADDED_CHAPTERS_PATH)
        if not added_root:
            return
        try:
            os.makedirs(added_root, exist_ok=True)
        except OSError as e:
            error_dialog(self.gui, 'Could not archive source folder',
                'Added chapters folder is not accessible: %s\n\n%s' % (added_root, str(e)),
                show=True, det_msg=traceback.format_exc())
            return

        base_name = os.path.basename(os.path.normpath(folder))
        target = os.path.join(added_root, base_name)
        suffix = 1
        while os.path.exists(target):
            target = os.path.join(added_root, '%s_%d' % (base_name, suffix))
            suffix += 1

        try:
            shutil.move(folder, target)
        except Exception as e:
            error_dialog(self.gui, 'Could not archive source folder',
                'Failed to move "%s" to "%s": %s' % (folder, target, str(e)),
                show=True, det_msg=traceback.format_exc())

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

    def import_chapters_from_folder(self):
        '''
        Import every html file in a folder the user picks into the one
        selected book, without the search term matching that the "Import
        chapters" option relies on. Only makes sense for a single book and a
        single folder, so both are required.
        '''
        from calibre.utils.config import dynamic
        PREF_KEY = 'epubaholic_import_chapters_last_dir'

        rows = self.gui.library_view.selectionModel().selectedRows()
        if not rows or len(rows) != 1:
            return error_dialog(self.gui, 'Cannot import chapters',
                'You must select exactly one book to import chapters into.', show=True)

        book_id = self.gui.library_view.get_selected_ids()[0]
        db = self.gui.library_view.model().db
        if not db.has_format(book_id, 'EPUB', index_is_id=True):
            return error_dialog(self.gui, 'Cannot import chapters',
                'No epub available. First convert the book to epub.', show=True)

        initial_dir = dynamic.get(PREF_KEY, os.path.expanduser('~'))
        if not os.path.isdir(initial_dir):
            initial_dir = os.path.expanduser('~')

        folder = QFileDialog.getExistingDirectory(self.gui,
            'Select the folder of HTML files to import as chapters', initial_dir,
            QFileDialog.Option.ShowDirsOnly)
        if not folder:
            return

        # Remember parent of the selected folder for next time
        dynamic.set(PREF_KEY, os.path.dirname(folder))

        html_files = html_chapter_files(folder)
        if not html_files:
            return error_dialog(self.gui, 'Cannot import chapters',
                'No HTML files found in "%s".' % folder, show=True)

        title = db.title(book_id, index_is_id=True)
        if not question_dialog(self.gui, 'Import chapters',
                '<p>' + ('Import <b>%d HTML file(s)</b> from "%s" as chapters of '
                         '<b>%s</b>?') % (len(html_files), folder, title)):
            return

        # Run the existing import through the normal modify pipeline, with
        # every other modify option turned off.
        options = dict((key, False) for key, _t, _tt in ALL_OPTIONS)
        options['import_chapters'] = True
        options['import_chapters_folder'] = folder

        tdir = PersistentTemporaryDirectory('_epubaholic', prefix='')
        QueueProgressDialog(self.gui, [book_id], tdir, options, self._queue_job, db)

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
