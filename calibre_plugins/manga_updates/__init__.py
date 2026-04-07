from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'

from calibre.customize import InterfaceActionBase

class ActionMangaUpdates(InterfaceActionBase):
    name                    = 'MangaUpdates'
    description             = 'Download metadata from mangaupdates.com'
    supported_platforms     = ['windows', 'osx', 'linux']
    author                  = 'crybx'
    version                 = (1, 0, 0)
    minimum_calibre_version = (2, 85, 1)

    actual_plugin           = 'calibre_plugins.manga_updates.action:MangaUpdatesAction'

    def is_customizable(self):
        return True

    def config_widget(self):
        if self.actual_plugin_:
            from calibre_plugins.manga_updates.config import ConfigWidget
            return ConfigWidget(self.actual_plugin_)

    def save_settings(self, config_widget):
        config_widget.save_settings()
