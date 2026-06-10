from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'

import os
import re
from urllib.parse import quote

try:
    from qt.core import (Qt, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                         QPushButton, QTableWidget, QTableWidgetItem,
                         QAbstractItemView, QHeaderView, QApplication,
                         QFileDialog, QSize, QLineEdit, QCheckBox,
                         QProgressBar, QTimer)
except ImportError:
    from PyQt5.Qt import (Qt, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                          QPushButton, QTableWidget, QTableWidgetItem,
                          QAbstractItemView, QHeaderView, QApplication,
                          QFileDialog, QSize, QLineEdit, QCheckBox,
                          QProgressBar, QTimer)


# Map of substrings found in a URL to a default display text. When a bare URL
# is added (e.g. from the clipboard) and contains one of these substrings, the
# corresponding text is used instead of repeating the URL.
SITE_DEFAULT_TEXT = {
    'novelupdates.com': 'Novel Updates',
    'ridibooks.com': 'Ridibooks',
}


def default_text_for_url(url):
    """Return a default display text for a URL based on known sites.

    Falls back to the URL itself if no known site matches.
    """
    lowered = url.lower()
    for substring, text in SITE_DEFAULT_TEXT.items():
        if substring in lowered:
            return text
    return url


def parse_links(text):
    """Parse markdown links from comma-separated text.
    Format: [text](url), [text2](url2)
    Returns list of (text, url) tuples.
    """
    if not text or not text.strip():
        return []
    links = []
    for match in re.finditer(r'\[([^\]]*)\]\(([^)]*)\)', text):
        links.append((match.group(1), match.group(2)))
    return links


def format_links(links):
    """Format list of (text, url) tuples as comma-separated markdown links."""
    return ', '.join('[%s](%s)' % (text, url) for text, url in links)


def path_to_file_uri(folder_path):
    """Convert a filesystem path to a file:/// URI with proper encoding."""
    # Normalize path separators
    folder_path = folder_path.replace('\\', '/')
    # Remove trailing slash
    folder_path = folder_path.rstrip('/')
    # Split into drive and rest for Windows paths
    if len(folder_path) >= 2 and folder_path[1] == ':':
        drive = folder_path[0]
        rest = folder_path[2:]
        # Encode each path component
        encoded_parts = []
        for part in rest.split('/'):
            if part:
                encoded_parts.append(quote(part, safe=''))
        return 'file:///%s:/%s' % (drive, '/'.join(encoded_parts))
    else:
        # Unix path
        parts = []
        for part in folder_path.split('/'):
            if part:
                parts.append(quote(part, safe=''))
        return 'file:///' + '/'.join(parts)


