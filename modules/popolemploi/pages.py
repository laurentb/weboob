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

from weboob.capabilities.job import BaseJobAdvert
from weboob.browser.pages import HTMLPage
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.filters.standard import Regexp, CleanText, Env, BrowserURL, Filter, Join
from weboob.browser.filters.html import XPath


import re
from datetime import datetime, timedelta


class PoleEmploiDate(Filter):
    def filter(self, el):
        days = 0
        if el == u'Publié aujourd\'hui':
            days = 0
        elif el == u'Publié hier':
            days = 1
        else:
            m = re.search(u'Publié il y a (\d*) jours', el)
            if m:
                days = int(m.group(1))

        return datetime.now() - timedelta(days=days)


class SearchPage(HTMLPage):
    @method
    class iter_job_adverts(ListElement):
        item_xpath = '//ul[has-class("result-list")]/li'

        class item(ItemElement):
            klass = BaseJobAdvert

            obj_id = CleanText('./@data-id-offre')
            obj_contract_type = CleanText('./div/div/p[@class="contrat"]')
            obj_title = CleanText('./div/div/h2')
            obj_society_name = CleanText('./div/div/p[@class="subtext"]',
                                         children=False, replace=[('-', '')])
            obj_place = CleanText('./div/div/p[@class="subtext"]/span')
            obj_publication_date = PoleEmploiDate(CleanText('./div/div/p[@class="date"]'))


class AdvertPage(HTMLPage):
    @method
    class get_job_advert(ItemElement):
        klass = BaseJobAdvert

        obj_id = Env('id')
        obj_url = BrowserURL('advert', id=Env('id'))
        obj_title = CleanText('//div[@class="modal-body"]/h2')
        obj_job_name = CleanText('//div[@class="modal-body"]/h2')
        obj_description = CleanText('//div[has-class("description")]/p')
        obj_society_name = CleanText('//div[@class="media-body"]/h4')
        obj_experience = Join(u'- ',
                              '//h4[contains(text(), "Exp")]/following-sibling::ul[has-class("skill-list")][1]/li',
                              newline=True,
                              addBefore='\n- ')
        obj_formation = Join(u'- ',
                             '//h4[contains(text(), "For")]/following-sibling::ul[has-class("skill-list")][1]/li',
                             newline=True,
                             addBefore='\n- ')

        obj_place = CleanText('//div[@class="modal-body"]/h2/following-sibling::p[1]')
        obj_publication_date = PoleEmploiDate(CleanText('//div[@class="modal-body"]/h2/following-sibling::p[2]'))

        def parse(self, el):
            for el in XPath('//dl[@class="icon-group"]/dt')(el):
                dt = CleanText('.')(el)
                if dt == u'Type de contrat':
                    self.obj.contract_type = CleanText('./following-sibling::dd[1]')(el)
                elif dt == u'Salaire':
                    self.obj.pay = Regexp(CleanText('./following-sibling::dd[1]'),
                                          u'Salaire : (.*)')(el)
