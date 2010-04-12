# -*- coding: utf-8 -*-

"""
Copyright(C) 2009-2010  Christophe Benz

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

import re

from weboob.tools.browser import Browser

class YoutubeBrowser(Browser):
    regex = re.compile(r'&t=([^ ,&]*)')
    def get_video_url(self, page_url):
        result = self.openurl(page_url).read()
        for _signature in re.finditer(self.regex, result):
            signature = _signature.group(1)
            break
        else:
            return None
        m = re.match(r'http://.*\.youtube\.com/watch\?v=(.+)', page_url)
        video_id = m.group(1)
        url = 'http://www.youtube.com/get_video?video_id=%s&t=%s&fmt=18' % (video_id, signature)
        return url