class LinkManagerDialog(QDialog):

    def __init__(self, parent, book_title, current_value, col_name,
                 default_folder_dir='', default_folder_text=''):
        QDialog.__init__(self, parent)
        self.setWindowTitle('Link Manager - %s' % book_title)
        self.resize(QSize(700, 450))
        self.default_folder_dir = default_folder_dir
        self.default_folder_text = default_folder_text

        self.links = parse_links(current_value)

        layout = QVBoxLayout(self)
        self.setLayout(layout)

        # Header
        layout.addWidget(QLabel('Links in <b>%s</b> for: <i>%s</i>' % (col_name, book_title)))

        # Table
        self.table = QTableWidget(self)
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(['Text', 'URL'])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().resizeSection(0, 200)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setWordWrap(True)
        layout.addWidget(self.table)

        # Control buttons row
        btn_row = QHBoxLayout()

        self.sort_btn = QPushButton('Sort A-Z', self)
        self.sort_btn.setToolTip('Sort links alphabetically by text')
        self.sort_btn.clicked.connect(self.sort_links)
        btn_row.addWidget(self.sort_btn)

        self.paste_btn = QPushButton('Add from Clipboard', self)
        self.paste_btn.setToolTip('Add a markdown link from clipboard: [text](url)')
        self.paste_btn.clicked.connect(self.add_from_clipboard)
        btn_row.addWidget(self.paste_btn)

        self.folder_btn = QPushButton('Add Folder Link\u2026', self)
        self.folder_btn.setToolTip('Pick a folder and add it as a file:/// link')
        self.folder_btn.clicked.connect(self.add_folder_link)
        btn_row.addWidget(self.folder_btn)

        self.open_btn = QPushButton('Open', self)
        self.open_btn.setToolTip('Open the selected link in the default application')
        self.open_btn.clicked.connect(self.open_selected)
        btn_row.addWidget(self.open_btn)

        btn_row.addStretch()

        self.up_btn = QPushButton('\u2191 Up', self)
        self.up_btn.clicked.connect(self.move_up)
        btn_row.addWidget(self.up_btn)

        self.down_btn = QPushButton('\u2193 Down', self)
        self.down_btn.clicked.connect(self.move_down)
        btn_row.addWidget(self.down_btn)

        self.delete_btn = QPushButton('Delete', self)
        self.delete_btn.clicked.connect(self.delete_selected)
        btn_row.addWidget(self.delete_btn)

        layout.addLayout(btn_row)

        # Manual add row
        add_row = QHBoxLayout()
        add_row.addWidget(QLabel('Text:'))
        self.new_text_edit = QLineEdit(self)
        self.new_text_edit.setPlaceholderText('Display text')
        add_row.addWidget(self.new_text_edit)
        add_row.addWidget(QLabel('URL:'))
        self.new_url_edit = QLineEdit(self)
        self.new_url_edit.setPlaceholderText('https://...')
        add_row.addWidget(self.new_url_edit, stretch=1)
        self.add_btn = QPushButton('Add', self)
        self.add_btn.clicked.connect(self.add_manual)
        add_row.addWidget(self.add_btn)
        layout.addLayout(add_row)

        # Dialog buttons
        dialog_btns = QHBoxLayout()
        dialog_btns.addStretch()
        self.apply_btn = QPushButton('Apply', self)
        self.apply_btn.clicked.connect(self.accept)
        dialog_btns.addWidget(self.apply_btn)
        self.cancel_btn = QPushButton('Cancel', self)
        self.cancel_btn.clicked.connect(self.reject)
        dialog_btns.addWidget(self.cancel_btn)
        layout.addLayout(dialog_btns)

        self._populate_table()

    def showEvent(self, event):
        QDialog.showEvent(self, event)
        self.table.resizeRowsToContents()

    def _populate_table(self):
        self.table.setRowCount(len(self.links))
        for row, (text, url) in enumerate(self.links):
            text_item = QTableWidgetItem(text)
            url_item = QTableWidgetItem(url)
            self.table.setItem(row, 0, text_item)
            self.table.setItem(row, 1, url_item)
        # Defer row resize so Qt has finished laying out the new content
        QTimer.singleShot(0, self.table.resizeRowsToContents)

    def _read_table(self):
        """Read current state from table back into self.links."""
        self.links = []
        for row in range(self.table.rowCount()):
            text = self.table.item(row, 0).text().strip() if self.table.item(row, 0) else ''
            url = self.table.item(row, 1).text().strip() if self.table.item(row, 1) else ''
            if text or url:
                self.links.append((text, url))

    def _selected_row(self):
        rows = self.table.selectionModel().selectedRows()
        if rows:
            return rows[0].row()
        return -1

    def open_selected(self):
        row = self._selected_row()
        if row < 0:
            return
        url = self.table.item(row, 1).text().strip() if self.table.item(row, 1) else ''
        if url:
            from qt.core import QDesktopServices, QUrl
            QDesktopServices.openUrl(QUrl(url))

    def sort_links(self):
        self._read_table()
        self.links.sort(key=lambda item: item[0].lower())
        self._populate_table()

    def add_from_clipboard(self):
        self._read_table()
        clipboard = QApplication.clipboard()
        text = (clipboard.text() or '').strip()
        if not text:
            return

        # Try to parse as markdown link
        parsed = parse_links(text)
        if parsed:
            self.links.extend(parsed)
        else:
            # Treat as a bare URL — use a known-site default text if one
            # matches, otherwise fall back to the URL as both text and link
            self.links.append((default_text_for_url(text), text))
        self._populate_table()

    def add_folder_link(self):
        self._read_table()
        start_dir = self.default_folder_dir or ''
        folder = QFileDialog.getExistingDirectory(self, 'Select Folder', start_dir)
        if not folder:
            return
        uri = path_to_file_uri(folder)
        # Use configured default text, or fall back to folder name
        if self.default_folder_text:
            display = self.default_folder_text
        else:
            display = os.path.basename(folder.rstrip('/\\')) or folder
        self.links.append((display, uri))
        self._populate_table()

    def add_manual(self):
        text = self.new_text_edit.text().strip()
        url = self.new_url_edit.text().strip()
        if not text and not url:
            return
        self._read_table()
        self.links.append((text or url, url or text))
        self._populate_table()
        self.new_text_edit.clear()
        self.new_url_edit.clear()

    def move_up(self):
        row = self._selected_row()
        if row < 1:
            return
        self._read_table()
        self.links[row - 1], self.links[row] = self.links[row], self.links[row - 1]
        self._populate_table()
        self.table.selectRow(row - 1)

    def move_down(self):
        row = self._selected_row()
        if row < 0 or row >= len(self.links) - 1:
            return
        self._read_table()
        self.links[row], self.links[row + 1] = self.links[row + 1], self.links[row]
        self._populate_table()
        self.table.selectRow(row + 1)

    def delete_selected(self):
        row = self._selected_row()
        if row < 0:
            return
        self._read_table()
        self.links.pop(row)
        self._populate_table()
        if self.links:
            self.table.selectRow(min(row, len(self.links) - 1))

    def get_value(self):
        """Return the formatted markdown string to write back to the column."""
        self._read_table()
        return format_links(self.links)


