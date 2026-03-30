import json
import re

from qt.core import (
    QAction, QDialog, QDialogButtonBox, QFormLayout, QInputDialog, QLabel,
    QLineEdit, QPlainTextEdit, QSpinBox, QVBoxLayout,
)

from calibre.ebooks.oeb.polish.container import OEB_DOCS
from calibre.ebooks.oeb.polish.replace import rename_files
from calibre.gui2 import error_dialog, info_dialog
from calibre.gui2.tweak_book.plugin import Tool
from calibre.utils.config import JSONConfig

prefs = JSONConfig('plugins/fixfilenames')
prefs.defaults['rules'] = [
    {
        'glob': 'ep_fix_filename_',
        'extension': '.html',
        'patterns': [
            r'<h1>\s*(?P<num>\d+)\ud654',
            r'<h1>.*?(?P<num>\d+)\ud654</h1>',
            r'<h1>.*?(?P<num>\d+)<span[^>]*>\ud654</span></h1>',
            r'<h1>.*?(?P<num>\d+)</h1>',
            r'<h2>\s*(?P<num>\d+)\ud654\.',
            r'(?P<num>\d+)\ud654</p>',
        ],
        'filename': 'ep_{num}.html',
        'search_lines': 15,
    },
    {
        'glob': 'ep_fix_filename_',
        'extension': '.xhtml',
        'patterns': [
            r'<h2>.*?(?P<num>\d+)\ud654</h2>',
            r'<h2>.*?(?P<num>\d+)</h2>',
            r'<h3[^>]*>.*?(?P<num>\d+)\ud654</h3>',
            r'<title>(?P<num>\d+)\ud654</title>',
        ],
        'filename': 'ep_{num}.xhtml',
        'search_lines': 25,
    },
]


class ConfigDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Configure "Rename files by chapter number"')
        self.resize(700, 500)

        layout = QVBoxLayout(self)

        help_text = QLabel(
            'Edit rules as JSON. Each rule needs:\n'
            '  glob — filename prefix to match\n'
            '  extension — file extension to match (.html, .xhtml)\n'
            '  patterns — list of regexes with a named group "num" and optional "part"\n'
            '  filename — output template using {num} and optionally {part}\n'
            '             e.g. ep_{num}.html or ep_{num}_{part}.html\n'
            '  search_lines — how many lines from the top to search\n\n'
            'Both {num} and {part} are auto zero-padded.\n'
            'If {part} is in the template but not matched, it becomes empty.'
        )
        help_text.setWordWrap(True)
        layout.addWidget(help_text)

        self.editor = QPlainTextEdit(self)
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        current = prefs['rules']
        self.editor.setPlainText(json.dumps(current, indent=2, ensure_ascii=False))
        layout.addWidget(self.editor)

        self.error_label = QLabel('')
        self.error_label.setStyleSheet('color: red')
        layout.addWidget(self.error_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.RestoreDefaults)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(self.restore_defaults)
        layout.addWidget(buttons)

    def restore_defaults(self):
        self.editor.setPlainText(json.dumps(prefs.defaults['rules'], indent=2, ensure_ascii=False))

    def validate(self):
        try:
            rules = json.loads(self.editor.toPlainText())
        except json.JSONDecodeError as e:
            self.error_label.setText('Invalid JSON: %s' % e)
            return None
        if not isinstance(rules, list):
            self.error_label.setText('Rules must be a JSON array')
            return None
        for i, rule in enumerate(rules):
            for key in ('glob', 'extension', 'patterns', 'filename'):
                if key not in rule:
                    self.error_label.setText('Rule %d missing "%s"' % (i + 1, key))
                    return None
            for j, pat in enumerate(rule['patterns']):
                try:
                    re.compile(pat)
                except re.error as e:
                    self.error_label.setText('Rule %d, pattern %d: %s' % (i + 1, j + 1, e))
                    return None
                if 'num' not in re.compile(pat).groupindex:
                    self.error_label.setText('Rule %d, pattern %d: missing (?P<num>...) group' % (i + 1, j + 1))
                    return None
        self.error_label.setText('')
        return rules

    def accept(self):
        rules = self.validate()
        if rules is not None:
            prefs['rules'] = rules
            super().accept()


def extract_number(text, patterns):
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            num = int(m.group('num'))
            try:
                raw_part = m.group('part')
                part = int(raw_part) if raw_part is not None else None
            except IndexError:
                part = None
            return num, part
    return None, None


