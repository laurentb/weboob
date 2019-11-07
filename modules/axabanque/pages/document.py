# -*- coding: utf-8 -*-

# Copyright(C) 2010-2017 Théo Dorée
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.filters.standard import CleanText, Env, Regexp, Format
from weboob.browser.elements import ListElement, ItemElement, method, SkipItem
from weboob.capabilities.bill import Document
from weboob.tools.compat import urljoin


class DocumentsPage(LoggedPage, HTMLPage):
    @method
    class get_documents(ListElement):
        item_xpath = '//article'

        class item(ItemElement):
            klass = Document

            obj_id = Format(
                '%s_%s',
                Env('subid'),
                Regexp(CleanText('./@data-route'), '#/details/(.*)'),
            )
            obj_format = 'pdf'
            obj_label = CleanText('.//h2')
            obj_type = 'document'

            def obj_url(self):
                url = urljoin(self.page.browser.BASEURL, CleanText('./@data-url')(self))
                self.page.browser.location(url)
                if self.page.doc.xpath('//form[contains(., "Afficher")]'):
                    return url
                raise SkipItem()


class DownloadPage(LoggedPage, HTMLPage):
    def create_document(self):
        form = self.get_form(xpath='//form[contains(., "Afficher")]')
        form.submit()
