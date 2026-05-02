from __future__ import unicode_literals, division, absolute_import, print_function

__license__ = 'GPL v3'

try:
    from qt.core import QApplication
except ImportError:
    from PyQt5.Qt import QApplication

from calibre.gui2 import gprefs
from calibre.gui2.actions import InterfaceAction
from calibre.gui2.metadata.basic_widgets import IdentifiersEdit


_PATCHED_FLAG = '_auto_uri_id_patched'


def _patched_paste_identifier(self):
    # Mirror of calibre.gui2.metadata.basic_widgets.IdentifiersEdit.paste_identifier,
    # changing only the auto-detected URL prefix from 'url' to 'uri'. Re-sync this body
    # from the Calibre source whenever the upstream method changes.
    if self.parse_clipboard_for_identifier():
        return
    text = str(QApplication.clipboard().text()).strip()
    if text.startswith(('http://', 'https://')):
        return self.paste_prefix('uri')
    try:
        prefix = gprefs['paste_isbn_prefixes'][0]
    except IndexError:
        prefix = 'isbn'
    self.paste_prefix(prefix)


class AutoUriIdAction(InterfaceAction):
    name = 'AutoUriId'
    action_spec = ('AutoUriId', None,
                   'Auto-paste identifier uses uri: instead of url:', None)
    action_type = 'global'
    # Don't surface anywhere — this plugin only patches GUI behavior at startup.
    dont_add_to = frozenset(['toolbar', 'toolbar-device', 'toolbar-child',
                             'menubar', 'menubar-device',
                             'context-menu', 'context-menu-device',
                             'context-menu-cover-browser', 'context-menu-split',
                             'searchbar'])

    def genesis(self):
        if not getattr(IdentifiersEdit, _PATCHED_FLAG, False):
            IdentifiersEdit.paste_identifier = _patched_paste_identifier
            setattr(IdentifiersEdit, _PATCHED_FLAG, True)
