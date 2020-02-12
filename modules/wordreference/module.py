# -*- coding: utf-8 -*-

# Copyright(C) 2012 Lucien Loiseau
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
"backend for http://www.wordreference.com"


from weboob.capabilities.translate import CapTranslate, TranslationFail, LanguageNotSupported
from weboob.tools.backend import Module

from .browser import WordReferenceBrowser


__all__ = ['WordReferenceModule']


class WordReferenceModule(Module, CapTranslate):
    MAINTAINER = u'Lucien Loiseau'
    EMAIL = 'loiseau.lucien@gmail.com'
    VERSION = '2.1'
    LICENSE = 'AGPLv3+'
    NAME = 'wordreference'
    DESCRIPTION = u'Free online translator'
    BROWSER = WordReferenceBrowser
    WRLANGUAGE = [
        'ar',
        'zh',
        'cz',
        'en',
        'fr',
        'gr',
        'it',
        'ja',
        'ko',
        'pl',
        'pt',
        'ro',
        'es',
        'tr',
    ]

    def translate(self, lan_from, lan_to, text):
        if lan_from not in self.WRLANGUAGE:
            raise LanguageNotSupported()

        if lan_to not in self.WRLANGUAGE:
            raise LanguageNotSupported()

        translations = self.browser.translate(lan_from, lan_to, text)
        has_translation = False

        for translation in translations:
            has_translation = True
            yield translation

        if not has_translation:
            raise TranslationFail()
