# -*- coding: utf-8 -*-

# Copyright(C) 2015      Bezleputh
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

from weboob.capabilities.travel import Departure
from weboob.browser.filters.standard import CleanText, Regexp, CleanDecimal
from weboob.browser.filters.html import Link
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.pages import JsonPage
from weboob.capabilities.base import Currency

from io import StringIO
import lxml.html as html
from datetime import datetime


class DeparturesPage(JsonPage):

    ENCODING = None

    def __init__(self, browser, response, *args, **kwargs):
        super(DeparturesPage, self).__init__(browser, response, *args, **kwargs)
        self.encoding = self.ENCODING or response.encoding
        parser = html.HTMLParser(encoding=self.encoding)
        if 'results' in self.doc['html']:
            self.doc = html.parse(StringIO(self.doc['html']['results']), parser)
        else:
            self.doc = html.Element('brinbrin')

    @method
    class get_station_departures(ListElement):
        item_xpath = '//ul[@class="trip-search-results"]/li/a'

        class item(ItemElement):
            klass = Departure

            obj_id = Regexp(Link('.'), '/(.*)')

            def obj_time(self):
                _date = CleanText('./article/div/h3[@itemprop="startDate"]/@content')(self).split('-')
                _time = Regexp(CleanText('./article/div/h3[@itemprop="startDate"]'),
                               u'.* à (\d+:\d+)')(self).split(':')
                return datetime(int(_date[0]), int(_date[1]),
                                int(_date[2]), int(_time[0]),
                                0 if len(_time) < 2 or len(_time) == 2 and not _time[1] else int(_time[1]))

            obj_type = CleanText('./article/div/h3[@class="fromto"]/span[@class!="u-visuallyHidden"]')
            obj_departure_station = CleanText('./article/div/dl[@class="geo-from"]/dd',
                                              replace=[(": voir avec le conducteur", "")])
            obj_arrival_station = CleanText('./article/div/dl[@class="geo-to"]/dd',
                                            replace=[(": voir avec le conducteur", "")])

            obj_price = CleanDecimal(CleanText('./article/div/div[@itemprop="location"]/strong/span[last()]'))

            def obj_currency(self):
                txt = CleanText('./article/div/div[@itemprop="location"]')(self)
                return Currency.get_currency(txt)

            obj_information = CleanText('./article/div/div[@class="availability"]')