class RenameByChapterTool(Tool):

    name = 'rename-by-chapter'
    allowed_in_toolbar = False
    allowed_in_menu = True

    def create_action(self, for_toolbar=True):
        ac = QAction('Rename files by chapter number', self.gui)
        if not for_toolbar:
            self.register_shortcut(ac, 'fix-filenames-tool', default_keys=())
        ac.triggered.connect(self.run)
        return ac

    def run(self):
        selected = self.gui.file_list.file_list.selected_names
        if not selected:
            info_dialog(self.gui, 'Rename by chapter',
                'No files selected. Select files in the File browser first.', show=True)
            return
        self.boss.commit_all_editors_to_container()
        try:
            renamed, skipped, failed, details = self.fix_filenames(selected)
        except Exception:
            import traceback
            error_dialog(self.gui, 'Failed to rename files',
                'Failed to rename files, click "Show details" for more info',
                det_msg=traceback.format_exc(), show=True)
            self.boss.revert_requested(self.boss.global_undo.previous_container)
            return

        if renamed > 0:
            self.boss.show_current_diff()
            self.boss.apply_container_update_to_gui()
            return

        summary = '%d renamed, %d already correct, %d failed' % (renamed, skipped, failed)
        info_dialog(self.gui, 'Rename by chapter', summary,
            det_msg=details if details else None, show=True)

    def fix_filenames(self, selected):
        self.boss.add_savepoint('Before: Fix filenames')
        container = self.current_container
        rules = prefs['rules']

        total_renamed = 0
        total_skipped = 0
        total_failed = 0
        details_lines = []

        for rule in rules:
            prefix = rule['glob']
            ext = rule['extension']
            patterns = rule['patterns']
            filename_template = rule['filename']
            search_lines = rule.get('search_lines', 20)

            # Find matching files in the container
            matching = []
            for name, media_type in container.mime_map.items():
                if media_type not in OEB_DOCS:
                    continue
                if name not in selected:
                    continue
                basename = name.rsplit('/', 1)[-1] if '/' in name else name
                if basename.startswith(prefix) and basename.endswith(ext):
                    matching.append(name)
            matching.sort()

            if not matching:
                continue

            details_lines.append('[%s*%s]' % (prefix, ext))

            # First pass: extract all numbers to determine zero-padding width
            file_numbers = {}
            for name in matching:
                text = container.raw_data(name, decode=True)
                lines = text.split('\n')[:search_lines]
                header_text = '\n'.join(lines)
                num, part = extract_number(header_text, patterns)
                if num is not None:
                    file_numbers[name] = (num, part)

            if file_numbers:
                max_num = max(n for n, p in file_numbers.values())
                num_width = len(str(max_num))
                parts = [p for n, p in file_numbers.values() if p is not None]
                part_width = len(str(max(parts))) if parts else 0
            else:
                num_width = 1
                part_width = 0

            # Second pass: build rename map with zero-padded numbers
            file_map = {}
            targets_seen = {}

            for name in matching:
                dirname = name.rsplit('/', 1)[0] + '/' if '/' in name else ''
                basename = name.rsplit('/', 1)[-1] if '/' in name else name

                entry = file_numbers.get(name)
                if entry is None:
                    details_lines.append('  SKIP (no match):  %s' % basename)
                    total_failed += 1
                    continue

                num, part = entry
                fmt = {'num': str(num).zfill(num_width)}
                if part is not None:
                    fmt['part'] = str(part).zfill(part_width)
                else:
                    fmt['part'] = ''

                new_basename = filename_template.format(**fmt)
                new_name = dirname + new_basename

                if new_name == name:
                    total_skipped += 1
                    continue

                if container.exists(new_name) and new_name not in file_map.values():
                    details_lines.append('  CONFLICT:         %s -> %s (target exists)' % (basename, new_basename))
                    total_failed += 1
                    continue

                if new_name in targets_seen:
                    details_lines.append('  DUPLICATE TARGET: %s -> %s (same as %s)' % (
                        basename, new_basename, targets_seen[new_name]))
                    total_failed += 1
                    continue

                targets_seen[new_name] = basename
                file_map[name] = new_name
                details_lines.append('  Renamed:  %s  ->  %s' % (basename, new_basename))

            if file_map:
                rename_files(container, file_map)
                total_renamed += len(file_map)

            details_lines.append('  --- %d renamed, %d already correct, %d failed\n' % (
                len(file_map), total_skipped, total_failed))

        return total_renamed, total_skipped, total_failed, '\n'.join(details_lines)


