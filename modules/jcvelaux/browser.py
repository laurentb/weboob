# -*- coding: utf-8 -*-

# Copyright(C) 2013      dud
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
from weboob.deprecated.browser import Browser


__all__ = ['VelibBrowser']


class VelibBrowser(Browser):
    ENCODING = 'utf-8'

    API_KEY = '2282a34b49cf45d8129cdf93d88762914cece88b'
    BASE_URL = 'https://api.jcdecaux.com/vls/v1/'

    def __init__(self, *a, **kw):
        kw['parser'] = 'json'
        Browser.__init__(self, *a, **kw)

    def do_get(self, path, **query):
        qs = '&'.join('%s=%s' % kv for kv in query.items())
        if qs:
            qs = '&' + qs
        url = '%s%s?apiKey=%s%s' % (self.BASE_URL, path, self.API_KEY, qs)
        return self.get_document(self.openurl(url))

    def get_contracts_list(self):
        return self.do_get('contracts')

    def get_station_list(self, contract=None):
        if contract:
            doc = self.do_get('stations', contract=contract)
        else:
            doc = self.do_get('stations')
        for jgauge in doc:
            self._transform(jgauge)
        return doc

    def get_station_infos(self, gauge):
        station_id, contract = gauge.split('.', 1)
        doc = self.do_get('stations/%s' % station_id, contract=contract)
        return self._transform(doc)

    def _transform(self, jgauge):
        jgauge['id'] = '%s.%s' % (jgauge['number'], jgauge['contract_name'])
        jgauge['city'] = jgauge['contract_name']
        jgauge['last_update'] = datetime.datetime.fromtimestamp(jgauge['last_update'] / 1000)
        jgauge['latitude'] = str(jgauge['position']['lat'])
        jgauge['longitude'] = str(jgauge['position']['lng'])
        del jgauge['position']
        return jgauge
