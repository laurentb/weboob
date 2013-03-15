# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Julien Hébert, Romain Bignon
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

import datetime

from weboob.capabilities import UserError
from weboob.tools.misc import to_unicode
from weboob.tools.browser import BasePage, BrokenPageError


__all__ = ['StationNotFound', 'DeparturesPage']


class StationNotFound(UserError):
    pass


class DeparturesPage(BasePage):
    def iter_routes(self):
        try:
            table = self.parser.select(self.document.getroot(), 'table.horaires3', 1)
        except BrokenPageError:
            raise StationNotFound('Station not found')

        departure = self.parser.select(table, 'td.caption strong', 1).text
        for tr in table.findall('tr'):
            if len(tr.findall('td')) != 4:
                continue

            code_mission = self.parser.select(tr, 'td[headers=Code_de_mission] a', 1).text.strip()
            time_s = self.parser.select(tr, 'td[headers=Heure_de_passage]', 1).text.strip().rstrip(u'\xa0*')
            destination = self.parser.select(tr, 'td[headers=Destination]', 1).text.strip()
            plateform = self.parser.select(tr, 'td[headers=Voie]', 1).text.strip()

            late_reason = None
            time = None
            try :
                time = datetime.datetime.combine(datetime.date.today(), datetime.time(*[int(x) for x in time_s.split(':')]))
            except ValueError:
                late_reason = time_s
                self.logger.warning('Unable to parse datetime "%s"' % time_s)

            yield {'type':        to_unicode(code_mission),
                   'time':        time,
                   'departure':   to_unicode(departure),
                   'arrival':     to_unicode(destination),
                   'late':        datetime.time(),
                   'late_reason': late_reason,
                   'plateform':   to_unicode(plateform)}
