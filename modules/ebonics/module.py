# -*- coding: utf-8 -*-

# Copyright(C) 2012-2018  Romain Bignon, Laurent Bachelier
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


from weboob.browser import URL, PagesBrowser
from weboob.browser.filters.html import FormValue
from weboob.browser.pages import HTMLPage
from weboob.capabilities.translate import CapTranslate, LanguageNotSupported, Translation, TranslationFail
from weboob.tools.backend import Module

__all__ = ['EbonicsModule']


class TranslatorPage(HTMLPage):
    def get_text(self):
        return FormValue('//textarea[@name="Ebonics"]')(self.doc)


class Ebonics(PagesBrowser):
    translator = URL('http://joel.net/EBONICS/Translator', TranslatorPage)

    def translate(self, text):
        return self.open(self.translator.build(),
                         data={'English': text},
                         data_encoding='UTF-8').page.get_text()


class EbonicsModule(Module, CapTranslate):
    NAME = 'ebonics'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '2.0'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u'English to Ebonics translation service'
    BROWSER = Ebonics

    def translate(self, lan_from, lan_to, text):
        if lan_from != 'English' or lan_to != 'Nigger!':
            raise LanguageNotSupported()

        translated_text = self.browser.translate(text)
        if not translated_text:
            raise TranslationFail()

        translation = Translation(0)
        translation.lang_src = lan_from
        translation.lang_dst = lan_to
        translation.text = translated_text

        return translation
