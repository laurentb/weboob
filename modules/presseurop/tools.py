"tools for presseurop backend"
# -*- coding: utf-8 -*-

# Copyright(C) 2012  Florent Fourcot
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


import re


def url2id(url):
    "return an id from an url"
    if "/today/" in url:
        return url.split("#")[1]
    else:
        regexp = re.compile(".*/.*-([0-9]+)\?.*")
        id = regexp.match(url).group(1)
        return id


def rssid(entry):
    return url2id(entry.link)
