# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Christophe Benz

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

from weboob.capabilities.video import ICapVideoProvider
from weboob.tools.application import ConsoleApplication

class Videoob(ConsoleApplication):
    APPNAME = 'videoob'
    CONFIG = {}

    def main(self, argv):
        self.weboob.load_backends(ICapVideoProvider)
        return self.process_command(*argv[1:])

    @ConsoleApplication.command('Get video file URL from page URL')
    def command_file_url(self, url):
        for name, backend in self.weboob.iter_backends(ICapVideoProvider):
            print backend.get_video_url(url)

    @ConsoleApplication.command('Get video title from page URL')
    def command_title(self, url):
        for name, backend in self.weboob.iter_backends(ICapVideoProvider):
            print backend.get_video_title(url)
