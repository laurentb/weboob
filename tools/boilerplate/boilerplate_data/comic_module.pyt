<%inherit file="layout.pyt"/>
from weboob.tools.capabilities.gallery.genericcomicreader import GenericComicReaderModule, DisplayPage


__all__ = ['${r.classname}Module']


class ${r.classname}Module(GenericComicReaderModule):
    NAME = '${r.name}'
    DESCRIPTION = u'${r.name} manga reading site'
    MAINTAINER = u'${r.author}'
    EMAIL = '${r.email}'
    VERSION = '${r.version}'
    LICENSE = 'LGPLv3+'

    DOMAIN = 'www.${r.name}.com'
    BROWSER_PARAMS = dict(
        img_src_xpath="//img[@id='comic_page']/@src",
        page_list_xpath="(//select[@id='page_select'])[1]/option/@value")
    ID_REGEXP = r'[^/]+/[^/]+'
    URL_REGEXP = r'.+${r.name}.com/(%s).+' % ID_REGEXP
    ID_TO_URL = 'http://www.${r.name}.com/%s'
    PAGES = {URL_REGEXP: DisplayPage}
