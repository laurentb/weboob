# -*- coding: utf-8 -*-

# Copyright(C) 2012 Lucien Loiseau
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.


from weboob.tools.browser import BaseBrowser, BrowserHTTPNotFound, BrowserIncorrectPassword
from weboob.tools.browser.decorators import id2url, check_url
from weboob.capabilities.translate import TranslationFail

from .pages import TranslatePage

import urllib

__all__ = ['GoogleTranslateBrowser']

class GoogleTranslateBrowser(BaseBrowser):
    DOMAIN = 'translate.google.com'
    ENCODING = 'UTF-8'
    USER_AGENT = BaseBrowser.USER_AGENTS['desktop_firefox']
    PAGES = {
        'https?://translate\.google\.com': TranslatePage
        }

    def __init__(self, *args, **kwargs):
        BaseBrowser.__init__(self, *args, **kwargs)

    def translate(self, source, to, text):
        """
        translate 'text' from 'source' language to 'to' language
        """
        try:
          d = {
              'sl': source, 
              'tl': to,
              'js': 'n',
              'prev': '_t',
              'hl': 'en',
              'ie': 'UTF-8',
              'layout': '2',
              'eotf': '1',
              'text': text,
              }
          self.location('http://'+self.DOMAIN, urllib.urlencode(d))
          translation = self.page.get_translation()
          return translation

        except TranslationFail:
            return "no translation available"

