# -*- coding: utf-8 -*-

# Copyright(C) 2013      Romain Bignon
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


import re
from decimal import Decimal
from datetime import time, datetime, timedelta

from weboob.deprecated.browser import Page
from weboob.tools.json import json
from weboob.deprecated.mech import ClientForm
from weboob.capabilities.base import UserError, Currency


class ForeignPage(Page):
    def on_loaded(self):
        raise UserError('Your IP address is localized in a country not supported by this module (%s). Currently only the French website is supported.' % self.group_dict['country'])


class CitiesPage(Page):
    def get_stations(self):
        result = json.loads(self.document[self.document.find('{'):-2])
        return result['CITIES']


class SearchPage(Page):
    def search(self, departure, arrival, date, age, card, comfort_class):
        self.browser.select_form(name='saisie')
        self.browser['ORIGIN_CITY'] = departure.encode(self.browser.ENCODING)
        self.browser['DESTINATION_CITY'] = arrival.encode(self.browser.ENCODING)

        if date is None:
            date = datetime.now() + timedelta(hours=1)
        elif date < datetime.now():
            raise UserError("You cannot look for older departures")

        self.browser['OUTWARD_DATE'] = date.strftime('%d/%m/%y')
        self.browser['OUTWARD_TIME'] = [str(date.hour)]
        self.browser['PASSENGER_1'] = [age]
        self.browser['PASSENGER_1_CARD'] = [card]
        self.browser['COMFORT_CLASS'] = [str(comfort_class)]
        self.browser.controls.append(ClientForm.TextControl('text', 'nbAnimalsForTravel', {'value': ''}))
        self.browser['nbAnimalsForTravel'] = '0'
        self.browser.submit()


class SearchErrorPage(Page):
    def on_loaded(self):
        p = self.document.getroot().cssselect('div.messagesError p')
        if len(p) > 0:
            message = p[0].text.strip()
            raise UserError(message)


class SearchInProgressPage(Page):
    def on_loaded(self):
        link = self.document.xpath('//a[@id="url_redirect_proposals"]')[0]
        self.browser.location(link.attrib['href'])


class ResultsPage(Page):
    def get_value(self, div, name, last=False):
        i = -1 if last else 0
        p = div.cssselect(name)[i]
        sub = p.find('p')
        if sub is not None:
            txt = sub.tail.strip()
            if txt == '':
                p.remove(sub)
            else:
                return unicode(txt)

        return unicode(self.parser.tocleanstring(p))

    def parse_hour(self, div, name, last=False):
        txt = self.get_value(div, name, last)
        hour, minute = map(int, txt.split('h'))
        return time(hour, minute)

    def iter_results(self):
        for div in self.document.getroot().cssselect('div.train_info'):
            info = None
            price = None
            currency = None
            for td in div.cssselect('td.price'):
                txt = self.parser.tocleanstring(td)
                p = Decimal(re.sub('([^\d\.]+)', '', txt))
                if price is None or p < price:
                    info = list(div.cssselect('strong.price_label')[0].itertext())[-1].strip().strip(':')
                    price = p
                    currency = Currency.get_currency(txt)

            yield {'type': self.get_value(div, 'div.transporteur-txt'),
                   'time': self.parse_hour(div, 'div.departure div.hour'),
                   'departure': self.get_value(div, 'div.departure div.station'),
                   'arrival': self.get_value(div, 'div.arrival div.station', last=True),
                   'arrival_time': self.parse_hour(div, 'div.arrival div.hour', last=True),
                   'price': price,
                   'currency': currency,
                   'price_info': info,
                  }
