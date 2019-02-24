# -*- coding: utf-8 -*-

# Copyright(C) 2013      Vincent A
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

from __future__ import unicode_literals

import re
from datetime import datetime, time

from weboob.browser.pages import JsonPage
from weboob.browser.elements import DictElement, ItemElement, method
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import Field
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.calendar import BaseCalendarEvent, CATEGORIES, STATUS, TRANSP


class NoEvent(Exception):
    pass


class EventItem(ItemElement):
    klass = BaseCalendarEvent

    obj_id = Dict('id')
    obj_city = Dict('ville')
    obj_category = CATEGORIES.CONCERT

    obj_timezone = 'Europe/Paris'

    def obj_start_date(self):
        return datetime.fromtimestamp(int(self.el['datetimestamp']))

    def obj_end_date(self):
        return datetime.combine(self.obj_start_date().date(), time.max)

    def obj_summary(self):
        t = ' + '.join(g['NomGroupe'] for g in self.el['groupes'])
        if int(self.el['Guest']):
            t += ' + GUEST(S)'
        return t

    def obj_description(self):
        parts = []
        for g in self.el['groupes']:
            if 'WebOfficielGroupe' in g:
                parts.append('%s (%s): %s' % (g['NomGroupe'], g['StyleMusicalGroupe'], g['WebOfficielGroupe']))
            else:
                parts.append('%s (%s)' % (g['NomGroupe'], g['StyleMusicalGroupe']))
        if int(self.el['Guest']):
            parts.append('GUEST(S)')
        return '\n'.join(parts)

    def obj__flyer(self):
        img = self.el['flyer']
        if img:
            return 'http://sueurdemetal.com/images/flyers/' + img
        else:
            return NotAvailable

    def obj_url(self):
        slug = re.sub('[^a-z]', '', self.el['groupes'][0]['NomGroupe'], flags=re.I).lower()
        return 'http://www.sueurdemetal.com/detail-concert/%s-%s' % (slug, Field('id')(self))

    def obj_status(self):
        statuses = {
            '0': STATUS.CONFIRMED,
            '2': STATUS.CANCELLED,
        }
        return statuses.get(self.el['etat'])

    obj_transp = TRANSP.OPAQUE


class ConcertListPage(JsonPage):
    @method
    class iter_concerts(DictElement):
        item_xpath = 'results/collection1'

        class item(EventItem):
            pass


class ConcertPage(JsonPage):
    @method
    class get_concert(EventItem):
        def parse(self, el):
            try:
                self.el = self.el['results']['collection1'][0]
            except IndexError:
                raise NoEvent()

        def obj_price(self):
            return float(re.match('[\d.]+', self.el['prix']).group(0))

        def obj_location(self):
            return '%s, %s' % (self.el['salle'], self.el['adresse'])
