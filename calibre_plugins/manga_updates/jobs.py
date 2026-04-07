from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'

'''
Background thread worker for fetching MangaUpdates metadata.
Uses QThread so network I/O doesn't block the GUI.
'''

try:
    from qt.core import QThread, pyqtSignal
except ImportError:
    from PyQt5.Qt import QThread, pyqtSignal

from calibre_plugins.manga_updates.scraper import fetch_mu_metadata


class FetchWorker(QThread):
    '''
    Worker thread that fetches metadata for a list of books from MU.

    books_data: list of (book_id, title, mu_url)  — mu_url may be None
    '''

    # Emitted after each book is processed: (current_index, total, book_title)
    progress = pyqtSignal(int, int, str)
    # Emitted when all done: dict mapping book_id → (mu_data | None)
    finished = pyqtSignal(dict)

    def __init__(self, books_data, user_agent=None, parent=None):
        QThread.__init__(self, parent)
        self.books_data = books_data
        self.user_agent = user_agent
        self._abort = False

    def abort(self):
        self._abort = True

    def run(self):
        results = {}
        total = len(self.books_data)

        class SimpleLog:
            def __init__(self):
                self.lines = []
            def __call__(self, msg):
                self.lines.append(str(msg))

        for i, (book_id, title, mu_url) in enumerate(self.books_data):
            if self._abort:
                break
            self.progress.emit(i, total, title)

            if mu_url:
                log = SimpleLog()
                data = fetch_mu_metadata(mu_url, user_agent=self.user_agent, log=log)
                if data is None:
                    data = {}
                data['_log'] = log.lines
                data['_url'] = mu_url
                data['_failed'] = not bool(data.get('title'))
                results[book_id] = data
            else:
                results[book_id] = {'_failed': True, '_log': ['No MangaUpdates URL found for this book'], '_url': None}

        self.finished.emit(results)
