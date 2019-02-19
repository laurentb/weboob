<%inherit file="layout.pyt"/>
from weboob.tools.capabilities.gallery.genericcomicreadertest import GenericComicReaderTest


class ${r.classname}BackendTest(GenericComicReaderTest):
    MODULE = '${r.name}'

    def test_download(self):
        return self._test_download('${r.download_id}')
