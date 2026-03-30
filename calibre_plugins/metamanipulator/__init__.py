from calibre.customize import InterfaceActionBase


class ActionMetaManipulator(InterfaceActionBase):

    name = 'MetaManipulator'
    version = (1, 0, 0)
    author = 'epubaholic'
    description = 'Bulk metadata manipulation for any book format'
    supported_platforms = ['windows', 'osx', 'linux']
    minimum_calibre_version = (5, 0, 0)
    actual_plugin = 'calibre_plugins.metamanipulator.action:MetaManipulatorAction'
