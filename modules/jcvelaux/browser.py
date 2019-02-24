# -*- coding: utf-8 -*-

# Copyright(C) 2013      dud
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

import datetime

from weboob.browser.browsers import APIBrowser


__all__ = ['VelibBrowser']


class VelibBrowser(APIBrowser):
    ENCODING = 'utf-8'

    API_KEY = '2282a34b49cf45d8129cdf93d88762914cece88b'
    BASEURL = 'https://api.jcdecaux.com/vls/v1/'

    def __init__(self, api_key, *a, **kw):
        super(VelibBrowser, self).__init__(*a, **kw)
        self.api_key = api_key or VelibBrowser.API_KEY

    def do_get(self, path, **query):
        query['apiKey'] = self.api_key
        return self.request(path, params=query)

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
        jgauge['latitude'] = '%s' % jgauge['position']['lat']
        jgauge['longitude'] = '%s' % jgauge['position']['lng']
        del jgauge['position']
        return jgauge
