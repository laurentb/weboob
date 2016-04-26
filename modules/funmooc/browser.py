# -*- coding: utf-8 -*-

# Copyright(C) 2015      Vincent A
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


from weboob.browser import LoginBrowser, URL, need_login

from .pages import PageLogin, PageDashboard, PageChapter, PageSection
from .video import MoocVideo

import re


class FunmoocBrowser(LoginBrowser):
    BASEURL = 'https://www.fun-mooc.fr'

    login = URL('/accounts/login', PageLogin)
    dashboard = URL('/dashboard', PageDashboard)
    course = URL('/courses/(?P<course>[^/]+/[^/]+/[^/]+)/courseware/?$',
                 '/courses/(?P<course>[^/]+/[^/]+/[^/]+)/info/?$',
                 PageChapter)
    chapter = URL('/courses/(?P<course>[^/]+/[^/]+/[^/]+)/courseware'
                  '/(?P<chapter>[0-9a-f]+)/$', PageChapter)
    section = URL('/courses/(?P<course>[^/]+/[^/]+/[^/]+)/courseware/'
                  '(?P<chapter>[0-9a-f]+)/(?P<section>[0-9a-f]+)/$', PageSection)

    file = URL(r'https://fun\.libcast\.com/resource/(?P<id>[^/]+)/'
               r'flavor/video/fun-(?P<quality>\w+)\.mp4')

    def __init__(self, username, password, quality='hd', *args, **kwargs):
        super(FunmoocBrowser, self).__init__(username, password, *args, **kwargs)
        self.quality = quality

    def do_login(self):
        self.login.stay_or_go()
        csrf = self.session.cookies.get('csrftoken')
        self.page.login(self.username, self.password, csrf)

    def get_video(self, _id):
        if re.search('[^a-zA-Z0-9_-]', _id):
            match = self.file.match(_id)
            if not match:
                return None
            _id = match.group('id')

        v = MoocVideo(_id)
        v.url = self.file.build(id=_id, quality=self.quality)
        v.ext = 'mp4'
        v.title = _id
        return v

    @need_login
    def iter_videos(self, course, chapter, section):
        course = course.replace('-', '/')
        assert self.section.stay_or_go(course=course, chapter=chapter, section=section)
        return self.page.iter_videos()

    @need_login
    def iter_sections(self, courseid, chapter):
        course = courseid.replace('-', '/')
        assert self.chapter.stay_or_go(course=course, chapter=chapter)
        for coll in self.page.iter_sections():
            if coll.split_path[:2] == [courseid, chapter]:
                yield coll

    @need_login
    def iter_chapters(self, courseid):
        course = courseid.replace('-', '/')
        assert self.course.stay_or_go(course=course)
        return self.page.iter_chapters()

    @need_login
    def iter_courses(self):
        assert self.dashboard.stay_or_go()
        return self.page.iter_courses()
