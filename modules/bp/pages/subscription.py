# -*- coding: utf-8 -*-

# Copyright(C) 2010-2018 Célande Adrien
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

from __future__ import unicode_literals

import re

from weboob.capabilities.bill import Subscription, Document
from weboob.browser.pages import LoggedPage, HTMLPage
from weboob.browser.filters.standard import CleanText, Regexp, Env, Date, Format, Field
from weboob.browser.filters.html import Link, Attr, TableCell
from weboob.browser.elements import ListElement, ItemElement, method, TableElement


class SubscriptionPage(LoggedPage, HTMLPage):
    # because of freaking JS from hell
    STATEMENT_TYPES = ('RCE', 'RPT', 'RCO')

    @method
    class iter_subscriptions(ListElement):
        item_xpath = '//select[@id="compte"]/option'

        class item(ItemElement):
            klass = Subscription

            obj_id = Regexp(Attr('.', 'value'), r'\w-(\w+)')
            obj_label = CleanText('.')
            obj_subscriber = Env('subscriber')

    @method
    class iter_documents(ListElement):
        def condition(self):
            return not (
                CleanText('//p[contains(text(), "est actuellement indisponible")]')(self)
                or CleanText('//p[contains(text(), "Aucun e-Relevé n\'est disponible")]')(self)
            )

        item_xpath = '//ul[contains(@class, "liste-cpte")]/li'
        # you can have twice the same statement: same month, same subscription
        ignore_duplicate = True

        class item(ItemElement):
            klass = Document

            obj_id = Format('%s_%s%s', Env('sub_id'), Regexp(CleanText('.//a/@title'), r' (\d{2}) '), CleanText('.//span[contains(@class, "date")]' ,symbols='/'))
            obj_label = Format('%s - %s', CleanText('.//span[contains(@class, "lib")]'), CleanText('.//span[contains(@class, "date")]'))
            obj_url = Format('/voscomptes/canalXHTML/relevePdf/relevePdf_historique/%s', Link('./a'))
            obj_format = 'pdf'
            obj_type = 'other'

            def obj_date(self):
                date = CleanText('.//span[contains(@class, "date")]')(self)
                m = re.search(r'(\d{2}/\d{2}/\d{4})', date)
                if m:
                    return Date(CleanText('.//span[contains(@class, "date")]'), dayfirst=True)(self)
                else:
                    return Date(
                        Format(
                            '%s/%s',
                            Regexp(CleanText('.//a/@title'), r' (\d{2}) '),
                            CleanText('.//span[contains(@class, "date")]')
                        ),
                        dayfirst=True
                    )(self)

    def get_params(self, sub_label):
        # the id is in the label
        sub_value = Attr('//select[@id="compte"]/option[contains(text(), "%s")]' % sub_label, 'value')(self.doc)

        form = self.get_form(name='formulaireHistorique')
        form['formulaire.numeroCompteRecherche'] = sub_value
        return form

    def get_years(self):
        return self.doc.xpath('//select[@id="annee"]/option/@value')

    def has_error(self):
        return (
            CleanText('//p[contains(text(), "est actuellement indisponible")]')(self.doc)
            or CleanText('//p[contains(text(), "Aucun e-Relevé n\'est disponible")]')(self.doc)
        )


class DownloadPage(LoggedPage, HTMLPage):
    def get_content(self):
        if self.doc.xpath('//iframe'):
            # the url has the form
            # ../relevePdf_telechargement/affichagePDF-telechargementPDF.ea?date=XXX
            part_link = Attr('//iframe', 'src')(self.doc).replace('..', '')
            return self.browser.open('/voscomptes/canalXHTML/relevePdf%s' % part_link).content
        return self.content

class ProSubscriptionPage(LoggedPage, HTMLPage):
    @method
    class iter_subscriptions(ListElement):
        item_xpath = '//select[@id="numeroCompteRechercher"]/option'

        class item(ItemElement):
            klass = Subscription

            obj_label = CleanText('.')
            obj_id = Regexp(Field('label'), r'\w? ?- (\w+)')
            obj_subscriber = Env('subscriber')
            obj__number = Attr('.', 'value')

    @method
    class iter_documents(TableElement):
        item_xpath = '//table[@id="relevesPDF"]//tr[td]'
        head_xpath = '//table[@id="relevesPDF"]//th'
        # may have twice the same statement for a given month
        ignore_duplicate = True

        col_date = re.compile('Date du relevé')
        col_label = re.compile('Type de document')

        class item(ItemElement):
            klass = Document

            obj_date = Date(CleanText(TableCell('date')), dayfirst=True)
            obj_label = Format('%s %s', CleanText(TableCell('label')), CleanText(TableCell('date')))
            obj_id = Format('%s_%s', Env('sub_id'), CleanText(TableCell('date'), symbols='/'))
            # the url uses an id depending on the page where the document is
            # by example, if the id is 0,
            # it means that it is the first document that you can find
            # on the page of the year XXX for the subscription YYYY
            obj_url = Link('.//a')
            obj_format = 'pdf'
            obj_type = 'other'

    def submit_form(self, sub_number, year):
        form = self.get_form(name='formRechHisto')

        form['historiqueReleveParametre.numeroCompteRecherche'] = sub_number
        form['typeRecherche'] = 'annee'
        form['anneeRechercheDefaut'] = year

        form.submit()

    def get_years(self):
        return self.doc.xpath('//select[@name="anneeRechercheDefaut"]/option/@value')

    def no_statement(self):
        return self.doc.xpath('//p[has-class("noresult")]')

    def has_document(self, date):
        return self.doc.xpath('//td[@headers="dateReleve" and contains(text(), "%s")]' % date.strftime('%d/%m/%Y'))

    def get_sub_number(self, doc_id):
        sub_id = doc_id.split('_')[0]
        return Attr('//select[@id="numeroCompteRechercher"]/option[contains(text(), "%s")]' % sub_id, 'value')(self.doc)