class SortSpineTool(Tool):

    name = 'sort-spine'
    allowed_in_toolbar = False
    allowed_in_menu = True

    def create_action(self, for_toolbar=True):
        ac = QAction('Sort files by filename', self.gui)
        if not for_toolbar:
            self.register_shortcut(ac, 'sort-spine-tool', default_keys=())
        ac.triggered.connect(self.run)
        return ac

    def run(self):
        selected = self.gui.file_list.file_list.selected_names
        if not selected:
            info_dialog(self.gui, 'Sort files',
                'No files selected. Select files in the File browser first.', show=True)
            return
        self.boss.commit_all_editors_to_container()
        try:
            details = self.sort_spine(selected)
        except Exception:
            import traceback
            error_dialog(self.gui, 'Failed to sort spine',
                'Failed to sort spine, click "Show details" for more info',
                det_msg=traceback.format_exc(), show=True)
            self.boss.revert_requested(self.boss.global_undo.previous_container)
            return

        if details:
            self.boss.show_current_diff()
            self.boss.apply_container_update_to_gui()

    def sort_spine(self, selected):
        self.boss.add_savepoint('Before: Sort files by filename')
        container = self.current_container

        def natural_key(name):
            return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', name)]

        manifest_id_map = container.manifest_id_map  # {idref: canonical_name}

        # Get all <itemref> elements from the spine
        spine_elem = container.opf_xpath('//opf:spine')[0]
        itemrefs = list(container.opf_xpath('//opf:spine/opf:itemref[@idref]'))

        # Identify selected spine elements
        selected_indices = []
        selected_elements = []
        for i, item in enumerate(itemrefs):
            idref = item.get('idref')
            name = manifest_id_map.get(idref)
            if name and name in selected:
                selected_indices.append(i)
                selected_elements.append(item)

        if not selected_indices:
            info_dialog(self.gui, 'Sort files',
                'None of the selected files are in the spine.', show=True)
            return None

        # Sort by basename only (ignore directory path)
        def sort_key(item):
            name = manifest_id_map.get(item.get('idref'), '')
            basename = name.rsplit('/', 1)[-1] if '/' in name else name
            return natural_key(basename)
        sorted_elements = sorted(selected_elements, key=sort_key)

        if all(a is b for a, b in zip(selected_elements, sorted_elements)):
            info_dialog(self.gui, 'Sort files', 'Files are already sorted.', show=True)
            return None

        # Place sorted elements back into their original positions
        for idx, elem in zip(selected_indices, sorted_elements):
            itemrefs[idx] = elem

        # Rebuild spine: remove all itemrefs, re-add in new order
        tail = itemrefs[0].tail if itemrefs else '\n    '
        last_tail = itemrefs[-1].tail if itemrefs else '\n  '
        for item in list(spine_elem):
            if item.tag and item.tag.endswith('}itemref'):
                spine_elem.remove(item)
        for i, item in enumerate(itemrefs):
            item.tail = last_tail if i == len(itemrefs) - 1 else tail
            spine_elem.append(item)

        container.dirty(container.opf_name)
        return True


class ConfigureRenameTool(Tool):

    name = 'rename-configure'
    allowed_in_toolbar = False
    allowed_in_menu = True

    def create_action(self, for_toolbar=True):
        ac = QAction('Configure "Rename files by chapter number"...', self.gui)
        ac.triggered.connect(self.run)
        return ac

    def run(self):
        ConfigDialog(self.gui).exec()


