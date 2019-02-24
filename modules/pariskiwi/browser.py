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

from datetime import datetime, time
import re

from weboob.browser.browsers import APIBrowser


__all__ = ['ParisKiwiBrowser']


CAL = 'Agenda/Detruire_Ennui_Paris'

class ParisKiwiBrowser(APIBrowser):
    PROTOCOL = 'https'
    DOMAIN = 'pariskiwi.org'
    BASEURL = 'https://pariskiwi.org'
    ENCODING = 'utf-8'

    def list_events_all(self):
        ids = []
        cont = ''
        # titles are in m-d-y format, so we're forced to fetch everything
        while True:
            data = self.request('/api.php?action=query&list=allpages&apprefix=%s&aplimit=500&format=json&apcontinue=%s' % (CAL, cont))
            ids.extend(id_from_title(p['title']) for p in data['query']['allpages'])

            if 'continue' in data:
                cont = data['continue']['apcontinue']
            else:
                break

        ids = [_id for _id in ids if _id and _id != 'style']
        ids.sort(key=date_from_id)
        for _id in ids:
            yield {
                'id': _id,
                'date': date_from_id(_id),
            }

    def get_event(self, _id):
        _id = id_from_title(_id)
        j = self.request('/api.php?action=query&format=json&prop=revisions&rvprop=content&rvlimit=1&titles=%s/%s' % (CAL, _id))
        pages = j['query']['pages']
        page = pages[list(pages.keys())[0]]
        text = page['revisions'][0]['*']

        res = {
            'id': _id,
            'date': date_from_id(_id),
            'datetime': date_from_id(_id),
            'url': 'https://pariskiwi.org/index.php/%s/%s' % (CAL, _id),
            'description': text,
            'summary': find_title(text),
        }

        match = re.search(r'\b(\d\d?)h(\d\d)?\b', text)
        if match:
            res['hour'] = time(int(match.group(1)), int(match.group(2) or '0'))
            res['datetime'] = combine(res['date'], res['hour'])
            text = text[:match.start(0)] + text[match.end(0):]

        match = re.search(u'\\b(\\d+([,.]\\d+)?)\s*(euros\\b|euro\\b|€)', text)
        if match:
            res['price'] = float(match.group(1).replace(',', '.'))
            text = text[:match.start(0)] + text[match.end(0):]

        res['address'] = find_address(text)
        if not res['address']:
            res.pop('address')

        return res


def id_from_title(title):
    return title.rsplit('/', 1)[-1].replace(' ', '_')


def date_from_id(_id):
    _id = id_from_title(_id).split('_', 1)[0]
    return datetime.strptime(_id, '%m-%d-%Y')


def id_from_path(title):
    return title.replace(' ', '_').split('/')[-1]


def combine(dt, t):
    return datetime(dt.year, dt.month, dt.day, t.hour, t.minute)


def find_title(text):
    for line in text.split('\n'):
        line = line.strip()
        line = re.sub(r'^=+(.*)=+$', '', line)
        if line:
            return line


def find_address(text):
    address = []
    parts = text.split('\n')
    for n, p in enumerate(parts):
        match = re.search(r'\d+[\s,]+(rue|boulevard|avenue)\s+.+', p, re.I)
        if match:
            address.append(match.group(0))
            p = parts[n] = p[:match.start(0)] + p[match.end(0):]
        match = re.search(r'\b(75|92|93|94|78|77|95|91)\d\d\d\b.*', p)
        if match:
            address.append(match.group(0))
            p = parts[n] = p[:match.start(0)] + p[match.end(0):]
        match = re.search(r'\b(m.tro|rer)\b.*', p, re.I)
        if match:
            address.append(match.group(0))
            p = parts[n] = p[:match.start(0)] + p[match.end(0):]
        match = re.search(r'@\s+\w+(\s+[^.]+.*)?', p) # refuse '@foo' or '@ foo . plop'
        if match:
            address.append(match.group(0))
            p = parts[n] = p[:match.start(0)] + p[match.end(0):]

    return ' '.join(address)
