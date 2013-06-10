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
from dateutil.parser import parse as parse_date

from weboob.capabilities.tracking import Package, Location
from weboob.capabilities import NotAvailable
from weboob.tools.browser import BasePage


__all__ = ['IndexPage', 'TrackPage']


class IndexPage(BasePage):
    def track_package(self, _id):
        self.browser.select_form(predicate=lambda form: form.attrs.get('id', '') == 'suivreEnvoi')
        self.browser['chronoNumbers'] = _id.encode('utf-8')
        self.browser.submit()

class TrackPage(BasePage):
    def get_info(self, id):
        p = Package(id)
        p.arrival = NotAvailable
        p.history = []

        for i, tr in enumerate(self.document.xpath('//table[@class="tabListeEnvois"]//tr')):
            tds = tr.findall('td')
            if len(tds) < 3:
                continue

            loc = Location(i)
            loc.name = unicode(tds[1].text)
            loc.activity = unicode(tds[1].find('br').tail)
            if tds[-1].text is not None:
                loc.activity += ', ' + self.parser.tocleanstring(tds[-1])
            date = re.sub('[a-z]+', '', self.parser.tocleanstring(tds[0])).strip()
            date = re.sub('(\d+)/(\d+)/(\d+)', r'\3-\2-\1', date)
            loc.date = parse_date(date)
            p.history.append(loc)

        return p
