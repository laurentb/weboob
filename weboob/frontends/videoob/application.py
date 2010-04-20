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

    def configure_parser(self, parser):
        parser.add_option('-b', '--backends', help='what backend(s) to enable (comma separated)') 

    def main(self, argv):
        self.weboob.load_modules(ICapVideoProvider)
        self.enabled_backends = None
        if self.options.backends:
            self.enabled_backends = self.options.backends.split(',')
        return self.process_command(*argv[1:])

    def iter_enabled_backends(self):
        for backend in self.weboob.iter_backends(ICapVideoProvider):
            if self.enabled_backends is not None and backend.NAME not in self.enabled_backends:
                continue
            yield backend

    @ConsoleApplication.command('Get video information')
    def command_info(self, _id):
        for backend in self.iter_enabled_backends():
            video = backend.get_video(_id)
            if video is None:
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

    @ConsoleApplication.command('Search videos')
    def command_search(self, pattern=None):
        print u'.------------------------------------------------------------------------------.'
        if pattern:
            print u'| %-76s |' % (u'Search: %s' % pattern)
        else:
            print u'| %-76s |' % 'Last videos'
        print u"+------------.-----------------------------------------------------------------'"
        for backend in self.iter_enabled_backends():
            try:
                iterator = backend.iter_search_results(pattern)
            except NotImplementedError:
                continue
            else:
                for video in iterator:
                    print u"| %10d | %-63s |" % (video.id, video.title)
        print u"'--------------'---------------------------------------------------------------'"

    @ConsoleApplication.command('Get video file URL from page URL')
    def command_file_url(self, url):
        for backend in self.iter_enabled_backends():
            video = backend.get_video(url)
            if video:
                print video.url
                break
