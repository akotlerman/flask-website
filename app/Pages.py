from flask import abort
from werkzeug.utils import cached_property
import os


def force_unicode(value, encoding='utf-8', errors='strict'):
    """
    Convert bytes or any other Python instance to string.
    """
    if isinstance(value, str):
        return value
    return value.decode(encoding, errors)


class Page(object):
    def __init__(self, path, html):
        self.html = html
        self.path = path


class Pages(object):
    def __init__(self, app=None):
        self.app = app
        self.pages = {}
        self._file_cache = {}
        self.extension = '.html'
        self.encoding = 'utf-8'
        self.root_folder = 'pages'
        self.debug = True
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.app = app
        self.debug = app.debug
        self.root_folder = app.config.get('PAGES_ROOT', 'pages')
        if self.debug:
            print(self._pages)

    @property
    def root(self):
        """Full path to the directory where pages are looked for.

        This corresponds to the `FLATPAGES_%(name)s_ROOT` config value,
        interpreted as relative to the app's root directory.
        """
        root_dir = os.path.join(self.app.root_path, self.root_folder)
        return force_unicode(root_dir)

    @cached_property
    def _pages(self):
        """Walk the page root directory an return a dict of unicode path:
        page object.
        """

        def _walker():
            """
            Walk over directory and find all possible flatpages, i.e. files
            which end with the string or sequence given by
            ``PAGES_%(name)s_EXTENSION``.
            """
            results = {}

            for cur_path, cur_dir, filenames in os.walk(self.root):
                rel_path = cur_path.replace(self.root, '').lstrip(os.sep)
                path_prefix = tuple(rel_path.split(os.sep)) if rel_path else ''

                for name in filenames:
                    if not name.endswith(extension):
                        continue

                    if path_prefix and rel_path not in results:
                        results[rel_path] = {}

                    full_name = os.path.join(cur_path, name)
                    name_without_extension = [name[:-len(item)]
                                              for item in extension
                                              if name.endswith(item)][0]
                    page = self._load_file(path_prefix + (name_without_extension,), full_name)
                    results[rel_path][name_without_extension] = page
            return results

        extension = self.extension

        # Support for multiple extensions
        if isinstance(extension, str):
            if ',' in extension:
                extension = tuple(extension.split(','))
            else:
                extension = (extension,)
        elif isinstance(extension, (list, set)):
            extension = tuple(extension)

        # FlatPage extension should be a string or a sequence
        if not isinstance(extension, tuple):
            raise ValueError(
                'Invalid value for Pages extension. Should be a string or '
                'a sequence, got {0} instead: {1}'.format(type(extension).__name__, extension)
            )

        result = _walker()
        # result = dict([(path, self._load_file(path, full_name))
        #             for path, full_name in _walker()])

        if self.debug:
            print(result)

        return result

    def get_or_404(self, folder, page=None):
        """Returns the :class:`Page` object at ``path``, or raise Flask's
        404 error if there is no such page.
        """
        page = self.get(folder, page)
        if not page:
            abort(404)
        return page

    def get(self, folder, page=None, default=None):
        """Returns the :class:`Page` object at ``path``, or ``default`` if
        there is no such page.
        """
        # This may trigger the property. Do it outside of the try block.
        pages = self._pages
        try:
            if page is None:
                return pages[folder]
            else:
                return pages[folder][page]
        except KeyError:
            return default

    def _load_file(self, path, filename):
        """Load file from file system and put it to cached dict as
        :class:`Path` and `mtime` tuple.
        """
        mtime = os.path.getmtime(filename)
        cached = self._file_cache.get(filename)

        if cached and cached[1] == mtime:
            page = cached[0]
        else:
            encoding = self.encoding

            with open(filename, encoding=encoding) as handler:
                content = handler.read()

            page = Page(path, content)
            self._file_cache[filename] = (page, mtime)

        return page
