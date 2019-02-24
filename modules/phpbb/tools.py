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


from dateutil.parser import parse as _parse_dt

from weboob.tools.compat import urlsplit, parse_qs
from weboob.tools.date import local2utc


def url2id(url, nopost=False):
    v = urlsplit(url)
    pagename = v.path.split('/')[-1]
    args = parse_qs(v.query)
    if pagename == 'viewforum.php':
        return '%d' % int(args['f'][0])
    if pagename == 'viewtopic.php':
        if 'f' in args:
            s = '%d' % int(args['f'][0])
        else:
            s = '0'
        s += '.%d' % int(args['t'][0])
        if 'p' in args and not nopost:
            s += '.%d' % int(args['p'][0])
        return s

    return None


def id2url(id):
    v = str(id).split('.')
    if len(v) == 1:
        return 'viewforum.php?f=%d' % int(v[0])
    if len(v) == 2:
        return 'viewtopic.php?f=%d&t=%d' % (int(v[0]), int(v[1]))
    if len(v) == 3:
        return 'viewtopic.php?f=%d&t=%d&p=%d#p%d' % (int(v[0]),
                                                     int(v[1]),
                                                     int(v[2]),
                                                     int(v[2]))


def id2topic(id):
    try:
        return int(str(id).split('.')[1])
    except IndexError:
        return None


def rssid(id):
    return id


def parse_date(s):
    s = s.replace(u'Fév', 'Feb') \
         .replace(u'Avr', 'Apr') \
         .replace(u'Mai', 'May') \
         .replace(u'Juin', 'Jun') \
         .replace(u'Juil', 'Jul') \
         .replace(u'Aoû', 'Aug') \
         .replace(u'Ao\xfbt', 'Aug') \
         .replace(u'Déc', 'Dec')
    return local2utc(_parse_dt(s))
