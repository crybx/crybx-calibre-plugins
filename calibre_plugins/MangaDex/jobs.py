from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'

try:
    from qt.core import QThread, pyqtSignal
except ImportError:
    from PyQt5.Qt import QThread, pyqtSignal

from calibre_plugins.mangadex.scraper import fetch_md_metadata


class FetchWorker(QThread):
    '''Worker thread that fetches metadata for a list of books from MangaDex.'''

    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(dict)

    def __init__(self, books_data, parent=None):
        QThread.__init__(self, parent)
        self.books_data = books_data
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

        for i, (book_id, title, manga_id) in enumerate(self.books_data):
            if self._abort:
                break
            self.progress.emit(i, total, title)

            if manga_id:
                log = SimpleLog()
                data = fetch_md_metadata(manga_id, log=log)
                if data is None:
                    data = {}
                data['_log'] = log.lines
                data['_manga_id'] = manga_id
                data['_url'] = 'https://mangadex.org/title/%s' % manga_id
                data['_failed'] = not bool(data.get('title'))
                results[book_id] = data
            else:
                results[book_id] = {
                    '_failed': True,
                    '_log': ['No MangaDex URL found for this book'],
                    '_manga_id': None,
                    '_url': None,
                }

        self.finished.emit(results)
