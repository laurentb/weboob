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
    VERSION = '1.0'
    COPYRIGHT = 'Copyright(C) 2010 Christophe Benz, Romain Bignon'
    CONFIG = {}

    def main(self, argv):
        self.load_modules(ICapVideoProvider)
        return self.process_command(*argv[1:])

    @ConsoleApplication.command('Get video information (accept ID or URL)')
    def command_info(self, id):
        results = {}
        for backend in self.weboob.iter_backends():
            video = backend.get_video(id)
            if video is None:
                continue
            rows = []
            rows.append(('ID', video.id))
            if video.title:
                rows.append(('Video title', video.title))
            if video.duration:
                rows.append(('Duration', '%d:%02d:%02d' % (
                    video.duration / 3600, (video.duration % 3600) / 60, video.duration % 60)))
            if video.url:
                rows.append(('URL', video.url))
            if video.author:
                rows.append(('Author', video.author))
            if video.date:
                rows.append(('Date', video.date))
            if video.rating_max:
                rows.append(('Rating', '%s / %s' % (video.rating, video.rating_max)))
            elif video.rating:
                rows.append(('Rating', video.rating))
            results[backend.name] = rows
        return results

    @ConsoleApplication.command('Search videos')
    def command_search(self, pattern=None):
        results = {}
        if pattern:
            results['BEFORE'] = u'Search pattern: %s' % pattern
        else:
            results['BEFORE'] = u'Last videos'
        for backend in self.weboob.iter_backends():
            try:
                iterator = backend.iter_search_results(pattern)
            except NotImplementedError:
                continue
            else:
                rows = []
                for video in iterator:
                    rows.append(('ID', video.id))
                    rows.append(('Title', video.title))
            results[backend.name] = rows
        return results

    @ConsoleApplication.command('Get video file URL from page URL')
    def command_file_url(self, url):
        for backend in self.weboob.iter_backends():
            video = backend.get_video(url)
            if video:
                print video.url
                break
