from __future__ import unicode_literals, division, absolute_import, print_function

__license__ = 'GPL v3'

try:
    from qt.core import QDialogButtonBox, QIcon
except ImportError:
    from PyQt5.Qt import QDialogButtonBox, QIcon

from calibre.gui2.fts.dialog import FTSDialog


class FrozenFtsDialog(FTSDialog):
    """FTSDialog that always opens straight to the results panel.

    The stock dialog routes to ScanStatus when indexing is disabled (or below
    completion threshold). This plugin's whole point is to search without
    enabling indexing, so we skip that gate.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # Geometry name is inherited from FTSDialog so we share window size with
        # the stock dialog. If you want them tracked separately, override here.
        self.setWindowTitle(_('Search frozen full text'))
        self.setWindowIcon(QIcon.ic('fts.png'))

    def show_appropriate_panel(self):
        # Always show results — never the "enable indexing" panel.
        self.show_results_panel()

    def show_results_panel(self):
        super().show_results_panel()
        # ResultsPanel.specialize_button_box adds a "Show indexing status"
        # button that switches to ScanStatus. Strip it so users don't
        # accidentally toggle indexing on from this dialog.
        bb = self.bb
        bb.clear()
        bb.addButton(QDialogButtonBox.StandardButton.Close)
