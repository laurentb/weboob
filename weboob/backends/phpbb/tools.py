# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Romain Bignon
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


from dateutil.parser import parse as _parse_dt
from urlparse import urlsplit, parse_qs

from weboob.tools.misc import local2utc


def url2id(url):
    v = urlsplit(url)
    pagename = v.path.split('/')[-1]
    args = parse_qs(v.query)
    if pagename == 'viewtopic.php':
        s = '%d' % int(args['t'][0])
        if 'p' in args:
            s += '.%d' % int(args['p'][0])
        return s

    return None

def id2url(id):
    v = id.split('.')
    if len(v) == 1:
        return 'viewtopic.php?t=%d' % int(v[0])
    if len(v) == 2:
        return 'viewtopic.php?t=%d&p=%d#p%d' % (int(v[0]),
                                                int(v[1]),
                                                int(v[1]))

def rssid(id):
    return id

def parse_date(s):
    s = s.replace(u'Fév', 'Feb') \
         .replace(u'Avr', 'Apr') \
         .replace(u'Mai', 'May') \
         .replace(u'Juin', 'Jun') \
         .replace(u'Juil', 'Jul') \
         .replace(u'Aoû', 'Aug') \
         .replace(u'Déc', 'Dec')
    return local2utc(_parse_dt(s))
