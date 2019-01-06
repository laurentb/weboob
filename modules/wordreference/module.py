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
"backend for http://www.wordreference.com"


from weboob.capabilities.translate import CapTranslate, TranslationFail, LanguageNotSupported
from weboob.tools.backend import Module

from .browser import WordReferenceBrowser


__all__ = ['WordReferenceModule']


class WordReferenceModule(Module, CapTranslate):
    MAINTAINER = u'Lucien Loiseau'
    EMAIL = 'loiseau.lucien@gmail.com'
    VERSION = '1.5'
    LICENSE = 'AGPLv3+'
    NAME = 'wordreference'
    DESCRIPTION = u'Free online translator'
    BROWSER = WordReferenceBrowser
    WRLANGUAGE = {
        'Arabic': 'ar', 'Chinese': 'zh', 'Czech': 'cz', 'English': 'en', 'French': 'fr', 'Greek': 'gr',
        'Italian': 'it', 'Japanese': 'ja', 'Korean': 'ko', 'Polish': 'pl', 'Portuguese': 'pt',
        'Romanian': 'ro', 'Spanish': 'es', 'Turkish': 'tr',
        }

    def translate(self, lan_from, lan_to, text):
        if lan_from not in self.WRLANGUAGE.keys():
            raise LanguageNotSupported()

        if lan_to not in self.WRLANGUAGE.keys():
            raise LanguageNotSupported()

        translations = self.browser.translate(self.WRLANGUAGE[lan_from], self.WRLANGUAGE[lan_to], text)
        has_translation = False

        for translation in translations:
            has_translation = True
            yield translation

        if not has_translation:
            raise TranslationFail()
