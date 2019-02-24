# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Romain Bignon
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


import re

RSSID_RE = re.compile('tag:.*:(\w+)/(\d+)')
ID2URL_RE = re.compile('^(\w)(.*)\.([^ \.]+)$')

REGEXPS = {'/users/%s/journaux/%s': 'D%s.%s',
           '/news/%s':              'N.%s',
           '/wiki/%s':              'W.%s',
           '/suivi/%s':             'T.%s',
           '/sondages/%s':          'P.%s',
           '/forums/%s/posts/%s':   'B%s.%s',
          }


def f2re(f):
    return '.*' + f.replace('%s', '([^ /]+)')


def rssid(entry):
    m = RSSID_RE.match(entry.id)
    if not m:
        return None

    ind = m.group(1).replace('Post', 'Board')[0]

    for url_re, id_re in REGEXPS.items():
        if id_re[0] != ind:
            continue

        if id_re.count('%s') == 2:
            mm = re.match(f2re(url_re), entry.link)
            if not mm:
                return
            return '%s%s.%s' % (ind, mm.group(1), m.group(2))
        else:
            return '%s.%s' % (ind, m.group(2))


def id2url(id):
    m = ID2URL_RE.match(id)
    if not m:
        return None

    for url_re, id_re in REGEXPS.items():
        if id_re[0] != m.group(1):
            continue

        if id_re.count('%s') == 2:
            return url_re % (m.group(2), m.group(3))
        else:
            return url_re % m.group(3)


def url2id(url):
    for url_re, id_re in REGEXPS.items():
        m = re.match(f2re(url_re), url)
        if not m:
            continue

        return id_re % m.groups()


def id2threadid(id):
    m = ID2URL_RE.match(id)
    if m:
        return m.group(3)
