# -*- coding: utf-8 -*-

# Copyright(C) 2015 Matthieu Weber
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

from datetime import date
from itertools import imap, ifilter

from weboob.browser.pages import JsonPage, HTMLPage
from weboob.browser.elements import ItemElement, ListElement, DictElement, method
from weboob.capabilities.weather import Forecast, Current, City, Temperature
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import Filter, CleanText, CleanDecimal, Regexp, Format, Date


class Id(Filter):
    def filter(self, txt):
        return txt.split(", ")[0]


class SearchCitiesPage(JsonPage):
    @method
    class iter_cities(DictElement):
        item_xpath = '.'
        ignore_duplicate = True

        class item(ItemElement):
            klass = City

            obj_id = Id(Dict('id'))
            obj_name = Dict('value')


class WeatherPage(HTMLPage):
    @method
    class iter_forecast(ListElement):
        item_xpath = ('//div[contains(@class, "mid") and contains(@class, "local-weather-forecast")]//'
                      'tr[@class="meteogram-dates"]/td')

        class item(ItemElement):
            klass = Forecast

            obj_id = CleanText('.//span/@title')

            def obj_date(self):
                months = [u'tammikuuta', u'helmikuuta', u'maaliskuuta', u'huhtikuuta', u'toukokuuta', u'kesäkuuta',
                          u'heinäkuuta', u'elokuuta', u'syyskuuta', u'lokakuuta', u'marraskuuta', u'joulukuuta']
                d = CleanText('.//span/@title')(self).split()
                return date(int(d[2]), months.index(d[1])+1, int(d[0].strip(".")))

            def temperatures(self):
                offset = int(CleanText('string(sum(./preceding-sibling::td/@colspan))')(self))
                length = int(CleanText('@colspan')(self))
                temps = CleanText('../../../tbody/tr[@class="meteogram-temperatures"]/td[position() > %d '
                                  'and position() <= %d]/span' % (offset, offset+length))(self)
                return [float(_.strip(u'\xb0')) for _ in temps.split()]

            def obj_low(self):
                return Temperature(min(self.temperatures()), u'C')

            def obj_high(self):
                return Temperature(max(self.temperatures()), u'C')

            def obj_text(self):
                offset = int(CleanText('string(sum(./preceding-sibling::td/@colspan))')(self))
                length = int(CleanText('@colspan')(self))
                hour_test = ('../../tr[@class="meteogram-times"]/td[position() > %d and position() <= %d '
                             'and .//text() = "%%s"]' % (offset, offset+length))
                hour_offset = 'string(count(%s/preceding-sibling::td)+1)' % (hour_test)
                values = [
                    '../../../tbody/tr[@class="meteogram-weather-symbols"]/td[position() = %d]/div/@title',
                    '../../../tbody/tr[@class="meteogram-apparent-temperatures"]/td[position() = %d]/div/@title',
                    '../../../tbody/tr[@class="meteogram-wind-symbols"]/td[position() = %d]/div/@title',
                    '../../../tbody/tr[@class="meteogram-probabilities-of-precipitation"]/td[position() = %d]' +
                    '/div/@title',
                    '../../../tbody/tr[@class="meteogram-hourly-precipitation-values"]/td[position() = %d]/span/@title',
                ]

                def descriptive_text_for_hour(hour):
                    hour_exists = CleanText(hour_test % hour)(self) == hour
                    if hour_exists:
                        offset = int(CleanText(hour_offset % hour)(self))

                        def info_for_value(value):
                            return CleanText(value % offset)(self).replace(u'edeltävän tunnin ', u'')
                        return ("klo %s: " % hour) + ", ".join(ifilter(bool, imap(info_for_value, values)))

                return u'\n' + u'\n'.join(ifilter(bool, imap(descriptive_text_for_hour, ["02", "14"])))

    @method
    class get_current(ItemElement):
        klass = Current

        obj_id = date.today()
        obj_date = Date(Regexp(CleanText('//table[@class="observation-text"]//span[@class="time-stamp"]'),
                               r'^(\d+\.\d+.\d+)'))
        obj_text = Format(u'%s, %s, %s',
                          CleanText(u'(//table[@class="observation-text"])//tr[2]/td[2]'),
                          CleanText(u'(//table[@class="observation-text"])//tr[5]/td[1]'),
                          CleanText(u'(//table[@class="observation-text"])//tr[4]/td[2]'))

        def obj_temp(self):
            path = u'//table[@class="observation-text"]//span[@class="parameter-name" and text() = "Lämpötila"]' + \
                   u'/../span[@class="parameter-value"]'
            temp = CleanDecimal(Regexp(CleanText(path), r'^([^ \xa0]+)'), replace_dots=True)(self)
            unit = Regexp(CleanText(path), r'\xb0(\w)')(self)
            return Temperature(float(temp), unit)
