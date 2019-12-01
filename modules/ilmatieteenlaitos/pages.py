# -*- coding: utf-8 -*-

# Copyright(C) 2015 Matthieu Weber
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

from six.moves import filter, map

from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import CleanText, Filter
from weboob.browser.pages import HTMLPage, JsonPage
from weboob.capabilities.weather import City, Current, Forecast, Temperature


class Id(Filter):
    def filter(self, txt):
        return txt.split(", ")[0]


class SearchCitiesPage(JsonPage):
    @method
    class iter_cities(ListElement):
        ignore_duplicate = True

        def find_elements(self):
            for el in self.el:
                yield el

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
                                  'and position() <= %d]/div' % (offset, offset+length))(self)
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
                        return ("klo %s: " % hour) + ", ".join(filter(bool, map(info_for_value, values)))

                return u'\n' + u'\n'.join(filter(bool, map(descriptive_text_for_hour, ["02", "03", "14", "15"])))

    def get_station_id(self):
        return CleanText(u'//select[@id="observation-station-menu"]/option[@selected="selected"]/@value')(self.doc)


class ObservationsPage(JsonPage):
    WINDS = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
             'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']

    def get_current(self):
        obj = Current()
        obj.id = date.today()
        obj.date = date.fromtimestamp(self.doc['latestObservationTime']/1000)
        obj.temp = Temperature(max(self.doc['t2m'])[1], u'C')
        last_hour_precipitations = int(max(self.doc['Precipitation1h'])[1])
        nebulosity = int(max(self.doc['TotalCloudCover'])[1])
        wind_speed = int(max(self.doc['WindSpeedMS'])[1])
        wind_direction = self.WINDS[int(max(self.doc['WindDirection'])[1] / 22.5)]
        obj.text = u'1h precipitations %d mm, wind %d m/s (%s), nebulosity %d/8' % (
            last_hour_precipitations, wind_speed, wind_direction, nebulosity)
        return obj
