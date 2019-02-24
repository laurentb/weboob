"common tools for 20minutes backend"
# -*- coding: utf-8 -*-

# Copyright(C) 2011  Julien Hebert
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


def url2id(url):
    "return an id from an url"
    regexp = re.compile("http://www.20min.fr/(\w+)/([0-9]+)/(.*$)")
    match = regexp.match(url)
    return '%s.%d.%s' % (match.group(1), int(match.group(2)), match.group(3))


def rssid(entry):
    return url2id(entry.id)
