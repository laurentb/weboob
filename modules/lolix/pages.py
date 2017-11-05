# -*- coding: utf-8 -*-

# Copyright(C) 2013      Bezleputh
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


from weboob.browser.pages import HTMLPage
from weboob.browser.elements import TableElement, ItemElement, method
from weboob.browser.filters.standard import CleanText, Regexp, Date, Env, BrowserURL, Join, Format
from weboob.browser.filters.html import CleanHTML, TableCell
from weboob.capabilities.job import BaseJobAdvert


class AdvertPage(HTMLPage):
    @method
    class get_job_advert(ItemElement):
        klass = BaseJobAdvert

        obj_id = Env('id')
        obj_url = BrowserURL('advert_page', id=Env('id'))
        obj_society_name = CleanText('//td[@class="Contenu"]/table[4]/tr[1]/td[1]/a')
        obj_title = CleanText('//td[@class="Titre15"]')

        obj_description = Format('%s\n%s',
                                 Join('\n', u'//td[@class="Contenu"]/table[3]/tr[td/text()="Détails :"]/following-sibling::tr',
                                      textCleaner=CleanHTML),
                                 CleanHTML('//td[@class="Contenu"]/table[2]'))

        obj_job_name = CleanText(u'//td[@class="Contenu"]/table[3]/tr/td[text()="Poste :"]/following-sibling::td',
                                 replace=[(u'-- Indifférent --', u'')])

        obj_contract_type = CleanText(CleanHTML(u'//td[@class="Contenu"]/table[3]/tr/td[text()="Contrat :"]/following-sibling::td',
                                                default=u''),
                                      replace=[(u'-- Indifférent --', u'')])

        obj_pay = CleanText(u'//td[@class="Contenu"]/table[3]/tr/td[contains(text(), "Rémunération")]/following-sibling::td',
                            default=u'')

        obj_place = CleanText(u'//td[@class="Contenu"]/table[3]/tr/td[contains(text(), "Région")]/following-sibling::td',
                              default=u'',
                              replace=[(u'-- Indifférent --', u''),
                                       (u'Lieu de travail : ', u'')])


class SearchPage(HTMLPage):
    @method
    class iter_job_adverts(TableElement):
        item_xpath = '//td[@class="Contenu"]/table/tr[position() > 1]'
        head_xpath = '//td[@class="Contenu"]/table/tr/td[@class="ListeTitre"]/text()'

        col_date = u'Date'
        col_societe = u'Société'
        col_titre = u'Titre'
        col_region = u'Région'

        class Item(ItemElement):
            klass = BaseJobAdvert

            def obj_id(self):
                return Regexp(CleanText('./a/@href'),
                              r'offre.php\?id=(.*)')(TableCell('titre')(self)[0])

            obj_publication_date = Date(CleanText(TableCell('date')))
            obj_society_name = CleanText(TableCell('societe'))
            obj_title = CleanText(TableCell('titre'))
            obj_place = CleanText(TableCell('region'))

            def validate(self, obj):
                if self.env['pattern'] is None or self.env['pattern'].upper() in obj.title.upper():
                    return obj
