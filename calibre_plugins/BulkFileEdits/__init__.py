from calibre.customize import EditBookToolPlugin


class BulkFileEditsPlugin(EditBookToolPlugin):

    name = 'BulkFileEdits'
    version = (1, 1, 0)
    author = 'epubaholic'
    supported_platforms = ['windows', 'osx', 'linux']
    description = 'Bulk file operations: rename by chapter content, sort spine, insert headers, delete matching files'
    minimum_calibre_version = (1, 46, 0)
