# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
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

ID2URL_NEWSPAPER = re.compile('.*/(\d{4})/(\d{2})/(\d{2})/(\d+)\.html$')
ID2URL_TELEGRAM  = re.compile('.*/~([A-Za-z0-9_]+)/(\d+)\.html$')
URL2ID_NEWSPAPER = re.compile('^N(\d{4})(\d{2})(\d{2}).(\d+)$')
URL2ID_TELEGRAM  = re.compile('^T([A-Za-z0-9_]+).(\d+)$')

def url2id(url):
    m = ID2URL_NEWSPAPER.match(url)
    if m:
        return 'N%04d%02d%02d.%d' % (int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)))
    m = ID2URL_TELEGRAM.match(url)
    if m:
        return 'T%s.%d' % (m.group(1), int(m.group(2)))
    return None

def id2url(_id):
    m = URL2ID_NEWSPAPER.match(_id)
    if m:
        return '/%04d/%02d/%02d/%d.html' % (int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)))
    m = URL2ID_TELEGRAM.match(_id)
    if m:
        return '/~%s/%d.html' % (m.group(1), int(m.group(2)))
    return None

def id2threadid(_id):
    m = URL2ID_NEWSPAPER.match(_id)
    if m:
        return int(m.group(4))
    m = URL2ID_TELEGRAM.match(_id)
    if m:
        return int(m.group(2))
    return None

def id2contenttype(_id):
    if not _id:
        return None
    if _id[0] == 'N':
        return 1
    if _id[0] == 'T':
        return 5
    return None
