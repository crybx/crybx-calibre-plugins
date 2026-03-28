from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'

from calibre.customize import InterfaceActionBase

class ActionLinkManager(InterfaceActionBase):
    name                    = 'Link Manager'
    description             = 'Manage markdown links in a custom column'
    supported_platforms     = ['windows', 'osx', 'linux']
    author                  = 'crybx'
    version                 = (1, 0, 0)
    minimum_calibre_version = (2, 85, 1)

    actual_plugin           = 'calibre_plugins.linkmanager.action:LinkManagerAction'

    def is_customizable(self):
        return True

    def config_widget(self):
        if self.actual_plugin_:
            from calibre_plugins.linkmanager.config import ConfigWidget
            return ConfigWidget(self.actual_plugin_)

    def save_settings(self, config_widget):
        config_widget.save_settings()
