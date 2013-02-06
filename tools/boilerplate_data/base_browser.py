<%inherit file="layout.py"/>
from weboob.tools.browser import BaseBrowser


__all__ = ['${r.classname}Browser']


class ${r.classname}Browser(BaseBrowser):
    PROTOCOL = 'http'
    DOMAIN = 'www.${r.name}.com'
    ENCODING = None

    PAGES = {}
