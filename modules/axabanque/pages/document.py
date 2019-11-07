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
from weboob.browser.filters.standard import CleanText, Env, Regexp, Format, Date
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.capabilities.bill import Document
from weboob.tools.date import parse_french_date


class DocumentsPage(LoggedPage, HTMLPage):
    @method
    class get_documents(ListElement):
        item_xpath = '//div[has-class("mawa-cards-item dashboard-item")]'

        class item(ItemElement):
            klass = Document

            obj_id = Format(
                '%s_%s',
                Env('subid'),
                Regexp(CleanText('./@data-module-open-link--link'), '#/details/(.*)'),
            )
            obj_format = 'pdf'
            # eg when formatted (not complete list):
            # - Situation de contrat suite à réajustement automatique Assurance Vie N° XXXXXXXXXX
            # - Lettre d'information client Assurance Vie N° XXXXXXXXXX
            # - Attestation de rachat partiel Assurance Vie N° XXXXXXXXXXXXXX
            obj_label = Format(
                '%s %s %s',
                CleanText('.//h3[@class="card-title"]'),
                CleanText('.//div[@class="sticker-content"]//strong'),
                CleanText('.//p[@class="contract-info"]'),
            )
            obj_date = Date(CleanText('.//p[@class="card-date"]'), parse_func=parse_french_date)
            obj_type = 'document'
            obj__download_id = Regexp(CleanText('./@data-url'), r'.did_(.*?)\.')


class DownloadPage(LoggedPage, HTMLPage):
    def create_document(self):
        form = self.get_form(xpath='//form[has-class("form-download-pdf")]')
        form.submit()
