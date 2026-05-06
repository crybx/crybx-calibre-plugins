from __future__ import unicode_literals, division, absolute_import, print_function

__license__ = 'GPL v3'

from calibre.customize import InterfaceActionBase


class FrozenFtsPlugin(InterfaceActionBase):
    name                    = 'Frozen FTS'
    description             = ('Search the existing full-text-search.db without enabling Calibre\'s '
                               'live indexing. Lets you query a previously-built FTS index without '
                               'paying the ongoing indexing cost.')
    supported_platforms     = ['windows', 'osx', 'linux']
    author                  = 'crybx'
    version                 = (0, 1, 0)
    minimum_calibre_version = (6, 0, 0)

    actual_plugin = 'calibre_plugins.frozen_fts.action:FrozenFtsAction'

    def is_customizable(self):
        return False
