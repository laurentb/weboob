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
from weboob.tools.application.results import BaseItem, FieldException, ObjectItem


class VideoItem(ObjectItem):
    def format(self, select=[]):
        if select:
            return u'\t'.join(self.get(field) for field in select)
        else:
            lines = [
                u'ID: %s' % self.obj.id,
                u'title: %s'% self.obj.title,
                u'duration: %s'% self.obj.formatted_duration,
                u'URL: %s'% self.obj.url,
                u'author: %s'% self.obj.author,
                u'date: %s'% self.obj.date,
                u'rating_max: %s'% self.obj.rating,
                u'rating: %s'% self.obj.rating_max,
            ]
            return u'\n'.join(lines)


class SearchResultItem(BaseItem):
    def __init__(self, _id, title, duration):
        self.id = _id
        self.title = title
        self.duration = duration

    def get(self, name):
        try:
            return getattr(self, name)
        except AttributeError:
            raise FieldException(name)

    def format(self, select=[]):
        if select:
            return u'\t'.join(unicode(self.get(field)) for field in select)
        else:
            return u'%s %s (%s)' % (self.id, self.title, self.duration)


class Videoob(ConsoleApplication):
    APPNAME = 'videoob'
    VERSION = '1.0'
    COPYRIGHT = 'Copyright(C) 2010 Christophe Benz, Romain Bignon'
    CONFIG = {}

    def __init__(self):
        ConsoleApplication.__init__(self)
        self._parser.add_option('--nsfw', action='store_true', help='enable non-suitable for work videos')

    def main(self, argv):
        self.load_modules(ICapVideoProvider)
        return self.process_command(*argv[1:])

    @ConsoleApplication.command('Get video information (accept ID or URL)')
    def command_info(self, id):
        for backend, video in self.weboob.do('get_video', id):
            if video is None:
                continue
            print self.format(VideoItem(video))

    @ConsoleApplication.command('Search videos')
    def command_search(self, pattern=None):
        print u'Search pattern: %s' % pattern if pattern else u'Last videos'
        for backend, video in self.weboob.do(
            'iter_search_results', pattern=pattern, nsfw=self.options.nsfw):
            print self.format(SearchResultItem(video.id, title=video.title, duration=video.formatted_duration))
