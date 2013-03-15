# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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
import datetime

from weboob.capabilities.travel import RoadmapError
from weboob.tools.browser import BasePage
from weboob.tools.misc import to_unicode
from weboob.tools.mech import ClientForm


__all__ = ['RoadmapPage']


class RoadmapSearchPage(BasePage):
    def search(self, departure, arrival, departure_time, arrival_time):
        self.browser.select_form('formHiRecherche')
        self.browser['lieuDepart'] = departure.encode('utf-8')
        self.browser['lieuArrivee'] = arrival.encode('utf-8')

        time = None
        if departure_time:
            self.browser['typeHeure'] = ['1']
            time = departure_time
        elif arrival_time:
            self.browser['typeHeure'] = ['-1']
            time = arrival_time

        if time:
            try:
                self.browser['jour'] = ['%d' % time.day]
                self.browser['mois'] = ['%02d/%d' % (time.month, time.year)]
                self.browser['heure'] = ['%02d' % time.hour]
                self.browser['minutes'] = ['%02d' % (time.minute - (time.minute%5))]
            except ClientForm.ItemNotFoundError:
                raise RoadmapError('Unable to establish a roadmap with %s time at "%s"' % ('departure' if departure_time else 'arrival', time))
        self.browser.submit()


class RoadmapPage(BasePage):
    def get_steps(self):
        errors = []
        for p in self.parser.select(self.document.getroot(), 'p.errors'):
            if p.text:
                errors.append(p.text.strip())

        if len(errors) > 0:
            raise RoadmapError('Unable to establish a roadmap: %s' % ', '.join(errors))

        current_step = None
        i = 0
        for tr in self.parser.select(self.document.getroot(), 'table.horaires2 tbody tr'):
            if not 'class' in tr.attrib:
                continue
            elif tr.attrib['class'] == 'trHautTroncon':
                current_step = {}
                current_step['id'] = i
                i += 1
                current_step['start_time'] = self.parse_time(self.parser.select(tr, 'td.formattedHeureDepart p', 1).text.strip())
                current_step['line'] = to_unicode(self.parser.select(tr, 'td.rechercheResultatColumnMode img')[-1].attrib['alt'])
                current_step['departure'] = to_unicode(self.parser.select(tr, 'td.descDepart p strong', 1).text.strip())
                current_step['duration'] = self.parse_duration(self.parser.select(tr, 'td.rechercheResultatVertAlign', 1).text.strip())
            elif tr.attrib['class'] == 'trBasTroncon':
                current_step['end_time'] = self.parse_time(self.parser.select(tr, 'td.formattedHeureArrivee p', 1).text.strip())
                current_step['arrival'] = to_unicode(self.parser.select(tr, 'td.descArrivee p strong', 1).text.strip())
                yield current_step

    def parse_time(self, time):
        h, m = time.split('h')
        return datetime.time(int(h), int(m))

    def parse_duration(self, dur):
        m = re.match('(\d+)min.', dur)
        if m:
            return datetime.timedelta(minutes=int(m.group(1)))
        m = re.match('(\d+)h(\d+)', dur)
        if m:
            return datetime.timedelta(hours=int(m.group(1)),
                                      minutes=int(m.group(2)))


class RoadmapConfirmPage(RoadmapPage):
    def select(self, name, num):
        try:
            self.browser[name] = str(num)
        except TypeError:
            self.browser[name] = [str(num)]

    def confirm(self):
        self.browser.select_form('form1')
        self.browser.set_all_readonly(False)
        try:
            self.select('idDepart', 1)
            self.select('idArrivee', 1)
            self.browser['modeTransport'] = ['0']
            self.browser['trainRer'] = 'true'
            self.browser['bus'] = 'false'
            self.browser['tramway'] = 'true'
            self.browser['bateau'] = 'false'
        except ClientForm.ControlNotFoundError:
            # We are already on the result page
            return
        else:
            self.browser.submit()
