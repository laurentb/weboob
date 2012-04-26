# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Romain Bignon, Florent Fourcot
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

from datetime import datetime, date, time
from weboob.tools.browser import BasePage
from weboob.capabilities.gauge import Gauge, GaugeMeasure
from weboob.capabilities.base import NotAvailable


__all__ = ['ListPage', 'HistoryPage']


class ListPage(BasePage):
    def get_rivers_list(self):
        for pegel in self.document.getroot().xpath(".//a[@onmouseout='pegelaus()']"):
            data = pegel.attrib['onmouseover'].strip('pegelein(').strip(')').replace(",'", ",").split("',")
            gauge = Gauge(int(data[7]))
            gauge.name = data[0].strip("'")
            gauge.river = data[1]
            try:
                lastdate = date(*reversed([int(x) for x in data[2].split(' ')[0].split(".")]))
                lasttime = time(*[int(x) for x in data[2].split(' ')[1].split(":")])
                gauge.lastdate = datetime.combine(lastdate, lasttime)
            except:
                gauge.lastdate = NotAvailable
            try:
                gauge.level = float(data[3])
            except:
                gauge.level = NotAvailable
            try:
                gauge.flow = float(data[4])
            except:
                gauge.flow = NotAvailable
            bildforecast = data[5]
            if bildforecast == "pf_gerade.png":
                gauge.forecast = "stable"
            elif bildforecast == "pf_unten.png":
                gauge.forecast = "Go down"
            elif bildforecast == "pf_oben.png":
                gauge.forecast = "Go up"
            else:
                gauge.forecast = NotAvailable

            yield gauge


class HistoryPage(BasePage):
    def iter_history(self):
        table = self.document.getroot().cssselect('table[width="215"]')
        first = True
        for line in table[0].cssselect("tr"):
            if first:
                first = False
                continue
            history = GaugeMeasure()
            leveldate = date(*reversed([int(x) for x in line[0].text_content().split(' ')[0].split(".")]))
            leveltime = time(*[int(x) for x in line[0].text_content().split(' ')[1].split(":")])
            history.date = datetime.combine(leveldate, leveltime)

            try:
                history.level = float(line[1].text_content())
            except:
                history.level = NotAvailable
            try:
                history.flow = float(line[2].text_content())
            except:
                history.flow = NotAvailable

            yield history

    def first_value(self, table, index):
        first = NotAvailable
        for lignes in table[0].cssselect("tr"):
            try:
                valeur = float(lignes[index].text_content())
                if (valeur > 1.0):
                    first = valeur
                return first
            except:
                continue
        return first

    def last_seen(self):
        tables = self.document.getroot().cssselect('table[width="215"]')
        gauge = GaugeMeasure()
        gauge.level = self.first_value(tables, 1)
        gauge.flow = self.first_value(tables, 2)

        return gauge