class BulkLinkManagerDialog(QDialog):

    def __init__(self, parent, book_ids, db, col_name):
        QDialog.__init__(self, parent)
        self.setWindowTitle('Link Manager - Bulk Actions (%d books)' % len(book_ids))
        self.resize(QSize(500, 300))
        self.book_ids = book_ids
        self.db = db
        self.db_api = db.new_api if hasattr(db, 'new_api') else db
        self.col_name = col_name
        self.updated_ids = []

        layout = QVBoxLayout(self)
        self.setLayout(layout)

        layout.addWidget(QLabel('<b>%d books selected</b>' % len(book_ids)))
        layout.addWidget(QLabel('Column: <b>%s</b>' % col_name))
        layout.addSpacing(10)

        # Count how many have links
        self.books_with_links = []
        for bid in book_ids:
            val = self.db_api.field_for(col_name, bid) or ''
            links = parse_links(val)
            if links:
                self.books_with_links.append((bid, links))

        layout.addWidget(QLabel('%d of %d books have links in %s' % (
            len(self.books_with_links), len(book_ids), col_name)))
        layout.addSpacing(10)

        # Actions
        layout.addWidget(QLabel('<b>Actions:</b>'))

        self.sort_btn = QPushButton('Sort all links A-Z', self)
        self.sort_btn.setToolTip('Sort links alphabetically by display text for all selected books')
        self.sort_btn.clicked.connect(self.sort_all)
        layout.addWidget(self.sort_btn)

        layout.addStretch()

        # Status
        self.status_label = QLabel('', self)
        layout.addWidget(self.status_label)

        # Dialog buttons
        dialog_btns = QHBoxLayout()
        dialog_btns.addStretch()
        self.close_btn = QPushButton('Close', self)
        self.close_btn.clicked.connect(self.accept)
        dialog_btns.addWidget(self.close_btn)
        layout.addLayout(dialog_btns)

    def sort_all(self):
        count = 0
        for bid, links in self.books_with_links:
            sorted_links = sorted(links, key=lambda item: item[0].lower())
            if sorted_links != links:
                new_val = format_links(sorted_links)
                self.db_api.set_field(self.col_name, {bid: new_val})
                self.updated_ids.append(bid)
                count += 1
        self.status_label.setText('Sorted links for %d book(s).' % count)
