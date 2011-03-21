# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Romain Bignon
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


import re

RSSID_RE = re.compile('tag:.*:(\w)\w+/(\d+)')
ID2URL_RE = re.compile('^(\w)([\w\-_]*)\.([^ \.]+)$')
URL2ID_DIARY_RE = re.compile('.*/users/([\w\-_]+)/journaux/([^\.]+)')
URL2ID_NEWSPAPER_RE = re.compile('.*/news/(.+)')
URL2ID_WIKI_RE = re.compile('.*/wiki/([^ /]+)')
URL2ID_SUIVI_RE = re.compile('.*/suivi/([^ /]+)')
URL2ID_FORUM_RE = re.compile('.*/forums/([\w\-_]+)/posts/([^\.]+)')

def rssid(entry):
    m = RSSID_RE.match(entry.id)
    if not m:
        return None
    if m.group(1) == 'D':
        mm = URL2ID_DIARY_RE.match(entry.link)
        if not mm:
            return
        return 'D%s.%s' % (mm.group(1), m.group(2))
    if m.group(1) == 'F':
        mm = URL2ID_FORUM_RE.match(entry.link)
        if not mm:
            return
        return 'F%s.%s' % (mm.group(1), m.group(2))
    return '%s.%s' % (m.group(1), m.group(2))

def id2url(id):
    m = ID2URL_RE.match(id)
    if not m:
        return None

    if m.group(1) == 'N':
        return '/news/%s' % m.group(3)
    if m.group(1) == 'D':
        return '/users/%s/journaux/%s' % (m.group(2), m.group(3))
    if m.group(1) == 'W':
        return '/wiki/%s' % m.group(3)
    if m.group(1) == 'F':
        return '/forums/%s/posts/%s' % (m.group(2), m.group(3))
    if m.group(1) == 'S':
        return '/suivi/%s' % m.group(3)

def url2id(url):
    m = URL2ID_NEWSPAPER_RE.match(url)
    if m:
        return 'N.%s' % (m.group(1))
    m = URL2ID_DIARY_RE.match(url)
    if m:
        return 'D%s.%s' % (m.group(1), m.group(2))
    m = URL2ID_WIKI_RE.match(url)
    if m:
        return 'W.%s' % (m.group(1))
    m = URL2ID_FORUM_RE.match(url)
    if m:
        return 'F%s.%s' % (m.group(1), m.group(2))
    m = URL2ID_SUIVI_RE.match(url)
    if m:
        return 'S.%s' % (m.group(1))

def id2threadid(id):
    m = ID2URL_RE.match(id)
    if m:
        return m.group(3)
