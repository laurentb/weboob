# -*- coding: utf-8 -*-

# Copyright(C) 2012  Romain Bignon
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



from weboob.capabilities.translate import CapTranslate, Translation, TranslationFail, LanguageNotSupported
from weboob.tools.backend import Module
from weboob.tools.compat import urlencode
from weboob.deprecated.browser import StandardBrowser


__all__ = ['EbonicsModule']


class EbonicsModule(Module, CapTranslate):
    NAME = 'ebonics'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '1.3'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u'English to Ebonics translation service'
    BROWSER = StandardBrowser

    def translate(self, lan_from, lan_to, text):
        if lan_from != 'English' or lan_to != 'Nigger!':
            raise LanguageNotSupported()

        with self.browser:
            data = {'English': text.encode('utf-8')}
            doc = self.browser.location('http://joel.net/EBONICS/Translator', urlencode(data))
            try:
                text = doc.getroot().cssselect('div.translateform div.bubble1 div.bubblemid')[0].text
            except IndexError:
                raise TranslationFail()

        if text is None:
            raise TranslationFail()

        translation = Translation(0)
        translation.lang_src = unicode(lan_from)
        translation.lang_dst = unicode(lan_to)
        translation.text = unicode(text).strip()

        return translation
