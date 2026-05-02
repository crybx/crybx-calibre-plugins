from __future__ import unicode_literals, division, absolute_import, print_function

__license__ = 'GPL v3'

from calibre.customize import InterfaceActionBase


class AutoUriIdPlugin(InterfaceActionBase):
    name                    = 'AutoUriId'
    description             = ('Make the Edit Metadata "Paste identifier" button use the '
                               'uri: prefix instead of url: when it auto-detects a URL.')
    supported_platforms     = ['windows', 'osx', 'linux']
    author                  = 'crybx'
    version                 = (1, 0, 0)
    minimum_calibre_version = (2, 0, 0)

    actual_plugin = 'calibre_plugins.auto_uri_id.action:AutoUriIdAction'

    def is_customizable(self):
        return False
