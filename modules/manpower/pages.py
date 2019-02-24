# -*- coding: utf-8 -*-

# Copyright(C) 2016      Bezleputh
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
from datetime import date

from weboob.browser.pages import HTMLPage
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.filters.standard import CleanText, Regexp, Env, BrowserURL, Date, Format
from weboob.browser.filters.html import CleanHTML
from weboob.capabilities.job import BaseJobAdvert
from weboob.capabilities.base import NotAvailable


class SearchPage(HTMLPage):
    @method
    class iter_job_adverts(ListElement):
        item_xpath = '//div[has-class("item")]'

        class item(ItemElement):
            klass = BaseJobAdvert

            obj_id = Regexp(CleanText('./div/a[@class="title-link"]/@href'),
                            '/candidats/detail-offre-d-emploi/(.*).html')
            obj_title = CleanText('./div/a[@class="title-link"]/h2')

            def obj_place(self):
                content = CleanText('./div[2]')(self)
                if len(content.split('|')) > 1:
                    return content.split('|')[1]
                return ''

            def obj_publication_date(self):
                content = CleanText('./div[2]')(self)
                split_date = content.split('|')[0].split('/')
                if len(split_date) == 3:
                    return date(int(split_date[2]) + 2000, int(split_date[1]), int(split_date[0]))
                return ''


class AdvertPage(HTMLPage):
    @method
    class get_job_advert(ItemElement):
        klass = BaseJobAdvert

        obj_id = Env('_id')
        obj_url = BrowserURL('advert_page', _id=Env('_id'))
        obj_title = CleanText('//div[@class="infos-lieu"]/h1')
        obj_place = CleanText('//div[@class="infos-lieu"]/h2')
        obj_publication_date = Date(Regexp(CleanText('//div[@class="info-agency"]'), '.*Date de l\'annonce :(.*)',
                                           default=''))
        obj_job_name = CleanText('//div[@class="infos-lieu"]/h1')
        obj_description = Format('\n%s%s',
                                 CleanHTML('//article[@id="post-description"]/div'),
                                 CleanHTML('//article[@id="poste"]'))
        obj_contract_type = Regexp(CleanText('//article[@id="poste"]/div/ul/li'),
                                   'Contrat : (\w*)', default=NotAvailable)
        obj_pay = Regexp(CleanText('//article[@id="poste"]/div/ul/li'),
                         'Salaire : (.*) par mois', default=NotAvailable)
        obj_experience = Regexp(CleanText('//article[@id="poste"]/div/ul/li'),
                                u'Expérience : (.* ans)', default=NotAvailable)
