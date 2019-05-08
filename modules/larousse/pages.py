# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
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

from __future__ import unicode_literals

import re

from weboob.capabilities.translate import Translation
from weboob.browser.elements import method, ListElement, ItemElement
from weboob.browser.filters.standard import Env, CleanText
from weboob.browser.pages import HTMLPage

CODES = {
    'allemand': 'de',
    'anglais': 'en',
    'arabe': 'ar',
    'chinois': 'zh',
    'espagnol': 'es',
    'francais': 'fr',
    'italien': 'it',
}

RCODES = {v: k for k, v in CODES.items()}

class LangList(HTMLPage):
    def get_langs(self):
        res = {}
        for a in self.doc.xpath('//a[@class="item-dico-bil"]'):
            url = a.attrib['href']
            mtc = re.search(r'/dictionnaires/(\w+)-(\w+)', url)
            if not mtc:
                continue
            src, dst = mtc.groups()
            res[CODES[src], CODES[dst]] = (src, dst)
        return res


class WordPage(HTMLPage):
    @method
    class iter_translations(ListElement):
        #~ item_xpath = '//span[@class="Traduction"]//a[@class="lienarticle2"]'
        item_xpath = '//span[has-class("Traduction") or has-class("Traduction2")][@lang]'

        class item(ItemElement):
            klass = Translation

            def condition(self):
                # ignore sub-translations
                parent = self.el.getparent()
                if parent.attrib.get('class', '') in ('Traduction', 'Traduction2'):
                    return False

                if self.el.xpath('./ancestor::div[@class="BlocExpression" or @class="ZoneExpression"]'):
                    # example: http://larousse.fr/dictionnaires/francais-anglais/maison/48638
                    return False

                # ignore idioms translations
                for sibling in self.el.xpath('./preceding-sibling::*')[::-1]:
                    if sibling.tag == 'br':
                        return True
                    if sibling.tag == 'span' and sibling.attrib.get('class', '') == 'Locution2':
                        return False
                    # TODO handle RTL text which is put in a sub div
                return True

            obj_lang_src = Env('src')
            obj_lang_dst = Env('dst')

            def obj_text(self):
                return re.sub(',', '', CleanText('.')(self)).strip()
