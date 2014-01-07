# -*- coding: utf-8 -*-

# Copyright(C) 2013      Florent Fourcot
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

from weboob.tools.json import json
from weboob.tools.browser import BaseBrowser, BrowserBanned


__all__ = ['ColissimoBrowser']


class ColissimoBrowser(BaseBrowser):
    PROTOCOL = 'http'
    DOMAIN = 'www.laposte.fr'
    ENCODING = None
    USER_AGENT = BaseBrowser.USER_AGENTS['android']

    api_key = 'd112dc5c716d443af02b13bf708f73985e7ee943'

    def get_tracking_info(self, _id):
        json_data = self.readurl('/outilsuivi/web/suiviInterMetiers.php?key=%s&method=json&code=%s' % (self.api_key, _id))
        if json_data is None:
            raise BrowserBanned('You are banned of the colissimo API (too many requests from your IP)')
        return json.loads(json_data)
