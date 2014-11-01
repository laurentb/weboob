# -*- coding: utf-8 -*-

# Copyright(C) 2014      Bezleputh
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

from weboob.browser.pages import HTMLPage, pagination
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.filters.standard import CleanText, Regexp, Format, Env, Date, BrowserURL, Join
from weboob.browser.filters.html import CleanHTML, Link
from weboob.capabilities.job import BaseJobAdvert
from weboob.exceptions import ParseError
from datetime import date, timedelta
from weboob.capabilities import NotAvailable


class SearchPage(HTMLPage):
    @pagination
    @method
    class iter_job_adverts(ListElement):
        item_xpath = '//section[@class="annonce"]'

        def next_page(self):
            return Link('//a[@class="picto picto-nextsmall"]')(self)

        class item(ItemElement):
            klass = BaseJobAdvert

            obj_id = Format(u'%s#%s',
                            Regexp(Env('domain'), 'http://www\.(.*)\.com'),
                            Regexp(CleanText('h1/a[2]/@href'), '/emplois/(.*)\.html'))
            obj_title = CleanText('h1/a[2]')
            obj_society_name = CleanText('figure/span[@itemprop="name"]')
            obj_place = CleanText('p[@class="inlineblock max-width-75"]')
            obj_contract_type = CleanText('p[@class="max-width-75"]')

            def obj_publication_date(self):
                _date = CleanText('p[@class="infos"]')
                try:
                    return Date(_date)(self)
                except ParseError:
                    str_date = _date(self)
                    if 'hier' in str_date:
                        return date.today() - timedelta(days=1)
                    else:
                        return date.today()


class AdvertPage(HTMLPage):
    @method
    class get_job_advert(ItemElement):
        klass = BaseJobAdvert

        obj_description = Join('\n%s', '//div[@id="annonce-detail"]/p[@class="text"]', textCleaner=CleanHTML)
        obj_id = Env('_id')
        obj_url = BrowserURL('advert_page', _id=Env('_id'))
        obj_publication_date = Date(Regexp(CleanText('//div[@id="annonce-detail"]/p[@class="infos"]'),
                                           '(\d{2}/\d{2}/\d{4})', default=NotAvailable), default=NotAvailable)
        obj_title = CleanText('//div[@id="annonce"]/div/div/h1')
        obj_society_name = CleanText('//section[@class="entp-resume"]/h1/a')

        obj_contract_type = CleanText('//dl[@class="infos-annonce"]/dt[span[@class="picto picto-contrat-grey"]]/following-sibling::dd[1]')
        obj_place = CleanText('//dl[@class="infos-annonce"]/dt[span[@class="picto picto-geolocalisation-grey"]]/following-sibling::dd[1]')
        obj_pay = CleanText('//div[@id="annonce-detail"]/p[@class="infos"]/preceding-sibling::p[1]',
                            replace=[('Salaire : ', '')])
