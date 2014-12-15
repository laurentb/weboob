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
from weboob.browser.filters.standard import Regexp, CleanText, Date, Env, BrowserURL
from weboob.browser.filters.html import Link, CleanHTML


class SearchPage(HTMLPage):
    @method
    class iter_job_adverts(ListElement):
        item_xpath = '//table[@class="definition-table ordered"]/tbody/tr'

        class item(ItemElement):
            klass = BaseJobAdvert

            obj_id = Regexp(Link('td[@headers="offre"]/a'), '.*detailoffre/(.*?)(?:\?|;).*')
            obj_contract_type = CleanText('td[@headers="contrat"]')
            obj_title = CleanText('td[@headers="offre"]/a')
            obj_society_name = CleanText('td/div/p/span[@class="company"]/span', default='')
            obj_place = CleanText('td[@headers="lieu"]')
            obj_publication_date = Date(CleanText('td[@headers="dateEmission"]'))


class AdvertPage(HTMLPage):
    @method
    class get_job_advert(ItemElement):
        klass = BaseJobAdvert

        obj_id = Env('id')
        obj_url = BrowserURL('advert', id=Env('id'))
        obj_title = CleanText('//div[@id="offre-body"]/h4[@itemprop="title"]')
        obj_job_name = CleanText('//div[@id="offre-body"]/h4[@itemprop="title"]')
        obj_description = CleanHTML('//div[@id="offre-body"]/p[@itemprop="description"]')
        obj_society_name = CleanText('//div[@id="offre-body"]/div[@class="vcard"]/p[@class="title"]/span',
                                     default='')
        obj_contract_type = CleanText('//div[@id="offre-body"]/dl/dd/span[@itemprop="employmentType"]')
        obj_place = CleanText('//div[@id="offre-body"]/dl/dd/ul/li[@itemprop="addressRegion"]')
        obj_formation = CleanText('//div[@id="offre-body"]/dl/dd/span[@itemprop="qualifications"]')
        obj_pay = CleanText('//div[@id="offre-body"]/dl/dd/span[@itemprop="baseSalary"]')
        obj_experience = CleanText('//div[@id="offre-body"]/dl/dd/span[@itemprop="experienceRequirements"]')
        obj_publication_date = Date(CleanText('//span[@itemprop="datePosted"]'))
