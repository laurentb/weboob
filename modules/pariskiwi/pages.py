# -*- coding: utf-8 -*-

# Copyright(C) 2013      Vincent A
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


from weboob.deprecated.browser import Page
from datetime import datetime, time
import json
import lxml.html
import re


def date_from_id(_id):
    textdate = _id.split('_')[0]
    return datetime.strptime(textdate, '%m-%d-%Y')


def id_from_path(title):
    return title.replace(' ', '_').split('/')[-1]


def combine(dt, t):
    return datetime(dt.year, dt.month, dt.day, t.hour, t.minute)


class PageList(Page):
    def get_events(self):
        raise NotImplementedError()


class PageList2(Page):
    def list_events(self):
        events = list(self.unsorted_list())
        events.sort(key=lambda d: (d['date'], d['id']))
        return events

    def unsorted_list(self):
        # TODO paginate when there are >500 events
        for jpage in json.loads(self.document)['query']['allpages']:
            d = {}
            d['id'] = id_from_path(jpage['title'])
            d['date'] = date_from_id(d['id'])
            yield d


class PageEvent(Page):
    def get_event(self):
        d = {}
        d['id'] = id_from_path(self.url)
        d['date'] = date_from_id(d['id'])
        d['datetime'] = date_from_id(d['id'])
        d['url'] = self.url

        html = lxml.html.fromstring(self.document)
        for div in html.iter('div'):
            if div.get('id') == 'bodyContent':
                break

        tags = [t for t in div if not callable(t.tag) and not t.get('id') and 'footer' not in t.get('class', '')]
        parts = [t.text_content().strip().replace('\n', ' ') for t in tags]
        description = '\n'.join(parts)
        summary = description.split('\n', 1)[0]

        self.div = div
        if not summary:
            return None

        d['summary'] = summary
        d['description'] = description

        for n, p in enumerate(parts):
            match = re.search(r'\b(\d\d?)h(\d\d)?\b', p)
            if match:
                d['hour'] = time(int(match.group(1)), int(match.group(2) or '0'))
                d['datetime'] = combine(d['date'], d['hour'])
                parts[n] = p[:match.start(0)] + p[match.end(0):]
                break

        for n, p in enumerate(parts):
            match = re.search(ur'\b(\d+([,.]\d+)?)\s*(euros\b|euro\b|€)', p)
            if match:
                d['price'] = float(match.group(1).replace(',', '.'))
                parts[n] = p[:match.start(0)] + p[match.end(0):]
                break

        address = []
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

        if address:
            d['address'] = ' '.join(address)

        return d