class RenamePrependTool(Tool):

    name = 'rename-prepend'
    allowed_in_toolbar = False
    allowed_in_menu = True

    def create_action(self, for_toolbar=True):
        ac = QAction('Rename prepend (number + original name)...', self.gui)
        if not for_toolbar:
            self.register_shortcut(ac, 'rename-prepend-tool', default_keys=())
        ac.triggered.connect(self.run)
        return ac

    def run(self):
        selected = self.gui.file_list.file_list.selected_names
        if not selected:
            info_dialog(self.gui, 'Rename prepend',
                'No files selected. Select files in the File browser first.', show=True)
            return

        # Only consider HTML/XHTML document files
        container = self.current_container
        doc_names = [n for n in selected if container.mime_map.get(n) in OEB_DOCS]
        if not doc_names:
            info_dialog(self.gui, 'Rename prepend',
                'No HTML/XHTML files in selection.', show=True)
            return

        # Show config dialog
        dlg = QDialog(self.gui)
        dlg.setWindowTitle('Rename prepend')
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel(
            'Prepend a numbered prefix to each selected file.\n'
            'e.g. prefix "ep_" starting at 1 renames files to:\n'
            '  ep_01_originalname.html, ep_02_originalname.html, ...'))

        form = QFormLayout()
        prefix_edit = QLineEdit('ep_')
        form.addRow('Prefix:', prefix_edit)
        start_spin = QSpinBox()
        start_spin.setMinimum(0)
        start_spin.setMaximum(99999)
        start_spin.setValue(1)
        form.addRow('Start number:', start_spin)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        prefix = prefix_edit.text()
        start = start_spin.value()

        self.boss.commit_all_editors_to_container()
        try:
            renamed, skipped, failed, details = self.prepend_rename(doc_names, prefix, start)
        except Exception:
            import traceback
            error_dialog(self.gui, 'Failed to rename files',
                'Failed to rename files, click "Show details" for more info',
                det_msg=traceback.format_exc(), show=True)
            self.boss.revert_requested(self.boss.global_undo.previous_container)
            return

        if renamed > 0:
            self.boss.show_current_diff()
            self.boss.apply_container_update_to_gui()
            return

        summary = '%d renamed, %d already correct, %d failed' % (renamed, skipped, failed)
        info_dialog(self.gui, 'Rename prepend', summary,
            det_msg=details if details else None, show=True)

    def prepend_rename(self, doc_names, prefix, start):
        self.boss.add_savepoint('Before: Rename prepend')
        container = self.current_container

        # Build spine order lookup: name -> position
        manifest_id_map = container.manifest_id_map
        itemrefs = list(container.opf_xpath('//opf:spine/opf:itemref[@idref]'))
        spine_order = {}
        for i, item in enumerate(itemrefs):
            name = manifest_id_map.get(item.get('idref'))
            if name:
                spine_order[name] = i

        # Sort selected files by spine order (files not in spine go to the end)
        max_spine = len(itemrefs)
        sorted_names = sorted(doc_names, key=lambda n: spine_order.get(n, max_spine))

        end = start + len(sorted_names) - 1
        num_width = len(str(end))

        file_map = {}
        targets_seen = {}
        details_lines = []
        renamed = 0
        skipped = 0
        failed = 0

        for i, name in enumerate(sorted_names):
            num = start + i
            dirname = name.rsplit('/', 1)[0] + '/' if '/' in name else ''
            basename = name.rsplit('/', 1)[-1] if '/' in name else name

            new_basename = '%s%s_%s' % (prefix, str(num).zfill(num_width), basename)
            new_name = dirname + new_basename

            if new_name == name:
                skipped += 1
                continue

            if container.exists(new_name) and new_name not in file_map.values():
                details_lines.append('  CONFLICT:         %s -> %s (target exists)' % (basename, new_basename))
                failed += 1
                continue

            if new_name in targets_seen:
                details_lines.append('  DUPLICATE TARGET: %s -> %s (same as %s)' % (
                    basename, new_basename, targets_seen[new_name]))
                failed += 1
                continue

            targets_seen[new_name] = basename
            file_map[name] = new_name
            details_lines.append('  Renamed:  %s  ->  %s' % (basename, new_basename))

        if file_map:
            rename_files(container, file_map)
            renamed = len(file_map)

        details_lines.append('  --- %d renamed, %d already correct, %d failed' % (renamed, skipped, failed))
        return renamed, skipped, failed, '\n'.join(details_lines)


