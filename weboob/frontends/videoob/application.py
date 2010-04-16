# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Christophe Benz, Romain Bignon

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

    @ConsoleApplication.command('Get video information')
    def command_info(self, _id):
        for backend in self.weboob.iter_backends(ICapVideoProvider):
            try:
                video = backend.get_video(_id)
            except NotImplementedError:
                continue
            print u'.------------------------------------------------------------------------------.'
            print u'| %-76s |' % (u'%s: %s' % (backend.name, video.title))
            print u"+-----------------.------------------------------------------------------------'"
            print u"| Duration        | %d:%02d:%02d" % (video.duration/3600, (video.duration%3600)/60, video.duration%60)
            print u"| URL             | %s" % video.url
            print u"| Author          | %s" % video.author
            print u"| Date            | %s" % video.date
            if video.rating_max:
                print u"| Rating          | %s / %s" % (video.rating, video.rating_max)
            elif video.rating:
                print u"| Rating          | %s" % video.rating
            print u"'-----------------'                                                             "

    @ConsoleApplication.command('Get video file URL from page URL')
    def command_file_url(self, url):
        for backend in self.weboob.iter_backends(ICapVideoProvider):
            video_url = backend.get_video_url(url)
            if video_url:
                print video_url
                break

    @ConsoleApplication.command('Get video title from page URL')
    def command_title(self, url):
        for backend in self.weboob.iter_backends(ICapVideoProvider):
            video_title = backend.get_video_title(url)
            if video_title:
                print video_title
                break
