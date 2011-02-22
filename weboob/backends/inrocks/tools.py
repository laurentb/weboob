"common tools for inrocks backend"
# -*- coding: utf-8 -*-

# Copyright(C) 2011  Julien Hebert
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
def id2url(_id):
    "return an url from an id"
    regexp2 = re.compile("(\w+).([0-9]+).(.*$)")
    match = regexp2.match(_id)
    if match:
        return 'http://www.20minutes.fr/%s/%s/%s' % (   match.group(1),
                                                        match.group(2),
                                                        match.group(3))
    else:
        raise ValueError("id doesn't match")

def url2id(url):
    "return an id from an url"
    return url