class RenameReplaceTool(Tool):

    name = 'rename-replace'
    allowed_in_toolbar = False
    allowed_in_menu = True

    def create_action(self, for_toolbar=True):
        ac = QAction('Rename replace in filename...', self.gui)
        if not for_toolbar:
            self.register_shortcut(ac, 'rename-replace-tool', default_keys=())
        ac.triggered.connect(self.run)
        return ac

    def run(self):
        selected = self.gui.file_list.file_list.selected_names
        if not selected:
            info_dialog(self.gui, 'Rename replace',
                'No files selected. Select files in the File browser first.', show=True)
            return

        container = self.current_container
        doc_names = [n for n in selected if container.mime_map.get(n) in OEB_DOCS]
        if not doc_names:
            info_dialog(self.gui, 'Rename replace',
                'No HTML/XHTML files in selection.', show=True)
            return

        dlg = QDialog(self.gui)
        dlg.setWindowTitle('Rename replace')
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel(
            'Replace text in filenames of selected files.\n'
            'Leave "Replace with" empty to remove the matched text.'))

        form = QFormLayout()
        find_edit = QLineEdit()
        find_edit.setPlaceholderText('e.g. ep_')
        form.addRow('Find:', find_edit)
        replace_edit = QLineEdit()
        replace_edit.setPlaceholderText('e.g. ch_ (leave empty to remove)')
        form.addRow('Replace with:', replace_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        find_text = find_edit.text()
        if not find_text:
            return
        replace_text = replace_edit.text()

        self.boss.commit_all_editors_to_container()
        try:
            renamed, skipped, failed, details = self.replace_in_names(
                doc_names, find_text, replace_text)
        except Exception:
            import traceback
            error_dialog(self.gui, 'Failed to rename files',
                'Failed to rename files, click "Show details" for more info',
                det_msg=traceback.format_exc(), show=True)
            self.boss.revert_requested(self.boss.global_undo.previous_container)
            return

        if renamed > 0:
            self.boss.show_current_diff()
            self.boss.apply_container_update_to_gui()
            return

        summary = '%d renamed, %d unchanged, %d failed' % (renamed, skipped, failed)
        info_dialog(self.gui, 'Rename replace', summary,
            det_msg=details if details else None, show=True)

    def replace_in_names(self, doc_names, find_text, replace_text):
        self.boss.add_savepoint('Before: Rename replace "%s" -> "%s"' % (find_text, replace_text))
        container = self.current_container

        file_map = {}
        targets_seen = {}
        details_lines = []
        renamed = 0
        skipped = 0
        failed = 0

        for name in sorted(doc_names):
            dirname = name.rsplit('/', 1)[0] + '/' if '/' in name else ''
            basename = name.rsplit('/', 1)[-1] if '/' in name else name

            if find_text not in basename:
                skipped += 1
                continue

            new_basename = basename.replace(find_text, replace_text, 1)
            new_name = dirname + new_basename

            if new_name == name:
                skipped += 1
                continue

            if not new_basename or new_basename.startswith('.'):
                details_lines.append('  INVALID:          %s -> %s' % (basename, new_basename))
                failed += 1
                continue

            if container.exists(new_name) and new_name not in file_map.values():
                details_lines.append('  CONFLICT:         %s -> %s (target exists)' % (basename, new_basename))
                failed += 1
                continue

            if new_name in targets_seen:
                details_lines.append('  DUPLICATE TARGET: %s -> %s (same as %s)' % (
                    basename, new_basename, targets_seen[new_name]))
                failed += 1
                continue

            targets_seen[new_name] = basename
            file_map[name] = new_name
            details_lines.append('  Renamed:  %s  ->  %s' % (basename, new_basename))

        if file_map:
            rename_files(container, file_map)
            renamed = len(file_map)

        details_lines.append('  --- %d renamed, %d unchanged, %d failed' % (renamed, skipped, failed))
        return renamed, skipped, failed, '\n'.join(details_lines)


class DeleteMatchingFilesTool(Tool):

    name = 'delete-matching-files'
    allowed_in_toolbar = False
    allowed_in_menu = True

    def create_action(self, for_toolbar=True):
        ac = QAction('Delete files matching...', self.gui)
        if not for_toolbar:
            self.register_shortcut(ac, 'delete-matching-files-tool', default_keys=())
        ac.triggered.connect(self.run)
        return ac

    def run(self):
        text, ok = QInputDialog.getText(
            self.gui, 'Delete matching files',
            'Delete all files whose name contains:')
        if not ok or not text.strip():
            return

        pattern = text.strip()
        container = self.current_container
        names_to_delete = [name for name in container.mime_map if pattern in name.rsplit('/', 1)[-1]]

        if not names_to_delete:
            info_dialog(self.gui, 'Delete matching files',
                'No files found matching "%s".' % pattern, show=True)
            return

        names_to_delete.sort()

        dlg = QDialog(self.gui)
        dlg.setWindowTitle('Confirm delete')
        dlg.resize(400, 300)
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel('Delete %d file(s) matching "%s"?' % (len(names_to_delete), pattern)))
        file_list = QPlainTextEdit(dlg)
        file_list.setReadOnly(True)
        file_list.setPlainText('\n'.join(n.rsplit('/', 1)[-1] for n in names_to_delete))
        layout.addWidget(file_list)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.No)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        self.boss.commit_all_editors_to_container()
        self.boss.add_savepoint('Before: Delete files matching "%s"' % pattern)

        c = self.current_container
        protected = c.names_that_must_not_be_removed
        skipped = []
        for name in names_to_delete:
            if name in protected:
                skipped.append(name)
                continue
            c.remove_item(name)

        self.boss.set_modified()
        self.boss.apply_container_update_to_gui()
        self.boss.show_current_diff()

        summary = 'Deleted %d file(s).' % (len(names_to_delete) - len(skipped))
        if skipped:
            summary += '\nSkipped %d protected file(s): %s' % (len(skipped), ', '.join(skipped))
        info_dialog(self.gui, 'Delete matching files', summary, show=True)
